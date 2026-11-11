"""Dead code detection for Python projects.

This package performs name-based whole-program analysis across a set of Python
source files. It reports unused imports, functions, classes, methods, module-
level variables, and unreachable statements with confidence scores.
"""

from __future__ import annotations

import ast
import fnmatch
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

__all__ = [
    "DeadCodeError",
    "DetectionKind",
    "Finding",
    "Report",
    "format_json",
    "format_text",
    "scan",
    "scan_sources",
]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

DetectionKind = Literal[
    "unused_import",
    "unused_function",
    "unused_class",
    "unused_method",
    "unused_variable",
    "unreachable_code",
]


class DeadCodeError(Exception):
    """Raised for invalid library usage such as bad paths or too many files."""

    def __init__(self, code: Literal["too_many_files", "invalid_path"], message: str = ""):
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class Finding:
    """A single dead code finding."""

    kind: DetectionKind
    name: str
    module: str
    line: int
    confidence: int


@dataclass(frozen=True)
class Report:
    """Result of a scan: findings and per-file processing errors."""

    findings: list[Finding]
    errors: list[tuple[str, str]]


_DefinitionKind = Literal["function", "class", "method", "variable", "import"]


@dataclass(frozen=True)
class _Definition:
    kind: _DefinitionKind
    name: str
    module: str
    line: int
    decorated: bool
    has_overload: bool


def _has_decorators(node: ast.AST) -> bool:
    """Return True if node has any decorators."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return bool(node.decorator_list)
    return False


def _has_overload(node: ast.AST) -> bool:
    """Return True if node is decorated with typing.overload."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    for decorator in node.decorator_list:
        decorator_str = ast.unparse(decorator)
        if decorator_str == "overload" or decorator_str.endswith(".overload"):
            return True
    return False


def _extract_all(tree: ast.Module) -> set[str]:
    """Return strings listed in a module's __all__ assignment, if any."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__all__"
                    and isinstance(node.value, (ast.List, ast.Tuple, ast.Set))
                ):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            names.add(elt.value)
    return names


def _collect_in_block(
    stmts: list[ast.stmt],
    module: str,
    scope: Literal["module", "class"],
    defs: list[_Definition],
) -> None:
    """Collect definitions from a statement list under the given scope."""
    for stmt in stmts:
        if isinstance(stmt, ast.ClassDef):
            # Module-level or nested class; use 'class' kind for both.
            defs.append(
                _Definition(
                    "class",
                    stmt.name,
                    module,
                    stmt.lineno,
                    _has_decorators(stmt),
                    False,
                )
            )
            _collect_in_block(stmt.body, module, "class", defs)
            continue
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if scope == "module":
                kind: _DefinitionKind = "function"
            elif scope == "class":
                kind = "method"
            else:
                # Nested function inside a function; not part of the public
                # module/class API, so ignored for dead-code analysis.
                continue
            defs.append(
                _Definition(
                    kind,
                    stmt.name,
                    module,
                    stmt.lineno,
                    _has_decorators(stmt),
                    _has_overload(stmt),
                )
            )
            # Do not descend into function bodies for definition collection.
            continue
        if scope == "module" and isinstance(stmt, ast.Import):
            for alias in stmt.names:
                bound = alias.asname if alias.asname else alias.name.split(".")[0]
                defs.append(_Definition("import", bound, module, stmt.lineno, False, False))
            continue
        if scope == "module" and isinstance(stmt, ast.ImportFrom):
            if stmt.module == "__future__":
                continue
            if stmt.module != "*" and not any(alias.name == "*" for alias in stmt.names):
                for alias in stmt.names:
                    bound = alias.asname if alias.asname else alias.name
                    defs.append(_Definition("import", bound, module, stmt.lineno, False, False))
            continue
        if scope == "module" and isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    defs.append(
                        _Definition("variable", target.id, module, target.lineno, False, False)
                    )
        if (
            scope == "module"
            and isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.value is not None
        ):
            defs.append(
                _Definition("variable", stmt.target.id, module, stmt.target.lineno, False, False)
            )
        # Process nested blocks in control-flow statements with the same scope
        # so that module-level definitions inside if/for/try are still collected.
        _process_nested_blocks(stmt, scope, module, defs)


def _process_nested_blocks(
    stmt: ast.stmt,
    scope: Literal["module", "class"],
    module: str,
    defs: list[_Definition],
) -> None:
    """Recursively collect definitions from control-flow sub-blocks."""
    if isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While)):
        _collect_in_block(stmt.body, module, scope, defs)
        _collect_in_block(stmt.orelse, module, scope, defs)
    elif isinstance(stmt, ast.Try):
        _collect_in_block(stmt.body, module, scope, defs)
        for handler in stmt.handlers:
            _collect_in_block(handler.body, module, scope, defs)
        _collect_in_block(stmt.orelse, module, scope, defs)
        _collect_in_block(stmt.finalbody, module, scope, defs)
    elif isinstance(stmt, (ast.With, ast.AsyncWith)):
        _collect_in_block(stmt.body, module, scope, defs)
    elif isinstance(stmt, ast.Match):
        for case in stmt.cases:
            _collect_in_block(case.body, module, scope, defs)


def _collect_definitions(tree: ast.Module, module: str, defs: list[_Definition]) -> None:
    """Collect all reportable definitions from a module."""
    _collect_in_block(tree.body, module, "module", defs)


def _collect_references(tree: ast.Module, references: set[str]) -> None:
    """Collect every name reference in a module."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            references.add(node.id)
        elif isinstance(node, ast.Attribute):
            references.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.isidentifier():
                references.add(node.value)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                references.add(alias.name)


def _collect_load_names(tree: ast.Module) -> set[str]:
    """Collect Name Load identifiers within a module (for unused import logic)."""
    loads: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loads.add(node.id)
    return loads


def _is_test_module(module: str) -> bool:
    """Return True if the module path looks like a test file."""
    name = module.split("/")[-1]
    return (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py")


def _is_exempt(
    definition: _Definition,
    module_all: set[str],
    is_test_module: bool,
    whitelist: Sequence[str],
    include_decorated: bool,
) -> bool:
    """Check whether a definition should never be reported regardless of references."""
    name = definition.name
    if name in module_all:
        return True
    if name.startswith("__") and name.endswith("__"):
        return True
    if name == "_":
        return True
    if any(fnmatch.fnmatchcase(name, pattern) for pattern in whitelist):
        return True
    if definition.kind in ("function", "method") and name.startswith("test_") and is_test_module:
        return True
    if definition.kind == "class" and name.startswith("Test") and is_test_module:
        return True
    if definition.kind == "method" and name in {"setUp", "tearDown"}:
        return True
    if definition.kind in ("function", "method") and definition.has_overload:
        return True
    return (
        definition.kind in ("function", "method") and definition.decorated and not include_decorated
    )


def _find_unreachable(tree: ast.Module, module: str, findings: list[Finding]) -> None:
    """Find unreachable statements after return/raise/continue/break."""

    def process_block(stmts: list[ast.stmt], current_name: str) -> None:
        found = False
        for i, stmt in enumerate(stmts):
            if found:
                break
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Continue, ast.Break)) and i + 1 < len(
                stmts
            ):
                next_stmt = stmts[i + 1]
                findings.append(
                    Finding(
                        "unreachable_code",
                        current_name,
                        module,
                        next_stmt.lineno,
                        100,
                    )
                )
                found = True
                # The unreachable code is not executed; definitions inside it
                # were collected in pass 1, but further unreachable detection
                # is intentionally skipped (reported once per block).
            process_stmt(stmt, current_name)

    def process_stmt(stmt: ast.stmt, current_name: str) -> None:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            process_block(stmt.body, stmt.name)
        elif isinstance(stmt, ast.ClassDef):
            # Class body cannot contain return/break; still process nested blocks.
            process_block(stmt.body, current_name)
        elif isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            process_block(stmt.body, current_name)
            process_block(stmt.orelse, current_name)
        elif isinstance(stmt, ast.Try):
            process_block(stmt.body, current_name)
            for handler in stmt.handlers:
                process_block(handler.body, current_name)
            process_block(stmt.orelse, current_name)
            process_block(stmt.finalbody, current_name)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            process_block(stmt.body, current_name)
        elif isinstance(stmt, ast.Match):
            for case in stmt.cases:
                process_block(case.body, current_name)

    process_block(tree.body, "<module>")


def scan_sources(
    sources: Mapping[str, str],
    *,
    whitelist: Sequence[str] = (),
    include_decorated: bool = False,
) -> Report:
    """Analyze in-memory sources keyed by module name.

    Args:
        sources: Mapping from module key (e.g. ``"a.py"``) to source text.
        whitelist: fnmatch patterns for names that are never reported.
        include_decorated: If False (default), decorated functions and methods
            are exempt from unused-function/unused-method detection. If True,
            they are reported with confidence 50.

    Returns:
        A :class:`Report` with sorted findings and per-module errors.
    """
    modules: dict[str, ast.Module] = {}
    errors: list[tuple[str, str]] = []
    defs: list[_Definition] = []
    all_names: dict[str, set[str]] = {}

    for module_name, source in sources.items():
        try:
            tree = ast.parse(source, filename=module_name)
            modules[module_name] = tree
            all_names[module_name] = _extract_all(tree)
            _collect_definitions(tree, module_name, defs)
        except SyntaxError:
            errors.append((module_name, "syntax_error"))
        except ValueError:
            errors.append((module_name, "syntax_error"))
        except RecursionError:
            errors.append((module_name, "too_deep"))

    references: set[str] = set()
    for tree in modules.values():
        _collect_references(tree, references)
    for names in all_names.values():
        references.update(names)

    module_load_names: dict[str, set[str]] = {}
    for module_name, tree in modules.items():
        module_load_names[module_name] = _collect_load_names(tree)

    findings: list[Finding] = []
    for definition in defs:
        if definition.kind == "import":
            loads = module_load_names.get(definition.module, set())
            module_all = all_names.get(definition.module, set())
            if definition.name not in loads and definition.name not in module_all:
                findings.append(
                    Finding(
                        "unused_import",
                        definition.name,
                        definition.module,
                        definition.line,
                        90,
                    )
                )
            continue

        module_all = all_names.get(definition.module, set())
        is_test = _is_test_module(definition.module)
        if _is_exempt(
            definition,
            module_all,
            is_test,
            whitelist,
            include_decorated,
        ):
            continue
        if definition.name not in references:
            kind_map: dict[_DefinitionKind, DetectionKind] = {
                "function": "unused_function",
                "class": "unused_class",
                "method": "unused_method",
                "variable": "unused_variable",
            }
            kind = kind_map[definition.kind]
            confidence = 60
            if (
                definition.kind in ("function", "method")
                and definition.decorated
                and include_decorated
            ):
                confidence = 50
            findings.append(
                Finding(kind, definition.name, definition.module, definition.line, confidence)
            )

    for module_name, tree in modules.items():
        _find_unreachable(tree, module_name, findings)

    findings.sort(key=lambda f: (f.module, f.line, f.name))
    return Report(findings=findings, errors=errors)


def _iter_py_files(root: Path, exclude: Sequence[str]) -> list[Path]:
    """Return all .py files under root, excluding directories matching exclude."""
    result: list[Path] = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        parts = rel.parts
        if any(
            any(fnmatch.fnmatch(part, pattern) for pattern in exclude) or part in exclude
            for part in parts
        ):
            continue
        result.append(path)
    return result


def scan(
    paths: Sequence[Path],
    *,
    whitelist: Sequence[str] = (),
    max_file_bytes: int = 1_000_000,
    max_files: int = 5000,
    exclude: Sequence[str] = (".venv", ".git", "__pycache__"),
) -> Report:
    """Scan files on disk.

    Args:
        paths: Directories to scan recursively or individual ``.py`` files.
        whitelist: fnmatch patterns for names that are never reported.
        max_file_bytes: Files larger than this are skipped with ``file_too_large``
            errors.
        max_files: Maximum number of ``.py`` files to consider. Exceeding this
            raises :class:`DeadCodeError` with code ``too_many_files``.
        exclude: Directory/file names or fnmatch patterns to skip.

    Returns:
        A :class:`Report`, with ``errors`` containing per-file processing
        problems encountered during reading and parsing.

    Raises:
        DeadCodeError: if any path does not exist (``invalid_path``) or
            ``max_files`` is exceeded.
    """
    sources: dict[str, str] = {}
    pre_errors: list[tuple[str, str]] = []
    file_count = 0

    for path in paths:
        if not path.exists():
            raise DeadCodeError(
                "invalid_path",
                f"Path does not exist: {path}",
            )

        if path.is_dir():
            root = path
            for py_file in _iter_py_files(root, exclude):
                file_count += 1
                if file_count > max_files:
                    raise DeadCodeError("too_many_files")
                rel = py_file.relative_to(root).as_posix()
                if py_file.stat().st_size > max_file_bytes:
                    pre_errors.append((rel, "file_too_large"))
                    continue
                try:
                    sources[rel] = py_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    pre_errors.append((rel, "decode_error"))
        elif path.is_file():
            file_count += 1
            if file_count > max_files:
                raise DeadCodeError("too_many_files")
            if path.suffix != ".py":
                continue
            rel = path.name
            if path.stat().st_size > max_file_bytes:
                pre_errors.append((rel, "file_too_large"))
                continue
            try:
                sources[rel] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                pre_errors.append((rel, "decode_error"))
        else:
            raise DeadCodeError("invalid_path", f"Path is not a file or directory: {path}")

    report = scan_sources(sources, whitelist=whitelist)
    return Report(report.findings, pre_errors + report.errors)


def format_text(report: Report) -> str:
    """Return a human-readable one-line-per-finding string."""
    lines: list[str] = []
    for finding in report.findings:
        kind = finding.kind.replace("_", " ")
        lines.append(
            f"{finding.module}:{finding.line}: {kind} '{finding.name}' ({finding.confidence}%)"
        )
    return "\n".join(lines)


def format_json(report: Report) -> str:
    """Return the report as an indented JSON string with sorted keys."""
    data = {
        "findings": [
            {
                "kind": f.kind,
                "name": f.name,
                "module": f.module,
                "line": f.line,
                "confidence": f.confidence,
            }
            for f in report.findings
        ],
        "errors": [list(err) for err in report.errors],
    }
    return json.dumps(data, indent=2, sort_keys=True)
