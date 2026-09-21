from src.agents import static_analysis_agent


def test_heuristic_source_score_is_not_described_as_probability() -> None:
    result = static_analysis_agent(
        {
            "package_name": "lodash-4.17.21",
            "static_malicious_probability": 0.3,
            "model_name": "Read-only rule-based source scanner",
            "evidence_type": "heuristic_source_score",
        }
    )

    assert "heuristic risk score" in result["finding"]
    assert "not a calibrated malicious probability" in result["finding"]
