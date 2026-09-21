"""CLI entry point for target-ecosystem label-efficiency evaluation."""

from __future__ import annotations

import argparse
import json

from src.label_efficiency import evaluate_label_efficiency


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure how target labels improve cross-ecosystem static transfer.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", default="outputs/label_efficiency")
    parser.add_argument("--budgets", nargs="+", type=int, default=[0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 200, 400])
    parser.add_argument("--n-seeds", type=int, default=8)
    parser.add_argument("--pool-fraction", type=float, default=0.65)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--no-xgboost", action="store_true")
    args = parser.parse_args()
    result = evaluate_label_efficiency(
        args.dataset,
        args.output,
        budgets=args.budgets,
        n_seeds=args.n_seeds,
        pool_fraction=args.pool_fraction,
        random_state=args.random_state,
        prefer_xgboost=not args.no_xgboost,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()