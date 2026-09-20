"""Aggregate metrics for the evidence-aware triage policy.

The input is an analyst-prepared CSV. Each row represents one package and must
include ``package_name``, ``ecosystem``, and ``static_probability``. Optional
columns are ``ground_truth``, ``dynamic_probability``, and
``dynamic_analysis_seconds``. This module never executes a package.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from .triage import evidence_aware_triage


REQUIRED_COLUMNS = {"package_name", "ecosystem", "static_probability"}


def evaluate_triage_policy(input_csv: str | Path, output_json: str | Path) -> dict[str, Any]:
    """Report workflow cost, evidence coverage, and optional labelled metrics."""
    frame = pd.read_csv(input_csv)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    has_dynamic = "dynamic_probability" in frame.columns
    records: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        dynamic = None
        if has_dynamic and pd.notna(row["dynamic_probability"]):
            dynamic = float(row["dynamic_probability"])
        triage = evidence_aware_triage(float(row["static_probability"]), dynamic)
        records.append(
            {
                "package_name": str(row["package_name"]),
                "ecosystem": str(row["ecosystem"]),
                "static_probability": round(float(row["static_probability"]), 4),
                "dynamic_probability": dynamic,
                **triage,
            }
        )
    decisions = pd.DataFrame(records)
    total = len(decisions)
    queued = decisions["action"].eq("queue_for_dynamic_analysis")
    review = decisions["action"].str.startswith("human_review_")
    disagreement = decisions["action"].eq("human_review_modality_disagreement")
    dynamic_available = decisions["dynamic_probability"].notna()
    summary: dict[str, Any] = {
        "input": str(Path(input_csv).resolve()),
        "packages": int(total),
        "dynamic_trace_available_rate": round(float(dynamic_available.mean()), 4),
        "dynamic_referral_rate": round(float(queued.mean()), 4),
        "human_review_rate": round(float(review.mean()), 4),
        "modality_disagreement_rate": round(float(disagreement.mean()), 4),
        "by_ecosystem": {},
    }
    if "dynamic_analysis_seconds" in frame.columns:
        durations = pd.to_numeric(frame["dynamic_analysis_seconds"], errors="coerce")
        summary["mean_dynamic_analysis_seconds"] = round(float(durations.dropna().mean()), 4) if durations.notna().any() else None
    if "ground_truth" in frame.columns:
        labels = pd.to_numeric(frame["ground_truth"], errors="raise").astype(int)
        static_predictions = (pd.to_numeric(frame["static_probability"]) >= 0.5).astype(int)
        final_predictions = (decisions["fused_score"] >= 0.5).astype(int)
        summary["labelled_static_metrics"] = _classification_metrics(labels, static_predictions)
        summary["labelled_triage_metrics"] = _classification_metrics(labels, final_predictions)
    for ecosystem, group in decisions.groupby("ecosystem"):
        summary["by_ecosystem"][str(ecosystem)] = {
            "packages": int(len(group)),
            "dynamic_trace_available_rate": round(float(group["dynamic_probability"].notna().mean()), 4),
            "dynamic_referral_rate": round(float(group["action"].eq("queue_for_dynamic_analysis").mean()), 4),
            "human_review_rate": round(float(group["action"].str.startswith("human_review_").mean()), 4),
        }
    payload = {"summary": summary, "records": records}
    Path(output_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _classification_metrics(labels: pd.Series, predictions: pd.Series) -> dict[str, float]:
    return {
        "precision": round(float(precision_score(labels, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, predictions, zero_division=0)), 4),
    }
