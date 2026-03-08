"""Tests for shared logging configuration."""

from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path

from src.logging_setup import setup_logging


class TestLoggingSetup(unittest.TestCase):
    def test_setup_logging_writes_json_lines_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "logs" / "app.log"
            setup_logging(level="DEBUG", log_file=log_path)

            logger = logging.getLogger("tests.logging")
            logger.info("test_event", extra={"topic": "ai-research", "count": 2})

            contents = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(contents), 2)
            payload = json.loads(contents[-1])
            self.assertEqual("INFO", payload["level"])
            self.assertEqual("tests.logging", payload["logger"])
            self.assertEqual("test_event", payload["message"])
            self.assertEqual("ai-research", payload["context"]["topic"])
            self.assertEqual(2, payload["context"]["count"])

    def test_setup_logging_rejects_invalid_level(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "invalid log level"):
                setup_logging(level="NOT_A_LEVEL", log_file=Path(temp_dir) / "app.log")
