"""CLI entry point for the npm/PyPI static-transfer experiment."""

from __future__ import annotations

import argparse
import json

from src.transfer_evaluation import evaluate_leave_one_ecosystem_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate static-model transfer between npm and PyPI.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", default="outputs/static_transfer_metrics.json")
    parser.add_argument("--no-xgboost", action="store_true")
    args = parser.parse_args()
    result = evaluate_leave_one_ecosystem_out(args.dataset, args.output, prefer_xgboost=not args.no_xgboost)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
