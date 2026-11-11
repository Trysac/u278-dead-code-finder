"""Behavior tests for the public API of dead_code_finder."""

from __future__ import annotations

import pytest

import dead_code_finder


def test_normalize_trims_and_lowercases() -> None:
    assert dead_code_finder.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        dead_code_finder.normalize(value)


def test_version_is_semver() -> None:
    parts = dead_code_finder.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
