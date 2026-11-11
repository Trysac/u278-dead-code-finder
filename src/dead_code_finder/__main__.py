"""Command-line interface for dead-code detection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dead_code_finder import DeadCodeError, format_json, format_text, scan


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Returns:
        0 if no findings, 1 if findings, 2 on usage or path errors.
    """
    parser = argparse.ArgumentParser(prog="dead-code-finder")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--min-confidence", type=int, default=60)
    parser.add_argument("--whitelist", action="append", default=[])
    parser.add_argument("--json", action="store_true")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    try:
        report = scan(
            args.paths,
            whitelist=args.whitelist,
        )
    except DeadCodeError as exc:
        print(f"dead-code-finder: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"dead-code-finder: {exc}", file=sys.stderr)
        return 2

    filtered = [finding for finding in report.findings if finding.confidence >= args.min_confidence]
    filtered_report = type(report)(filtered, report.errors)

    if args.json:
        print(format_json(filtered_report))
    else:
        output = format_text(filtered_report)
        if output:
            print(output)
    return 1 if filtered else 0


if __name__ == "__main__":
    raise SystemExit(main())
