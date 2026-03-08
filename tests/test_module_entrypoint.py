"""Smoke tests for the package entry point."""

from __future__ import annotations

import subprocess
import sys
import unittest


class TestModuleEntrypoint(unittest.TestCase):
    def test_python_m_src_shows_cli_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "src", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Info Aggregator CLI", result.stdout)


if __name__ == "__main__":
    unittest.main()
