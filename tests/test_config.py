"""Tests for configuration loading and validation."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.config import AppConfig, ConfigError, load_config, parse_config


class ConfigLoaderTests(unittest.TestCase):
    def test_load_example_config(self) -> None:
        config = load_config(Path("config/topics.example.yaml"))

        self.assertIsInstance(config, AppConfig)
        self.assertEqual(1.0, config.settings.youtube_transcript_delay_seconds)
        self.assertEqual({"ai-research", "itad-market", "politics-us"}, set(config.topics))
        self.assertEqual("daily", config.topics["ai-research"].digest)
        self.assertEqual("weekly", config.topics["itad-market"].digest)
        self.assertIn("youtube", config.topics["ai-research"].sources)

    def test_parse_config_applies_default_settings(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"youtube": [{"channel_id": "UC123"}]},
                }
            }
        }

        config = parse_config(raw_config)
        self.assertEqual(1.0, config.settings.youtube_transcript_delay_seconds)

    def test_parse_config_accepts_explicit_transcript_delay(self) -> None:
        raw_config = {
            "settings": {"youtube_transcript_delay_seconds": 0.5},
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"youtube": [{"channel_id": "UC123"}]},
                }
            },
        }

        config = parse_config(raw_config)
        self.assertEqual(0.5, config.settings.youtube_transcript_delay_seconds)

    def test_parse_config_rejects_negative_transcript_delay(self) -> None:
        raw_config = {
            "settings": {"youtube_transcript_delay_seconds": -1},
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"youtube": [{"channel_id": "UC123"}]},
                }
            },
        }

        with self.assertRaisesRegex(
            ConfigError, r"config\.settings\.youtube_transcript_delay_seconds must be >= 0"
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_non_numeric_transcript_delay(self) -> None:
        raw_config = {
            "settings": {"youtube_transcript_delay_seconds": "fast"},
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"youtube": [{"channel_id": "UC123"}]},
                }
            },
        }

        with self.assertRaisesRegex(
            ConfigError,
            r"config\.settings\.youtube_transcript_delay_seconds must be a number >= 0",
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_missing_required_field(self) -> None:
        raw_config = {
            "topics": {
                "ai-research": {
                    "description": "Missing the name field",
                    "relevance_threshold": 6,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"rss": [{"url": "https://example.com/rss"}]},
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError, r"config\.topics\.ai-research\.name must be a non-empty string"
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_invalid_reddit_limit(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {
                        "reddit": [
                            {"subreddit": "python", "sort": "hot", "limit": 0},
                        ]
                    },
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError,
            r"config\.topics\.test-topic\.sources\.reddit\[0\]\.limit must be a positive integer",
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_invalid_schedule(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "every minute forever",
                    "digest": "daily",
                    "sources": {"rss": [{"url": "https://example.com/rss"}]},
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError,
            r"config\.topics\.test-topic\.schedule must be one of: daily, hourly, weekly, or a 5-field cron expression",
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_youtube_entry_without_locator(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"youtube": [{}]},
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError,
            r"config\.topics\.test-topic\.sources\.youtube\[0\] must include a non-empty channel_id or playlist_url",
        ):
            parse_config(raw_config)

    def test_load_config_rejects_invalid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "topics.yaml"
            path.write_text(
                textwrap.dedent(
                    """
                    topics:
                      broken:
                        name: Missing quote
                        description: "bad
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, r"Invalid YAML in .*topics\.yaml"):
                load_config(path)


_MINIMAL_TOPIC = {
    "name": "Test Topic",
    "description": "A test topic",
    "relevance_threshold": 5,
    "schedule": "daily",
    "digest": "daily",
    "sources": {"youtube": [{"channel_id": "UC123"}]},
}


class TestFetchSince(unittest.TestCase):
    def _make_config(self, fetch_since_value=None) -> dict:
        topic = dict(_MINIMAL_TOPIC)
        if fetch_since_value is not None:
            topic["fetch_since"] = fetch_since_value
        return {"topics": {"test-topic": topic}}

    def test_fetch_since_date_only(self) -> None:
        config = parse_config(self._make_config("2025-01-01"))
        self.assertEqual(
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            config.topics["test-topic"].fetch_since,
        )

    def test_fetch_since_datetime_string(self) -> None:
        config = parse_config(self._make_config("2025-06-15T08:00:00Z"))
        self.assertEqual(
            datetime(2025, 6, 15, 8, 0, 0, tzinfo=timezone.utc),
            config.topics["test-topic"].fetch_since,
        )

    def test_fetch_since_absent_defaults_to_none(self) -> None:
        config = parse_config(self._make_config())
        self.assertIsNone(config.topics["test-topic"].fetch_since)

    def test_fetch_since_non_string_raises(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            r"config\.topics\.test-topic\.fetch_since must be a string",
        ):
            parse_config(self._make_config(12345))

    def test_fetch_since_bad_format_raises(self) -> None:
        with self.assertRaisesRegex(
            ConfigError,
            r"config\.topics\.test-topic\.fetch_since: invalid date/datetime 'not-a-date'",
        ):
            parse_config(self._make_config("not-a-date"))


if __name__ == "__main__":
    unittest.main()
