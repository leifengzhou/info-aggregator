"""Tests for the CLI entry point."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src.adapters.reddit import RedditIngestResult
from src.adapters.youtube import YouTubeIngestResult
from src.main import FetchSummary, main, parse_since, run_fetch


_CONFIG_YAML = """\
settings:
  youtube_transcript_delay_seconds: 0.25
  youtube_transcript_max_retries: 4
  youtube_cookies_file: "/tmp/cookies.txt"
  reddit_request_delay_seconds: 1.5
topics:
  ai-research:
    name: "AI Research"
    description: "AI updates"
    relevance_threshold: 6
    schedule: "0 */4 * * *"
    digest: daily
    fetch_since: "2026-03-02"
    sources:
      youtube:
        - channel_id: "UC123456789"
      reddit:
        - subreddit: "MachineLearning"
          sort: "hot"
          limit: 10
      rss:
        - url: "https://example.com/feed.xml"
  politics-us:
    name: "Politics"
    description: "Politics updates"
    relevance_threshold: 7
    schedule: "0 */6 * * *"
    digest: daily
    fetch_since: "2026-03-03T12:00:00-05:00"
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


class TestRunFetch(unittest.TestCase):
    def test_run_fetch_processes_all_topics_and_skips_non_youtube_sources(self) -> None:
        youtube_calls: list[tuple[str, dict, Path, datetime | None, float, str | None, int]] = []
        reddit_calls: list[tuple[str, dict, Path, datetime | None, float]] = []

        def fake_youtube_ingestor(
            *,
            conn,
            topic,
            source_config,
            content_root,
            since,
            transcript_delay_seconds,
            youtube_cookies_file,
            transcript_max_retries,
        ):
            youtube_calls.append(
                (
                    topic,
                    source_config,
                    content_root,
                    since,
                    transcript_delay_seconds,
                    youtube_cookies_file,
                    transcript_max_retries,
                )
            )
            return YouTubeIngestResult(
                discovered=2,
                inserted=1,
                deduped=1,
                linked=2,
                missing_transcripts=0,
            )

        def fake_reddit_ingestor(
            *,
            conn,
            topic,
            source_config,
            content_root,
            since,
            request_delay_seconds,
        ):
            reddit_calls.append((topic, source_config, content_root, since, request_delay_seconds))
            return RedditIngestResult(discovered=1, inserted=1, deduped=0, linked=1)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            summary = run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                youtube_ingestor=fake_youtube_ingestor,
                reddit_ingestor=fake_reddit_ingestor,
            )

            self.assertEqual(2, summary.topics_processed)
            self.assertEqual(2, summary.youtube_sources_processed)
            self.assertEqual(1, summary.reddit_sources_processed)
            self.assertEqual(5, summary.discovered)
            self.assertEqual(3, summary.inserted)
            self.assertEqual(2, summary.deduped)
            self.assertEqual(5, summary.linked)
            self.assertEqual(1, summary.skipped_sources)
            self.assertEqual(
                [
                    ("ai-research", {"channel_id": "UC123456789"}),
                    ("politics-us", {"channel_id": "UCabcdefghijk"}),
                ],
                [(topic, source_config) for topic, source_config, _root, _since, *_ in youtube_calls],
            )
            self.assertTrue(
                all(content_root.name == "youtube" for _topic, _source, content_root, _since, *_ in youtube_calls)
            )
            self.assertEqual(
                [
                    datetime(2026, 3, 2, tzinfo=timezone.utc),
                    datetime(2026, 3, 3, 17, 0, tzinfo=timezone.utc),
                ],
                [_since for _topic, _source, _root, _since, *_ in youtube_calls],
            )
            self.assertEqual([0.25, 0.25], [delay for *_head, delay, _cookie, _retry in youtube_calls])
            self.assertEqual(
                ["/tmp/cookies.txt", "/tmp/cookies.txt"],
                [cookie for *_head, _delay, cookie, _retry in youtube_calls],
            )
            self.assertEqual([4, 4], [retries for *_head, _delay, _cookie, retries in youtube_calls])
            self.assertEqual([("ai-research", {"subreddit": "MachineLearning", "sort": "hot", "limit": 10})],
                             [(topic, source_config) for topic, source_config, *_ in reddit_calls])
            self.assertEqual([1.5], [delay for *_head, delay in reddit_calls])

    def test_run_fetch_topic_filter_limits_to_single_topic(self) -> None:
        calls: list[str] = []

        def fake_ingestor(
            *,
            conn,
            topic,
            source_config,
            content_root,
            since,
            transcript_delay_seconds,
            youtube_cookies_file,
            transcript_max_retries,
        ):
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

    def test_run_fetch_cli_since_overrides_topic_fetch_since(self) -> None:
        youtube_calls: list[datetime | None] = []
        reddit_calls: list[datetime | None] = []

        def fake_youtube_ingestor(
            *,
            conn,
            topic,
            source_config,
            content_root,
            since,
            transcript_delay_seconds,
            youtube_cookies_file,
            transcript_max_retries,
        ):
            youtube_calls.append(since)
            return YouTubeIngestResult(1, 1, 0, 1, 0)

        def fake_reddit_ingestor(
            *,
            conn,
            topic,
            source_config,
            content_root,
            since,
            request_delay_seconds,
        ):
            reddit_calls.append(since)
            return RedditIngestResult(1, 1, 0, 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")
            cli_since = datetime(2026, 3, 8, tzinfo=timezone.utc)

            run_fetch(
                config_path=config_path,
                db_path=Path(temp_dir) / "aggregator.db",
                content_root=Path(temp_dir) / "content",
                since=cli_since,
                youtube_ingestor=fake_youtube_ingestor,
                reddit_ingestor=fake_reddit_ingestor,
            )

        self.assertEqual([cli_since, cli_since], youtube_calls)
        self.assertEqual([cli_since], reddit_calls)

    def test_run_fetch_logs_effective_settings_and_runtime_fields(self) -> None:
        def fake_youtube_ingestor(
            *,
            conn,
            topic,
            source_config,
            content_root,
            since,
            transcript_delay_seconds,
            youtube_cookies_file,
            transcript_max_retries,
        ):
            return YouTubeIngestResult(1, 1, 0, 1, 0)

        def fake_reddit_ingestor(
            *,
            conn,
            topic,
            source_config,
            content_root,
            since,
            request_delay_seconds,
        ):
            return RedditIngestResult(1, 1, 0, 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "topics.yaml"
            config_path.write_text(_CONFIG_YAML, encoding="utf-8")

            with patch("src.main.logger.info") as log_info_mock:
                run_fetch(
                    config_path=config_path,
                    db_path=Path(temp_dir) / "aggregator.db",
                    content_root=Path(temp_dir) / "content",
                    run_id="run-123",
                    log_level="INFO",
                    log_file=Path(temp_dir) / "logs" / "run.log",
                    youtube_ingestor=fake_youtube_ingestor,
                    reddit_ingestor=fake_reddit_ingestor,
                )

        self.assertGreaterEqual(log_info_mock.call_count, 2)
        started_extra = log_info_mock.call_args_list[0].kwargs["extra"]
        completed_extra = log_info_mock.call_args_list[-1].kwargs["extra"]
        self.assertEqual("run-123", started_extra["run_id"])
        self.assertEqual(0.25, started_extra["settings"]["youtube_transcript_delay_seconds"])
        self.assertEqual(4, started_extra["settings"]["youtube_transcript_max_retries"])
        self.assertEqual("/tmp/cookies.txt", started_extra["settings"]["youtube_cookies_file"])
        self.assertEqual(1.5, started_extra["settings"]["reddit_request_delay_seconds"])
        self.assertEqual("run-123", completed_extra["run_id"])
        self.assertIn("duration_seconds", completed_extra)
        self.assertGreaterEqual(completed_extra["duration_seconds"], 0.0)


class TestMain(unittest.TestCase):
    @patch("src.main.run_fetch")
    def test_main_fetch_command_prints_summary(self, run_fetch_mock) -> None:
        run_fetch_mock.return_value = FetchSummary(
            topics_processed=1,
            youtube_sources_processed=1,
            reddit_sources_processed=1,
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
            self.assertIn("Reddit sources processed: 1", output)
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
                        "--log-file",
                        str(Path(temp_dir) / "logs" / "app.log"),
                        "--topic",
                        "unknown-topic",
                    ]
                )

            self.assertEqual(2, exc.exception.code)

    @patch("src.main.setup_logging")
    @patch("src.main.resolve_run_log_path")
    @patch("src.main.make_run_id", return_value="20260309_123000_000001")
    @patch("src.main.run_fetch")
    def test_main_fetch_uses_per_run_log_resolution(
        self,
        run_fetch_mock,
        make_run_id_mock,
        resolve_run_log_path_mock,
        setup_logging_mock,
    ) -> None:
        run_fetch_mock.return_value = FetchSummary(
            topics_processed=0,
            youtube_sources_processed=0,
            reddit_sources_processed=0,
            discovered=0,
            inserted=0,
            deduped=0,
            linked=0,
            missing_transcripts=0,
            skipped_sources=0,
        )
        resolved_path = Path("data/logs/info-aggregator_20260309_123000_000001.log")
        resolve_run_log_path_mock.return_value = resolved_path

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
        make_run_id_mock.assert_called_once()
        resolve_run_log_path_mock.assert_called_once()
        setup_logging_mock.assert_called_once_with(level="INFO", log_file=resolved_path)
        run_fetch_mock.assert_called_once()
        self.assertEqual("20260309_123000_000001", run_fetch_mock.call_args.kwargs["run_id"])
        self.assertEqual("INFO", run_fetch_mock.call_args.kwargs["log_level"])
        self.assertEqual(resolved_path, run_fetch_mock.call_args.kwargs["log_file"])


if __name__ == "__main__":
    unittest.main()
