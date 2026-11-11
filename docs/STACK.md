# Stack

## Used

| Tool | Why |
|---|---|
| Python >= 3.10 | Uses `ast.Match` and `list[str]` syntax. |
| Python standard library | `ast`, `argparse`, `json`, `logging`, `pathlib`, `dataclasses`, `fnmatch`, `typing`, `collections.abc`. |
| pytest | Tests live in `tests/test_dead_code_finder.py` and are collected by pytest. |
| `py.typed` | Type marker at `src/dead_code_finder/py.typed`. |

## Discarded

| Tool | Why not |
|---|---|
| Third-party runtime dependencies | `allowed_dependencies` is empty; imports in `__init__.py` and `__main__.py` are standard library only. |
| Type inference and class-based attribute resolution | Explicitly out of scope; analysis is name-based. |
| Execution of scanned code | The library parses with `ast` and never imports or runs scanned modules. |
