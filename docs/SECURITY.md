# Security notes

## Threat model

### Defended

- Scanned source is parsed with `ast.parse`; it is not imported, `eval`ed, `exec`ed or deserialized. The library has no runtime dependencies and performs no network access.
- `scan` reads files as UTF-8, skips files larger than `max_file_bytes` (default 1,000,000) with `file_too_large`, records `UnicodeDecodeError` as `decode_error`, and raises `DeadCodeError("too_many_files")` when more than `max_files` (default 5000) files are considered.
- `scan_sources` records `syntax_error` for `SyntaxError` or `ValueError` and `too_deep` for `RecursionError` per module, then continues with the remaining modules.
- Directory scanning skips any path part matching `exclude` (default `.venv`, `.git`, `__pycache__`) by name or fnmatch pattern.
- The library logs through `logging.getLogger(__name__)` with a `NullHandler` and does not print. The CLI writes diagnostics to stderr and exits 2 on `DeadCodeError` or `OSError`.

### Not defended

- `scan_sources` has no file-size or module-count limit. Very large or deeply nested source strings can consume CPU or memory; `RecursionError` is caught around parsing but not every resource-exhaustion path.
- `scan` limits files by byte size and count, but it does not sandbox the process, enforce timeouts or isolate concurrent scans.
- Analysis is name-based: any attribute named `x.m` suppresses every method named `m` in the scanned set. This is a documented accuracy limit, not a security boundary.
- Output is not sanitized for terminal control sequences; module keys and paths come from caller input and file names.
- No authentication, authorization, secret handling or network behavior is part of the library or CLI.

## Publishing

No publishing tokens or credentials are stored in the source tree; release and publishing configuration are outside this utility.
