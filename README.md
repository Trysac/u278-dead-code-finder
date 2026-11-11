# dead-code-finder

[![PyPI version](https://img.shields.io/pypi/v/trysac-dead-code-finder)](https://pypi.org/project/trysac-dead-code-finder/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-dead-code-finder)](LICENSE)
[![CI](https://github.com/Trysac/u278-dead-code-finder/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u278-dead-code-finder/actions/workflows/ci.yml)

Find dead Python code with ast across a set of modules: unused imports, functions, classes and methods, plus unreachable statements, with confidence scores

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-dead-code-finder
# or
uv add trysac-dead-code-finder
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import dead_code_finder

# normalize() trims surrounding whitespace and lower-cases the text.
print(dead_code_finder.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    dead_code_finder.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
