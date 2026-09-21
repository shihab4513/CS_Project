import tempfile
import unittest
from pathlib import Path

from src.strace_adapter import convert_strace_log


class StraceAdapterTests(unittest.TestCase):
    def test_adapter_extracts_observations(self):
        log = '\n'.join(
            [
                'execve("/usr/bin/node", ["node", "install.js"], 0x0) = 0',
                'openat(AT_FDCWD, "/tmp/output", O_WRONLY|O_CREAT, 0666) = 3',
                'connect(3, {sa_family=AF_INET, sin_port=htons(443)}, 16) = 0',
            ]
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.log"
            path.write_text(log, encoding="utf-8")
            trace = convert_strace_log(path, "demo", "NPM")
        self.assertIn("/usr/bin/node", trace["observed"]["processes"])
        self.assertIn("/tmp/output", trace["observed"]["files_written"])
        self.assertEqual(len(trace["observed"]["network_connections"]), 1)


if __name__ == "__main__":
    unittest.main()
