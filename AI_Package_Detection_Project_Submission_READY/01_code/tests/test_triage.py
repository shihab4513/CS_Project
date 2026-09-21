import unittest

from src.triage import evidence_aware_triage


class TriageTests(unittest.TestCase):
    def test_uncertain_static_score_queues_dynamic_analysis(self):
        result = evidence_aware_triage(0.50)
        self.assertEqual(result["action"], "queue_for_dynamic_analysis")

    def test_disagreement_requires_review(self):
        result = evidence_aware_triage(0.90, dynamic_probability=0.10)
        self.assertEqual(result["action"], "human_review_modality_disagreement")

    def test_agreeing_low_scores_are_recorded(self):
        result = evidence_aware_triage(0.10, dynamic_probability=0.15)
        self.assertEqual(result["action"], "record_multimodal_low_risk")


if __name__ == "__main__":
    unittest.main()
