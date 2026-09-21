"""Fuse read-only source evidence and imported sandbox telemetry for a new package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.agents import behavior_analysis_agent, build_llm_review_prompt, decision_agent, static_analysis_agent
from src.dynamic_trace import analyse_trace, load_trace


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fuse a source-scan JSON and optional imported VM trace. No package code is executed."
    )
    parser.add_argument("--source-scan", required=True, help="JSON created by scan_source.py")
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--ecosystem", required=True, choices=["NPM", "PyPI"])
    parser.add_argument("--trace", help="Optional JSON created by convert_strace.py")
    parser.add_argument("--output", default="outputs", help="Directory for evidence report files")
    args = parser.parse_args()

    source_scan = json.loads(Path(args.source_scan).read_text(encoding="utf-8"))
    source_score = float(source_scan["static_source_risk_score"])
    # This score is transparent heuristic evidence, not a probability from the
    # paper-dataset ML model. The report keeps that distinction explicit.
    static_prediction = {
        "package_name": args.package_name,
        "ecosystem": args.ecosystem,
        "static_malicious_probability": source_score,
        "static_label": "suspicious" if source_score >= 0.5 else "not automatically suspicious",
        "reference_label": None,
        "model_name": "Read-only rule-based source scanner (not the paper-dataset ML model)",
        "evidence_type": "heuristic_source_score",
    }
    dynamic_summary = analyse_trace(load_trace(args.trace)) if args.trace else None
    report = {
        "scope": "New-package evidence fusion. No package script, dependency, or source code was executed by this program.",
        "static_source_scan": source_scan,
        "package": static_prediction,
        "static_agent": static_analysis_agent(static_prediction),
        "behavior_agent": behavior_analysis_agent(dynamic_summary),
        "decision_agent": decision_agent(static_prediction, dynamic_summary),
    }
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "new_package_evidence_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "new_package_llm_review_prompt.txt").write_text(build_llm_review_prompt(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote evidence report to: {output.resolve()}")


if __name__ == "__main__":
    main()
