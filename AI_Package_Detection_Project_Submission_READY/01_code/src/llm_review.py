"""Bounded evidence preparation and output handling for a local LLM reviewer.

This module never loads a model, executes package code, or reads package source.
It only prepares a small, traceable summary from an evidence report that was
created earlier by the read-only scanner and imported VM telemetry pipeline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_evidence_report(path: str | Path) -> dict[str, Any]:
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Evidence report must contain one JSON object.")
    for key in ("package", "static_source_scan", "static_agent", "behavior_agent", "decision_agent"):
        if key not in report:
            raise ValueError(f"Evidence report is missing required field: {key}")
    return report


def build_bounded_evidence(report: dict[str, Any]) -> dict[str, Any]:
    """Keep only reviewed, explainable fields and avoid raw source/trace dumps."""
    source_scan = report["static_source_scan"]
    findings = [
        {
            "signal": finding.get("signal"),
            "match_count": finding.get("match_count"),
            "example_files": finding.get("files", [])[:3],
            "explanation": finding.get("explanation"),
        }
        for finding in source_scan.get("findings", [])
    ]
    return {
        "package": report["package"],
        "source_scan": {
            "heuristic_risk_score": source_scan.get("static_source_risk_score"),
            "findings": findings,
            "limitation": source_scan.get("limitation"),
        },
        "dynamic_evidence": {
            "risk_score": report["behavior_agent"].get("risk_score"),
            "finding": report["behavior_agent"].get("finding"),
        },
        "triage_policy": report["decision_agent"],
        "scope": report.get("scope"),
    }


def build_review_messages(evidence: dict[str, Any]) -> list[dict[str, str]]:
    payload = json.dumps(evidence, indent=2, ensure_ascii=True)
    return [
        {
            "role": "system",
            "content": (
                "You are a cautious software supply-chain security reviewer. Review only the supplied "
                "evidence. Do not invent behavior, do not claim package execution occurred, and do not "
                "override the evidence-aware triage action. A heuristic source score is not a calibrated "
                "malicious probability. A clean or limited trace is not proof of benignness."
            ),
        },
        {
            "role": "user",
            "content": (
                "Return exactly one JSON object with these fields: risk_level (low, medium, high, or "
                "insufficient_evidence), cited_evidence (array of short evidence statements), "
                "false_positive_considerations (array), safe_next_step (string), and limitations (array).\n\n"
                f"Evidence report summary:\n{payload}"
            ),
        },
    ]


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort parsing while preserving the original model response separately."""
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1) if fenced else stripped
    if not candidate.startswith("{"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def make_review_record(
    report: dict[str, Any], model_name: str, raw_response: str
) -> dict[str, Any]:
    return {
        "scope": (
            "Local LLM review of an already-created evidence report. The LLM received no package source "
            "code and did not install, download, or execute a package."
        ),
        "model": model_name,
        "bounded_evidence": build_bounded_evidence(report),
        "structured_review": extract_json_object(raw_response),
        "raw_model_response": raw_response,
        "limitation": (
            "The LLM output is reviewer assistance, not a ground-truth label or a replacement for "
            "sandbox isolation and human review."
        ),
    }
