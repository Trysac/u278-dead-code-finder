# dead-code-finder

[![PyPI version](https://img.shields.io/pypi/v/trysac-dead-code-finder)](https://pypi.org/project/trysac-dead-code-finder/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-dead-code-finder)](LICENSE)
[![CI](https://github.com/Trysac/u278-dead-code-finder/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u278-dead-code-finder/actions/workflows/ci.yml)

Find dead Python code with ast across a set of modules: unused imports, functions, classes and methods, plus unreachable statements, with confidence scores

## Problem

Python projects accumulate functions nobody calls and imports nobody uses, which slows reviews and hides real dependencies. Linters flag unused imports per file but not a function that no other module references, and whole-program tools report so many false positives that teams ignore them. This library builds one name-reference index across all scanned modules, honours `__all__`, dunders, string references and a whitelist, and scores each finding.

## Install

```sh
pip install trysac-dead-code-finder
# or
uv add trysac-dead-code-finder
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
from dead_code_finder import Finding, format_text, scan_sources

report = scan_sources({"a.py": "import os\nprint(2)\n"})
assert report.findings == [Finding("unused_import", "os", "a.py", 1, 90)]
print(format_text(report))
# a.py:1: unused import 'os' (90%)
```

Or scan a directory from the command line:

```sh
dead-code-finder src --min-confidence 70
```

Analysis is name-based: a name counts as referenced anywhere in the scanned set, so any attribute access such as `x.m` keeps every method named `m`.

## Public API

- `scan_sources(sources, *, whitelist=(), include_decorated=False) -> Report` parses an in-memory `Mapping[str, str]` keyed by module name.
- `scan(paths, *, whitelist=(), max_file_bytes=1_000_000, max_files=5000, exclude=(".venv", ".git", "__pycache__")) -> Report` reads directories recursively or individual `.py` files. Directory module keys are POSIX paths relative to the scanned root; an individual file uses `path.name`.
- `format_text(report) -> str` returns one line per finding: `{module}:{line}: {kind with _ replaced by space} '{name}' ({confidence}%)`.
- `format_json(report) -> str` returns `{"errors": [...], "findings": [...]}` with sorted keys and two-space indentation.
- `Finding` is a frozen dataclass with `kind`, `name`, `module`, `line`, `confidence`. `Report` is a frozen dataclass with `findings` and `errors`.
- `DetectionKind` is one of `unused_import`, `unused_function`, `unused_class`, `unused_method`, `unused_variable`, `unreachable_code`.

Confidence is 90 for `unused_import`, 60 for `unused_function`, `unused_class`, `unused_method` and `unused_variable`, 100 for `unreachable_code`, and 50 for a decorated function or method when `include_decorated=True`. Unreachable code is the first statement after `return`, `raise`, `continue` or `break` in the same statement list and is reported once per block.

Exemptions: names in a module's `__all__`, dunder names, `_` alone, names matching a `whitelist` fnmatch pattern, `test_*` functions and `Test*` classes in files named `test_*.py` or `*_test.py`, methods named `setUp` or `tearDown`, functions decorated with `typing.overload`, and decorated functions or methods unless `include_decorated=True`.

Errors and limits: `DeadCodeError(code)` has code `invalid_path` or `too_many_files`. Per-file problems are returned in `Report.errors` with codes `syntax_error`, `file_too_large`, `decode_error` and `too_deep`. `scan` skips files larger than `max_file_bytes`, raises when more than `max_files` `.py` files are considered, and skips directory parts matching `exclude`. `scan_sources` has no file-size or module-count limit. Findings are sorted by `(module, line, name)`.

CLI: `dead-code-finder PATH... [--min-confidence N] [--whitelist PATTERN] [--json]`. It exits 0 with no findings at or above the threshold, 1 with findings, and 2 on usage, path or read errors.

## Why not vulture

Vulture is the common whole-program alternative. This utility uses a smaller documented rule set with explicit per-kind confidence, credits string references and `__all__`, and exposes a pure `scan_sources` API for tests and tooling.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [testing](docs/TESTING.md)
- [Security](docs/SECURITY.md), [project record](docs/PROJECT.md) and [stack](docs/STACK.md)

## License

[MIT](LICENSE)
