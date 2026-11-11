"""Tests for dead_code_finder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dead_code_finder import (
    DeadCodeError,
    Finding,
    Report,
    format_json,
    format_text,
    scan,
    scan_sources,
)


def test_unused_import() -> None:
    sources = {"a": "import os\nimport sys\nprint(sys.argv)\n"}
    report = scan_sources(sources)
    assert report.findings == [
        Finding(kind="unused_import", name="os", module="a", line=1, confidence=90)
    ]
    assert report.errors == []


def test_import_alias_binds_alias() -> None:
    sources = {"a": "import os as operating\nimport sys\nprint(sys.argv)\n"}
    report = scan_sources(sources)
    assert report.findings == [
        Finding("unused_import", "operating", "a", 1, 90),
    ]


def test_import_dotted_binds_first_segment() -> None:
    sources = {"a": "import os.path\nimport sys\nprint(sys.argv)\n"}
    report = scan_sources(sources)
    assert report.findings == [
        Finding("unused_import", "os", "a", 1, 90),
    ]


def test_from_import_binds_name() -> None:
    sources = {"a": "from os import path\nimport sys\nprint(sys.argv)\n"}
    report = scan_sources(sources)
    assert report.findings == [
        Finding("unused_import", "path", "a", 1, 90),
    ]


def test_star_import_ignored() -> None:
    sources = {"a": "from os import *\nprint(sys.argv)\n"}
    report = scan_sources(sources)
    assert report.findings == []


def test_unused_function() -> None:
    sources = {"a": "def used():\n    return 1\n\ndef unused():\n    return 2\n\nused()\n"}
    report = scan_sources(sources)
    assert report.findings == [Finding("unused_function", "unused", "a", 4, 60)]


def test_cross_module_used() -> None:
    sources = {
        "a": "def helper():\n    pass\n",
        "b": "from a import helper\nhelper()\n",
    }
    report = scan_sources(sources)
    assert report.findings == []


def test_unused_class() -> None:
    sources = {"a": "class Used:\n    pass\n\nclass Unused:\n    pass\n\nUsed()\n"}
    report = scan_sources(sources)
    assert report.findings == [Finding("unused_class", "Unused", "a", 4, 60)]


def test_base_class_reference_counts() -> None:
    # 'Base' is only referenced as a base class; 'Child' is instantiated.
    sources = {"a": "class Base:\n    pass\n\nclass Child(Base):\n    pass\n\nChild()\n"}
    report = scan_sources(sources)
    assert report.findings == []


def test_decorator_reference_counts() -> None:
    sources = {"a": "def deco(f):\n    return f\n\n@deco\ndef func():\n    pass\n"}
    report = scan_sources(sources)
    assert report.findings == []


def test_unused_method() -> None:
    sources = {"a": "class C:\n    def m(self):\n        pass\n\nC()\n"}
    report = scan_sources(sources)
    assert report.findings == [Finding("unused_method", "m", "a", 2, 60)]


def test_used_method_via_attribute() -> None:
    sources = {"a": "class C:\n    def m(self):\n        pass\n\nC().m()\n"}
    report = scan_sources(sources)
    assert report.findings == []


def test_unused_variable() -> None:
    sources = {"a": "x = 1\ny = 2\nprint(y)\n"}
    report = scan_sources(sources)
    assert report.findings == [Finding("unused_variable", "x", "a", 1, 60)]


def test_annassign_variable() -> None:
    sources = {"a": "x: int = 1\ny: int = 2\nprint(y)\n"}
    report = scan_sources(sources)
    assert report.findings == [Finding("unused_variable", "x", "a", 1, 60)]


def test_annassign_without_value_is_not_a_definition() -> None:
    sources = {"a": "x: int\ny: int = 1\nprint(y)\n"}
    report = scan_sources(sources)
    assert report.findings == []


def test_future_import_not_reported() -> None:
    sources = {"a": "from __future__ import annotations\nx = 1\nprint(x)\n"}
    report = scan_sources(sources)
    assert report.findings == []


def test_unreachable_simple() -> None:
    sources = {"a": "def f():\n    return 1\n    print(2)\n\nf()\n"}
    report = scan_sources(sources)
    assert report.findings == [Finding("unreachable_code", "f", "a", 3, 100)]


def test_unreachable_raise_in_if() -> None:
    sources = {
        "a": "def f(x):\n    if x:\n        raise ValueError()\n        print('bad')\n    return 1\nf(0)\n"
    }
    report = scan_sources(sources)
    assert report.findings == [Finding("unreachable_code", "f", "a", 4, 100)]


def test_unreachable_module_level() -> None:
    sources = {"a": "return\nprint('never')\n"}
    report = scan_sources(sources)
    # ast.parse accepts a top-level return, and the statement after it is
    # unreachable; the reported name is '<module>'.
    assert report.findings == [Finding("unreachable_code", "<module>", "a", 2, 100)]
    assert report.errors == []


def test_unreachable_after_continue_in_loop() -> None:
    sources = {"a": "for i in range(3):\n    continue\n    print(i)\n"}
    report = scan_sources(sources)
    assert report.findings == [Finding("unreachable_code", "<module>", "a", 3, 100)]


def test_exemptions_dunder_and_all_and_string_and_whitelist() -> None:
    sources = {
        "a": (
            "__all__ = ['api']\n"
            "def api():\n"
            "    pass\n"
            "class X:\n"
            "    def __repr__(self):\n"
            "        return 'X'\n"
            "def handler():\n"
            "    pass\n"
            "getattr(obj, 'handler')\n"
            "def cli_runner():\n"
            "    pass\n"
        )
    }
    report = scan_sources(sources, whitelist=["cli_*"])
    assert report.findings == []


def test_exempt_setup_teardown_in_test_file() -> None:
    sources = {
        "test_things.py": (
            "class TestExample:\n"
            "    def setUp(self):\n"
            "        pass\n"
            "    def tearDown(self):\n"
            "        pass\n"
            "    def test_feature(self):\n"
            "        pass\n"
        )
    }
    report = scan_sources(sources)
    assert report.findings == []


def test_decorated_function_exempt_by_default() -> None:
    sources = {"a": "def deco(f):\n    return f\n\n@deco\ndef func():\n    pass\n"}
    report = scan_sources(sources)
    assert report.findings == []


def test_decorated_function_included_confidence_50() -> None:
    sources = {"a": "def deco(f):\n    return f\n\n@deco\ndef func():\n    pass\n"}
    report = scan_sources(sources, include_decorated=True)
    assert report.findings == [Finding("unused_function", "func", "a", 5, 50)]


def test_overload_always_exempt() -> None:
    sources = {
        "a": (
            "import typing\n"
            "@typing.overload\n"
            "def f(x: int) -> int: ...\n"
            "@typing.overload\n"
            "def f(x: str) -> str: ...\n"
        )
    }
    report = scan_sources(sources)
    assert report.findings == []


def test_scan_errors_syntax_and_large_and_decode(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def (\n")
    (tmp_path / "good.py").write_text("import os\n")
    large = tmp_path / "large.py"
    large.write_text("x" * 11)
    bad_bytes = tmp_path / "bad_bytes.py"
    bad_bytes.write_bytes(b"\xff\xfe")

    report = scan([tmp_path], max_file_bytes=10)
    assert ("bad.py", "syntax_error") in report.errors
    assert ("large.py", "file_too_large") in report.errors
    assert ("bad_bytes.py", "decode_error") in report.errors
    assert any(f.module == "good.py" and f.kind == "unused_import" for f in report.findings)


def test_scan_null_byte_records_syntax_error_and_keeps_scanning(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_bytes(b"x = 1\x00\n")
    (tmp_path / "good.py").write_text("import os\n")
    report = scan([tmp_path])
    assert ("a.py", "syntax_error") in report.errors
    assert any(f.module == "good.py" and f.kind == "unused_import" for f in report.findings)


def test_scan_too_many_files(tmp_path: Path) -> None:
    (tmp_path / "1.py").write_text("import os\n")
    (tmp_path / "2.py").write_text("import sys\n")
    with pytest.raises(DeadCodeError) as exc_info:
        scan([tmp_path], max_files=1)
    assert exc_info.value.code == "too_many_files"


def test_scan_invalid_path(tmp_path: Path) -> None:
    with pytest.raises(DeadCodeError) as exc_info:
        scan([tmp_path / "nonexistent"])
    assert exc_info.value.code == "invalid_path"


def test_scan_relative_module_key(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "mod.py").write_text("def unused():\n    pass\n")
    report = scan([tmp_path])
    expected_module = "sub/mod.py"
    assert report.findings == [Finding("unused_function", "unused", expected_module, 1, 60)]


def test_format_text() -> None:
    findings = [
        Finding("unused_import", "os", "a.py", 1, 90),
        Finding("unused_function", "unused", "a.py", 2, 60),
    ]
    report = Report(findings, [])
    text = format_text(report)
    assert text == ("a.py:1: unused import 'os' (90%)\na.py:2: unused function 'unused' (60%)")


def test_format_json() -> None:
    report = Report(
        [Finding("unused_import", "os", "a.py", 1, 90)],
        [("bad.py", "syntax_error")],
    )
    data = json.loads(format_json(report))
    assert data == {
        "errors": [["bad.py", "syntax_error"]],
        "findings": [
            {
                "kind": "unused_import",
                "name": "os",
                "module": "a.py",
                "line": 1,
                "confidence": 90,
            }
        ],
    }


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import dead_code_finder.__main__ as main_mod

    p = tmp_path / "a.py"
    p.write_text("import os\n")

    assert main_mod.main([str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "a.py:1: unused import 'os' (90%)" in captured.out

    ok = tmp_path / "ok.py"
    ok.write_text("pass\n")
    assert main_mod.main([str(ok)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""

    # --min-confidence filters out 60% findings, but the 90% import remains.
    p2 = tmp_path / "b.py"
    p2.write_text("def unused():\n    pass\n")
    assert main_mod.main([str(tmp_path), "--min-confidence", "70"]) == 1
    captured = capsys.readouterr()
    assert "unused function" not in captured.out
    assert "unused import 'os'" in captured.out

    assert main_mod.main([str(tmp_path / "nope")]) == 2
    captured = capsys.readouterr()
    assert "Path does not exist" in captured.err


def test_cli_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import dead_code_finder.__main__ as main_mod

    p = tmp_path / "a.py"
    p.write_text("import os\n")
    rc = main_mod.main([str(p), "--json"])
    assert rc == 1
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["findings"][0]["name"] == "os"


def test_dead_code_error_repr() -> None:
    err = DeadCodeError("invalid_path")
    assert err.code == "invalid_path"
    assert str(err) == "invalid_path"
