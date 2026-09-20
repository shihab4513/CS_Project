"""CLI entry point for read-only source inspection."""

from __future__ import annotations

import argparse
import json

from src.source_scan import write_source_scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only static scan for an unpacked npm/PyPI source directory.")
    parser.add_argument("--source-dir", required=True, help="Local directory containing already unpacked source files")
    parser.add_argument("--output", default="outputs/source_scan.json", help="JSON result path")
    parser.add_argument(
        "--include-nonproduction",
        action="store_true",
        help="Include tests, docs, examples, and CI configuration in risk scoring.",
    )
    args = parser.parse_args()
    result = write_source_scan(args.source_dir, args.output, include_nonproduction=args.include_nonproduction)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
