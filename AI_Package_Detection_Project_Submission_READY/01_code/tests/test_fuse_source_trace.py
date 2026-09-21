import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class FuseSourceTraceTests(unittest.TestCase):
    def test_fusion_creates_evidence_report(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            source_scan = work / "source_scan.json"
            source_scan.write_text(
                json.dumps({"static_source_risk_score": 0.3, "findings": []}), encoding="utf-8"
            )
            trace = work / "trace.json"
            trace.write_text(json.dumps({"observed": {}}), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    "fuse_source_trace.py",
                    "--source-scan",
                    str(source_scan),
                    "--trace",
                    str(trace),
                    "--package-name",
                    "test-package",
                    "--ecosystem",
                    "NPM",
                    "--output",
                    str(work / "out"),
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads((work / "out" / "new_package_evidence_report.json").read_text())
        self.assertEqual(report["package"]["package_name"], "test-package")
        self.assertEqual(report["behavior_agent"]["risk_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
