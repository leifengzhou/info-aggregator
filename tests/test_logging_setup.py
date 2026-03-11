"""Tests for shared logging configuration."""

from __future__ import annotations

import json
import io
import logging
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from src.logging_setup import (
    DEFAULT_LOG_FILE,
    make_run_id,
    resolve_run_log_path,
    setup_logging,
)


class TestLoggingSetup(unittest.TestCase):
    def test_setup_logging_writes_pretty_console_and_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "logs" / "app.log"
            stderr_buffer = io.StringIO()
            with redirect_stderr(stderr_buffer):
                setup_logging(level="DEBUG", log_file=log_path)

                logger = logging.getLogger("tests.logging")
                logger.info("test_event", extra={"topic": "ai-research", "count": 2})

            console_lines = [line for line in stderr_buffer.getvalue().splitlines() if line.strip()]
            self.assertGreaterEqual(len(console_lines), 2)
            self.assertIn("test_event", console_lines[-1])
            self.assertFalse(console_lines[-1].lstrip().startswith("{"))

            contents = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(contents), 2)
            payload = json.loads(contents[-1])
            self.assertEqual("INFO", payload["level"])
            self.assertEqual("tests.logging", payload["logger"])
            self.assertEqual("test_event", payload["message"])
            self.assertEqual("ai-research", payload["context"]["topic"])
            self.assertEqual(2, payload["context"]["count"])

    def test_resolve_run_log_path_appends_run_id_for_default_path(self) -> None:
        run_path = resolve_run_log_path(DEFAULT_LOG_FILE, "20260309_123000_000001")
        self.assertEqual(
            Path("data/logs/info-aggregator_20260309_123000_000001.log"),
            run_path,
        )

    def test_make_run_id_contains_microseconds(self) -> None:
        run_id = make_run_id()
        self.assertRegex(run_id, r"^\d{8}_\d{6}_\d{6}$")

    def test_setup_logging_rejects_invalid_level(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "invalid log level"):
                setup_logging(level="NOT_A_LEVEL", log_file=Path(temp_dir) / "app.log")
