# Testing

## Running

```sh
pytest tests/test_dead_code_finder.py
```

## Policy

- Tests call the public `scan_sources` API and assert exact `Report.findings` and `Report.errors` values using `Finding` objects.
- Cases are deterministic and in-memory; they do not use the network, wall clock or test-order dependence.
- The test module covers import binding, cross-module references, unused definitions, base-class references, decorator references and method references.

## Tiers

- The source contains one pytest tier: `tests/test_dead_code_finder.py`.
- No marker-based CI/conformance tier or external-tool setup is present in this source tree.

## Layout

`tests/test_dead_code_finder.py` is the test module. Its tests include:

- `test_unused_import`, `test_import_alias_binds_alias`, `test_import_dotted_binds_first_segment`, `test_from_import_binds_name`, `test_star_import_ignored`: import binding and unused-import reporting.
- `test_unused_function`, `test_cross_module_used`, `test_unused_class`, `test_base_class_reference_counts`, `test_decorator_reference_counts`, `test_unused_method`: definition references and unused definitions.
