# Architecture

## Purpose

`trysac-dead-code-finder` performs name-based whole-program analysis with `ast`: unused imports, functions, classes, methods, module-level variables and unreachable statements, with confidence scores.

## Shape

```text
caller
  -> dead_code_finder.scan_sources(sources)
       -> ast.parse each module
       -> collect definitions (module/class scope, module-level assignments and imports)
       -> collect references across all parsed modules
       -> append unused findings and unreachable findings
       -> sort by (module, line, name)
  -> dead_code_finder.scan(paths)
       -> discover and read .py files with limits and excludes
       -> call scan_sources
       -> merge file errors with parse errors
  -> format_text / format_json
  -> dead_code_finder.__main__.main -> CLI exit code
```

- **Public API**: the names in `__all__` of `src/dead_code_finder/__init__.py`.
- **Internal helpers**: underscore-prefixed functions in the same module collect definitions, references, exemptions and unreachable statements.
- **Errors**: `DeadCodeError(code)` with `invalid_path` or `too_many_files`; per-file and parse problems are returned in `Report.errors`.
- **Side effects**: `scan_sources` works on in-memory strings; `scan` reads files; the CLI prints. Library logging uses `logging.getLogger(__name__)` with a `NullHandler`.

## Quality contract

- The package ships `src/dead_code_finder/py.typed`.
- `Finding` and `Report` are frozen dataclasses.
- `tests/test_dead_code_finder.py` asserts exact findings and errors from `scan_sources`.
- The package imports only the Python standard library.

## Decisions

- Analysis is name-based across all scanned modules; attribute access such as `x.m` keeps every method named `m`.
- Confidence is fixed per kind: 90 for unused imports, 60 for unused functions, classes, methods and variables, 50 for decorated functions or methods with `include_decorated=True`, and 100 for unreachable code.
- Exemptions cover `__all__`, dunders, `_`, whitelist patterns, test functions and classes, `setUp`, `tearDown`, `typing.overload` and decorated definitions by default.
