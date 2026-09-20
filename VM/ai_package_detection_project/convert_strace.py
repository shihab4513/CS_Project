"""CLI entry point for converting a Linux strace log into dynamic trace JSON."""

from __future__ import annotations

import argparse
import json

from src.strace_adapter import write_trace


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert an existing isolated-VM strace log; does not execute a package.")
    parser.add_argument("--log", required=True, help="Path to an existing strace text log")
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--ecosystem", required=True, choices=["NPM", "PyPI"])
    parser.add_argument("--output", default="outputs/imported_trace.json")
    args = parser.parse_args()
    trace = write_trace(args.log, args.package_name, args.ecosystem, args.output)
    print(json.dumps(trace, indent=2))


if __name__ == "__main__":
    main()
