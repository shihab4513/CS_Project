"""Run the safe hybrid package-detection research prototype."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.agents import behavior_analysis_agent, build_llm_review_prompt, decision_agent, static_analysis_agent
from src.dynamic_trace import analyse_trace, load_trace
from src.static_model import predict_known_package, train_static_model


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Static ML plus imported sandbox-trace evidence fusion.")
    parser.add_argument("--dataset", required=True, help="Path to the official Labelled_Dataset.csv")
    parser.add_argument("--output", default=str(ROOT / "outputs"), help="Directory for models and result files")
    parser.add_argument("--package-name", required=True, help="A Package Name that already appears in the dataset")
    parser.add_argument("--trace", help="Optional JSON sandbox trace. This file is read only; nothing is executed.")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--no-xgboost", action="store_true", help="Force the sklearn Random Forest fallback.")
    args = parser.parse_args()

    output = Path(args.output)
    static_output = output / "static"
    summary = train_static_model(
        args.dataset,
        static_output,
        random_state=args.random_state,
        prefer_xgboost=not args.no_xgboost,
    )
    static_prediction = predict_known_package(static_output / "static_model.joblib", args.dataset, args.package_name)
    dynamic_summary = analyse_trace(load_trace(args.trace)) if args.trace else None
    static_agent = static_analysis_agent(static_prediction)
    behavior_agent = behavior_analysis_agent(dynamic_summary)
    decision = decision_agent(static_prediction, dynamic_summary)
    report = {
        "experiment": {
            "scope": "Static classification on the released feature CSV plus offline sandbox-trace interpretation.",
            "safety": "This program does not download, install, or execute a package.",
            "static_training": summary,
        },
        "package": static_prediction,
        "static_agent": static_agent,
        "behavior_agent": behavior_agent,
        "decision_agent": decision,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "package_decision_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "llm_review_prompt.txt").write_text(build_llm_review_prompt(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote results to: {output.resolve()}")


if __name__ == "__main__":
    main()
