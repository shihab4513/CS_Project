import json
import tempfile
import unittest
from pathlib import Path

from src.triage_evaluation import evaluate_triage_policy


class TriageEvaluationTests(unittest.TestCase):
    def test_reports_referral_and_disagreement(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "input.csv"
            output = Path(temp) / "result.json"
            source.write_text(
                "package_name,ecosystem,static_probability,dynamic_probability,ground_truth\n"
                "a,NPM,0.5,,0\n"
                "b,PyPI,0.9,0.1,1\n",
                encoding="utf-8",
            )
            payload = evaluate_triage_policy(source, output)
            saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["dynamic_referral_rate"], 0.5)
        self.assertEqual(saved["summary"]["modality_disagreement_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
