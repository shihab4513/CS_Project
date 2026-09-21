import tempfile
import unittest
from pathlib import Path

from src.source_scan import scan_source_directory


class SourceScanTests(unittest.TestCase):
    def test_scan_reports_static_signals_without_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text('{"scripts":{"postinstall":"node setup.js"}}', encoding="utf-8")
            (root / "setup.js").write_text("require('child_process'); fetch('https://example.invalid')", encoding="utf-8")
            result = scan_source_directory(root)
        signals = {finding["signal"] for finding in result["findings"]}
        self.assertIn("install_hook", signals)
        self.assertIn("shell_execution", signals)
        self.assertIn("network_access", signals)
        self.assertGreater(result["static_source_risk_score"], 0.0)

    def test_network_and_sensitive_signals_are_contextual(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "client.py").write_text(
                "import requests\npath = '.ssh/id_rsa'\nrequests.get('https://example.invalid')",
                encoding="utf-8",
            )
            result = scan_source_directory(root)
        self.assertEqual(result["static_source_risk_score"], 0.2)

    def test_test_fixtures_are_excluded_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests").mkdir()
            (root / "tests" / "fixture.py").write_text("token = '.ssh/id_rsa'", encoding="utf-8")
            result = scan_source_directory(root)
        self.assertEqual(result["static_source_risk_score"], 0.0)
        self.assertEqual(result["nonproduction_files_excluded_from_risk_scoring"], 1)


if __name__ == "__main__":
    unittest.main()
