"""CLI entry point for workflow-level triage evaluation."""

from __future__ import annotations

import argparse
import json

from src.triage_evaluation import evaluate_triage_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure triage workload and evidence coverage from an analyst-prepared CSV.")
    parser.add_argument("--input", required=True, help="CSV with package_name, ecosystem, static_probability and optional dynamic columns")
    parser.add_argument("--output", default="outputs/triage_policy_metrics.json")
    args = parser.parse_args()
    print(json.dumps(evaluate_triage_policy(args.input, args.output), indent=2))


if __name__ == "__main__":
    main()
