"""Evidence-fusion agents and an LLM-ready review prompt generator."""

from __future__ import annotations

from typing import Any

from .triage import evidence_aware_triage


def static_analysis_agent(static_prediction: dict[str, Any]) -> dict[str, Any]:
    score = float(static_prediction["static_malicious_probability"])
    evidence_type = static_prediction.get("evidence_type", "model_probability")
    if evidence_type == "heuristic_source_score":
        finding = (
            f"The read-only source scanner assigned a heuristic risk score of {score:.2%} to "
            f"{static_prediction['package_name']}. This is not a calibrated malicious probability."
        )
    else:
        finding = (
            f"The {static_prediction['model_name']} static model assigned a malicious probability of "
            f"{score:.2%} to {static_prediction['package_name']}."
        )
    return {
        "agent": "Static Analysis Agent",
        "risk_score": score,
        "evidence_type": evidence_type,
        "finding": finding,
    }


def behavior_analysis_agent(dynamic_summary: dict[str, Any] | None) -> dict[str, Any]:
    if dynamic_summary is None:
        return {
            "agent": "Behavior Analysis Agent",
            "risk_score": None,
            "finding": "No sandbox trace was supplied; dynamic evidence is unavailable.",
        }
    return {
        "agent": "Behavior Analysis Agent",
        "risk_score": dynamic_summary["dynamic_risk_score"],
        "finding": " ".join(dynamic_summary["evidence"]),
    }


def decision_agent(static_prediction: dict[str, Any], dynamic_summary: dict[str, Any] | None) -> dict[str, Any]:
    static_score = float(static_prediction["static_malicious_probability"])
    dynamic_score = None if dynamic_summary is None else float(dynamic_summary["dynamic_risk_score"])
    triage = evidence_aware_triage(static_score, dynamic_score)
    return {
        "agent": "Decision Agent",
        "fused_risk_score": triage["fused_score"],
        "decision": triage["action"],
        "reason": triage["reason"],
        "policy": "Evidence-aware triage: queue uncertain static cases, review modality disagreement, and preserve incomplete-evidence limits.",
    }


def build_llm_review_prompt(report: dict[str, Any]) -> str:
    """Create a bounded evidence prompt; this function makes no external API call."""
    return "\n".join(
        [
            "You are a software supply-chain security reviewer.",
            "Assess only the evidence below. Do not invent behavior or claim execution occurred.",
            f"Package: {report['package']['package_name']} ({report['package']['ecosystem']})",
            f"Static evidence score: {report['static_agent']['risk_score']:.4f} "
            f"({report['static_agent'].get('evidence_type', 'model_probability')})",
            f"Dynamic evidence: {report['behavior_agent']['finding']}",
            f"Provisional decision: {report['decision_agent']['decision']}",
            "Return: (1) risk level, (2) cited evidence, (3) false-positive considerations, (4) a safe next validation step.",
        ]
    )
