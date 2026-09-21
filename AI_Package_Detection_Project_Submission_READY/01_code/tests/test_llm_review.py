import unittest

from src.llm_review import build_bounded_evidence, extract_json_object


class LocalLlmReviewTests(unittest.TestCase):
    def test_bounded_evidence_excludes_raw_file_dump(self):
        report = {
            "package": {"package_name": "demo", "ecosystem": "NPM"},
            "static_source_scan": {
                "static_source_risk_score": 0.2,
                "findings": [{"signal": "network_access", "match_count": 1, "files": ["a.js"]}],
                "limitation": "heuristic only",
                "files_read": ["must not be copied"],
            },
            "static_agent": {"risk_score": 0.2},
            "behavior_agent": {"risk_score": 0.1, "finding": "No configured signal."},
            "decision_agent": {"action": "record_multimodal_low_risk"},
        }
        evidence = build_bounded_evidence(report)
        self.assertNotIn("files_read", evidence["source_scan"])
        self.assertEqual(evidence["source_scan"]["findings"][0]["example_files"], ["a.js"])

    def test_extract_json_object_accepts_fenced_response(self):
        result = extract_json_object('```json\n{"risk_level": "low"}\n```')
        self.assertEqual(result, {"risk_level": "low"})


if __name__ == "__main__":
    unittest.main()
