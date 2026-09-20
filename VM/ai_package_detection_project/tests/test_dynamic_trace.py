import unittest

from src.dynamic_trace import analyse_trace


class DynamicTraceTests(unittest.TestCase):
    def test_trace_with_sensitive_access_scores_higher(self):
        result = analyse_trace(
            {
                "observed": {
                    "install_hooks": ["postinstall"],
                    "commands": ["curl https://example.invalid/a"],
                    "processes": [],
                    "files_read": ["/home/user/.ssh/id_rsa"],
                    "files_written": [],
                    "network_connections": ["https://example.invalid"],
                }
            }
        )
        self.assertGreaterEqual(result["dynamic_risk_score"], 0.8)
        self.assertEqual(result["counts"]["sensitive_path_accesses"], 1)

    def test_empty_trace_is_low_risk(self):
        result = analyse_trace({"observed": {}})
        self.assertEqual(result["dynamic_risk_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
