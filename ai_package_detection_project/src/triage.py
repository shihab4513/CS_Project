"""Evidence-aware triage for cross-ecosystem package assessment.

The policy deliberately abstains when the available evidence is incomplete or
contradictory. It does not claim that static/dynamic/LLM fusion is novel; its
research purpose is to make the cost, coverage, and disagreement of a fusion
policy measurable across npm and PyPI.
"""

from __future__ import annotations

from typing import Any


def evidence_aware_triage(
    static_probability: float,
    dynamic_probability: float | None = None,
    dynamic_budget_available: bool = True,
    review_band: tuple[float, float] = (0.25, 0.75),
    disagreement_threshold: float = 0.35,
) -> dict[str, Any]:
    """Return an auditable next action rather than a single overconfident label."""
    low, high = review_band
    if not 0.0 <= static_probability <= 1.0:
        raise ValueError("static_probability must be between 0 and 1")
    if dynamic_probability is not None and not 0.0 <= dynamic_probability <= 1.0:
        raise ValueError("dynamic_probability must be between 0 and 1")

    if dynamic_probability is None:
        if static_probability >= high:
            return {
                "action": "human_review_high_static_risk",
                "reason": "Static score is high, but no behavioral trace is available.",
                "fused_score": round(static_probability, 4),
                "requires_dynamic_trace": dynamic_budget_available,
            }
        if static_probability >= low and dynamic_budget_available:
            return {
                "action": "queue_for_dynamic_analysis",
                "reason": "Static evidence is uncertain; collect install-time evidence before a final verdict.",
                "fused_score": round(static_probability, 4),
                "requires_dynamic_trace": True,
            }
        return {
            "action": "record_static_only_low_risk",
            "reason": "Static score is below the review band; this is not a guarantee of benignness.",
            "fused_score": round(static_probability, 4),
            "requires_dynamic_trace": False,
        }

    difference = abs(static_probability - dynamic_probability)
    fused = 0.5 * static_probability + 0.5 * dynamic_probability
    if difference >= disagreement_threshold:
        action = "human_review_modality_disagreement"
        reason = "Static and dynamic evidence disagree beyond the configured threshold."
    elif fused >= high:
        action = "human_review_high_fused_risk"
        reason = "Both available modalities support a high-risk assessment."
    elif fused >= low:
        action = "human_review_ambiguous_fused_risk"
        reason = "Combined evidence remains in the review band."
    else:
        action = "record_multimodal_low_risk"
        reason = "Both available modalities produce a low combined score; record evidence and monitor limitations."
    return {
        "action": action,
        "reason": reason,
        "fused_score": round(fused, 4),
        "static_dynamic_difference": round(difference, 4),
        "requires_dynamic_trace": False,
    }
