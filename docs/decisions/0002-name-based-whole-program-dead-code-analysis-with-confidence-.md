# Name-based whole-program dead code analysis with confidence scores

Status: accepted (generated, pending human review)

## Context

The utility must find dead Python code across modules while keeping false positives manageable. A whole-program type-resolution approach would be large and slow; per-file linters miss cross-module usage.

## Decision

Implement a name-reference index across all scanned modules using Python's ast. Pass 1 collects definitions (functions, classes, methods, module-level variables, imports). Pass 2 collects all name references: Name loads, attribute names, string constants that are identifiers, from-import names, and __all__ entries. A definition is dead if its name never appears in the reference set, modulo exemptions. Unreachable code is detected structurally (first statement after return/raise/continue/break in a block). Confidence levels are assigned per kind: imports 90, other dead definitions 60 (50 for decorated definitions when include_decorated=True), unreachable 100.

## Consequences

The analysis is simple, deterministic, and fast. It deliberately ignores attribute resolution by class, type inference, aliasing, and dynamic constructs; this is documented as an imprecision. Exemptions (dunders, __all__, test scaffolding, whitelist, decorated functions, typing.overload) reduce noise.
