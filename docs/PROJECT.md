# Project record

## Objective

Find dead Python code with `ast` across a set of modules: unused imports, functions, classes, methods and module-level variables, plus unreachable statements, with confidence scores.

## Scope

- In scope: `scan_sources` over an in-memory `Mapping[str, str]` and `scan` over directories or individual `.py` files.
- In scope: name-based whole-program analysis using `ast.Name` loads, attribute attributes, `from` imports, string constants that are valid identifiers, and `__all__` names.
- In scope: findings for `unused_import`, `unused_function`, `unused_class`, `unused_method`, `unused_variable` and `unreachable_code`, with fixed per-kind confidence.
- In scope: text and JSON formatting, file and module error reporting, `max_file_bytes`, `max_files`, `exclude`, `whitelist`, `include_decorated`, and the `dead-code-finder` CLI.
- Out of scope: type inference, attribute resolution by class, unused arguments, dynamic imports, notebooks and auto-deletion.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 839500 / 78951 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.1084 |

## Factory run u278 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-11 | generation | deepseek-v4-pro | yes | 1711 | 25701 | 0 | 3328 | 0.0521 |
| 2026-11-11 | fix-1 | deepseek-flash | no | 14014 | 4034 | 0 | 176896 | 0.0051 |
| 2026-11-11 | fix-2 | deepseek-flash | no | 9203 | 3444 | 0 | 31360 | 0.0035 |
| 2026-11-11 | audit | deepseek-flash | no | 23076 | 28128 | 0 | 411648 | 0.0216 |
| 2026-11-11 | fix-3 | deepseek-flash | no | 10294 | 1872 | 0 | 65920 | 0.0029 |
| 2026-11-11 | docs | deepseek-flash | no | 91794 | 15772 | 0 | 256 | 0.0232 |

Total: $0.1084. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
