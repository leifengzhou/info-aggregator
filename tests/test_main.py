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
from src.main import FetchSummary, main, parse_since, run_fetch


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


class TestRunFetch(unittest.TestCase):
    def test_run_fetch_processes_all_topics_and_skips_non_youtube_sources(self) -> None:
        calls: list[tuple[str, dict, Path, datetime | None]] = []

        def fake_ingestor(*, conn, topic, source_config, content_root, since):
            calls.append((topic, source_config, content_root, since))
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
                [(topic, source_config) for topic, source_config, _root, _since in calls],
            )
            self.assertTrue(all(content_root.name == "youtube" for _topic, _source, content_root, _since in calls))

    def test_run_fetch_topic_filter_limits_to_single_topic(self) -> None:
        calls: list[str] = []

        def fake_ingestor(*, conn, topic, source_config, content_root, since):
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


class TestMain(unittest.TestCase):
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
                        "--topic",
                        "unknown-topic",
                    ]
                )

            self.assertEqual(2, exc.exception.code)


if __name__ == "__main__":
    unittest.main()
