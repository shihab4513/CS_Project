import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.label_efficiency import evaluate_label_efficiency


class LabelEfficiencyTests(unittest.TestCase):
    def test_writes_both_training_conditions_without_holdout_leakage(self):
        with tempfile.TemporaryDirectory() as temp:
            dataset = Path(temp) / "dataset.csv"
            output = Path(temp) / "output"
            rows = []
            for ecosystem in ("NPM", "PyPI"):
                for index in range(20):
                    rows.append(
                        {
                            "Malicious": int(index % 2 == 0),
                            "Package Repository": ecosystem,
                            "Package Name": f"{ecosystem}-{index}",
                            "feature_a": float(index),
                            "feature_b": float(index % 3),
                        }
                    )
            pd.DataFrame(rows).to_csv(dataset, index=False)
            result = evaluate_label_efficiency(
                dataset, output, budgets=[0, 2], n_seeds=2, pool_fraction=0.6, prefer_xgboost=False
            )
            saved = json.loads((output / "label_efficiency_summary.json").read_text(encoding="utf-8"))
            conditions = {row["condition"] for row in result["summary"]}
            raw_exists = (output / "label_efficiency_raw.csv").is_file()
        self.assertEqual(
            conditions,
            {"NPM + k PyPI", "k PyPI only", "PyPI + k NPM", "k NPM only"},
        )
        self.assertEqual(saved["budgets"], [0, 2])
        self.assertTrue(raw_exists)


if __name__ == "__main__":
    unittest.main()