"""Tests for the CLI entry point."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src.adapters.youtube import YouTubeIngestResult
from src.main import FetchSummary, _build_log_path, main, parse_since, run_fetch


_CONFIG_YAML = """\
topics:
  ai-research:
    name: "AI Research"
    description: "AI updates"
    relevance_threshold: 6
    schedule: "0 */4 * * *"
    digest: daily
    sources:
      youtube:
        - channel_id: "UC123456789"
      rss:
        - url: "https://example.com/feed.xml"
  politics-us:
    name: "Politics"
    description: "Politics updates"
    relevance_threshold: 7
    schedule: "0 */6 * * *"
    digest: daily
    sources:
      youtube:
        - channel_id: "UCabcdefghijk"
"""


class TestParseSince(unittest.TestCase):
    def test_parse_since_supports_date_only(self) -> None:
        parsed = parse_since("2026-03-08")
        self.assertEqual(datetime(2026, 3, 8, tzinfo=timezone.utc), parsed)

    def test_parse_since_defaults_naive_datetime_to_utc(self) -> None:
        parsed = parse_since("2026-03-08T15:30:00")
        self.assertEqual(timezone.utc, parsed.tzinfo)

    def test_parse_since_normalizes_offset_datetime_to_utc(self) -> None:
        parsed = parse_since("2026-03-08T15:30:00-05:00")
        self.assertEqual(datetime(2026, 3, 8, 20, 30, tzinfo=timezone.utc), parsed)


class TestBuildLogPath(unittest.TestCase):
    def test_returns_path_in_data_logs_dir(self) -> None:
        path = _build_log_path(datetime(2026, 3, 8, 16, 24, 19, tzinfo=timezone.utc))
        self.assertEqual(Path("data/logs"), path.parent)

    def test_filename_contains_iso_timestamp(self) -> None:
        path = _build_log_path(datetime(2026, 3, 8, 16, 24, 19, tzinfo=timezone.utc))
        self.assertRegex(path.name, r"^info-aggregator_\d{8}T\d{6}Z\.log$")

    def test_different_datetimes_produce_different_paths(self) -> None:
        first = _build_log_path(datetime(2026, 3, 8, 16, 24, 19, tzinfo=timezone.utc))
        second = _build_log_path(datetime(2026, 3, 8, 16, 24, 20, tzinfo=timezone.utc))
        self.assertNotEqual(first, second)


class TestRunFetch(unittest.TestCase):
    def test_run_fetch_processes_all_topics_and_skips_non_youtube_sources(self) -> None:
        calls: list[tuple[str, dict, Path, datetime | None, float]] = []

        def fake_ingestor(*, conn, topic, source_config, content_root, since, transcript_delay_seconds):
            calls.append((topic, source_config, content_root, since, transcript_delay_seconds))
            return YouTubeIngestResult(
                discovered=2,
                inserted=1,
                deduped=1,
                linked=2,
                missing_transcripts=0,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            summary = run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                youtube_ingestor=fake_ingestor,
            )

            self.assertEqual(2, summary.topics_processed)
            self.assertEqual(2, summary.youtube_sources_processed)
            self.assertEqual(4, summary.discovered)
            self.assertEqual(2, summary.inserted)
            self.assertEqual(2, summary.deduped)
            self.assertEqual(4, summary.linked)
            self.assertEqual(1, summary.skipped_sources)
            self.assertEqual(
                [
                    ("ai-research", {"channel_id": "UC123456789"}),
                    ("politics-us", {"channel_id": "UCabcdefghijk"}),
                ],
                [(topic, source_config) for topic, source_config, _root, _since, _delay in calls],
            )
            self.assertTrue(
                all(content_root.name == "youtube" for _topic, _source, content_root, _since, _delay in calls)
            )
            self.assertTrue(all(delay == 1.0 for _topic, _source, _root, _since, delay in calls))

    def test_run_fetch_topic_filter_limits_to_single_topic(self) -> None:
        calls: list[str] = []

        def fake_ingestor(*, conn, topic, source_config, content_root, since, transcript_delay_seconds):
            calls.append(topic)
            return YouTubeIngestResult(1, 1, 0, 1, 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            summary = run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                topic="politics-us",
                youtube_ingestor=fake_ingestor,
            )

            self.assertEqual(["politics-us"], calls)
            self.assertEqual(1, summary.topics_processed)

    def test_run_fetch_uses_configured_transcript_delay(self) -> None:
        delays: list[float] = []
        config_yaml = """\
settings:
  youtube_transcript_delay_seconds: 0.25
topics:
  ai-research:
    name: "AI Research"
    description: "AI updates"
    relevance_threshold: 6
    schedule: "0 */4 * * *"
    digest: daily
    sources:
      youtube:
        - channel_id: "UC123456789"
"""

        def fake_ingestor(*, conn, topic, source_config, content_root, since, transcript_delay_seconds):
            delays.append(transcript_delay_seconds)
            return YouTubeIngestResult(1, 1, 0, 1, 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                youtube_ingestor=fake_ingestor,
            )

        self.assertEqual([0.25], delays)

    def test_cli_since_overrides_topic_fetch_since(self) -> None:
        """CLI --since takes precedence over topic-level fetch_since."""
        received_since: list[datetime | None] = []
        config_yaml = """\
topics:
  ai-research:
    name: "AI Research"
    description: "AI updates"
    relevance_threshold: 6
    schedule: "0 */4 * * *"
    digest: daily
    fetch_since: "2025-01-01"
    sources:
      youtube:
        - channel_id: "UC123456789"
"""

        def fake_ingestor(*, conn, topic, source_config, content_root, since, transcript_delay_seconds):
            received_since.append(since)
            return YouTubeIngestResult(1, 1, 0, 1, 0)

        cli_since = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                since=cli_since,
                youtube_ingestor=fake_ingestor,
            )

        self.assertEqual([cli_since], received_since)

    def test_topic_fetch_since_used_when_no_cli_since(self) -> None:
        """topic.fetch_since is used when CLI --since is not passed."""
        received_since: list[datetime | None] = []
        config_yaml = """\
topics:
  ai-research:
    name: "AI Research"
    description: "AI updates"
    relevance_threshold: 6
    schedule: "0 */4 * * *"
    digest: daily
    fetch_since: "2025-01-01"
    sources:
      youtube:
        - channel_id: "UC123456789"
"""

        def fake_ingestor(*, conn, topic, source_config, content_root, since, transcript_delay_seconds):
            received_since.append(since)
            return YouTubeIngestResult(1, 1, 0, 1, 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(config_yaml, encoding="utf-8")

            run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                since=None,
                youtube_ingestor=fake_ingestor,
            )

        self.assertEqual([datetime(2025, 1, 1, tzinfo=timezone.utc)], received_since)

    def test_no_since_anywhere_passes_none(self) -> None:
        """Ingestor receives None when neither CLI --since nor topic.fetch_since is set."""
        received_since: list[datetime | None] = []

        def fake_ingestor(*, conn, topic, source_config, content_root, since, transcript_delay_seconds):
            received_since.append(since)
            return YouTubeIngestResult(1, 1, 0, 1, 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                since=None,
                youtube_ingestor=fake_ingestor,
            )

        self.assertTrue(all(s is None for s in received_since))

    def test_run_fetch_returns_run_id_in_summary(self) -> None:
        def fake_ingestor(*, conn, topic, source_config, content_root, since, transcript_delay_seconds):
            return YouTubeIngestResult(1, 1, 0, 1, 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            summary = run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                youtube_ingestor=fake_ingestor,
                run_id="20260308T162419Z",
            )

        self.assertEqual("20260308T162419Z", summary.run_id)


class TestMain(unittest.TestCase):
    @patch("src.main.setup_logging")
    @patch("src.main.run_fetch")
    def test_main_fetch_uses_generated_log_file_when_omitted(self, run_fetch_mock, setup_logging_mock) -> None:
        run_fetch_mock.return_value = FetchSummary(
            topics_processed=0,
            youtube_sources_processed=0,
            discovered=0,
            inserted=0,
            deduped=0,
            linked=0,
            missing_transcripts=0,
            skipped_sources=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            exit_code = main(
                [
                    "fetch",
                    "--config",
                    str(config_path),
                    "--db",
                    str(Path(temp_dir) / "aggregator.db"),
                    "--content-root",
                    str(Path(temp_dir) / "content"),
                ]
            )

        self.assertEqual(0, exit_code)
        setup_logging_mock.assert_called_once()
        log_file = setup_logging_mock.call_args.kwargs["log_file"]
        self.assertIsInstance(log_file, Path)
        self.assertEqual(Path("data/logs"), log_file.parent)
        self.assertRegex(log_file.name, r"^info-aggregator_\d{8}T\d{6}Z\.log$")

    @patch("src.main.setup_logging")
    @patch("src.main.run_fetch")
    def test_main_fetch_respects_explicit_log_file_override(self, run_fetch_mock, setup_logging_mock) -> None:
        run_fetch_mock.return_value = FetchSummary(
            topics_processed=0,
            youtube_sources_processed=0,
            discovered=0,
            inserted=0,
            deduped=0,
            linked=0,
            missing_transcripts=0,
            skipped_sources=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")
            custom_log = str(Path(temp_dir) / "logs" / "custom.log")

            exit_code = main(
                [
                    "fetch",
                    "--config",
                    str(config_path),
                    "--db",
                    str(Path(temp_dir) / "aggregator.db"),
                    "--content-root",
                    str(Path(temp_dir) / "content"),
                    "--log-file",
                    custom_log,
                ]
            )

        self.assertEqual(0, exit_code)
        setup_logging_mock.assert_called_once_with(level="INFO", log_file=custom_log)

    @patch("src.main.run_fetch")
    def test_main_fetch_command_prints_summary(self, run_fetch_mock) -> None:
        run_fetch_mock.return_value = FetchSummary(
            topics_processed=1,
            youtube_sources_processed=1,
            discovered=3,
            inserted=2,
            deduped=1,
            linked=3,
            missing_transcripts=1,
            skipped_sources=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "fetch",
                        "--config",
                        str(config_path),
                        "--db",
                        str(Path(temp_dir) / "aggregator.db"),
                        "--content-root",
                        str(Path(temp_dir) / "content"),
                        "--log-file",
                        str(Path(temp_dir) / "logs" / "app.log"),
                        "--topic",
                        "politics-us",
                        "--since",
                        "2026-03-08",
                    ]
                )

            output = buffer.getvalue()
            self.assertEqual(0, exit_code)
            self.assertIn("Topics processed: 1", output)
            self.assertIn("YouTube sources processed: 1", output)
            run_fetch_mock.assert_called_once()
            self.assertRegex(
                run_fetch_mock.call_args.kwargs["run_id"],
                r"^\d{8}T\d{6}Z$",
            )

    def test_main_rejects_unknown_topic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            with self.assertRaises(SystemExit) as exc:
                main(
                    [
                        "fetch",
                        "--config",
                        str(config_path),
                        "--db",
                        str(Path(temp_dir) / "aggregator.db"),
                        "--log-file",
                        str(Path(temp_dir) / "logs" / "app.log"),
                        "--topic",
                        "unknown-topic",
                    ]
                )

            self.assertEqual(2, exc.exception.code)


if __name__ == "__main__":
    unittest.main()
