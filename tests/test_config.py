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
        config = load_config(Path("config/topics.yaml"))

        self.assertIsInstance(config, AppConfig)
        self.assertIn("ai-research", config.topics)
        self.assertIn("politics-us", config.topics)
        self.assertEqual("daily", config.topics["ai-research"].digest)
        self.assertEqual(datetime(2026, 3, 1, tzinfo=timezone.utc), config.topics["ai-research"].fetch_since)
        self.assertIn("youtube", config.topics["ai-research"].sources)
        self.assertEqual(1.0, config.settings.youtube_transcript_delay_seconds)
        self.assertEqual(3, config.settings.youtube_transcript_max_retries)
        self.assertIsNone(config.settings.youtube_cookies_file)
        self.assertEqual(1.0, config.settings.reddit_request_delay_seconds)

    def test_parse_config_accepts_transcript_settings(self) -> None:
        raw_config = {
            "settings": {
                "youtube_transcript_delay_seconds": 0.5,
                "youtube_transcript_max_retries": 5,
                "youtube_cookies_file": "cookies.txt",
                "reddit_request_delay_seconds": 2.0,
            },
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
        self.assertEqual(5, config.settings.youtube_transcript_max_retries)
        self.assertEqual("cookies.txt", config.settings.youtube_cookies_file)
        self.assertEqual(2.0, config.settings.reddit_request_delay_seconds)

    def test_parse_config_accepts_fetch_since_date(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "fetch_since": "2026-03-01",
                    "sources": {"youtube": [{"channel_id": "UC123"}]},
                }
            }
        }

        config = parse_config(raw_config)
        self.assertEqual(
            datetime(2026, 3, 1, tzinfo=timezone.utc),
            config.topics["test-topic"].fetch_since,
        )

    def test_parse_config_normalizes_fetch_since_datetime_to_utc(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "fetch_since": "2026-03-01T00:30:00-05:00",
                    "sources": {"youtube": [{"channel_id": "UC123"}]},
                }
            }
        }

        config = parse_config(raw_config)
        self.assertEqual(
            datetime(2026, 3, 1, 5, 30, tzinfo=timezone.utc),
            config.topics["test-topic"].fetch_since,
        )

    def test_parse_config_rejects_invalid_fetch_since(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "fetch_since": "not-a-date",
                    "sources": {"youtube": [{"channel_id": "UC123"}]},
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError, r"config\.topics\.test-topic\.fetch_since must be a valid ISO date/datetime string"
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
            r"config\.topics\.test-topic\.sources\.reddit\[0\]\.limit must be an integer between 1 and 100",
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_invalid_reddit_sort(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"reddit": [{"subreddit": "python", "sort": "top"}]},
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError,
            r"config\.topics\.test-topic\.sources\.reddit\[0\]\.sort must be one of: hot, new",
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_invalid_reddit_comment_limit(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"reddit": [{"subreddit": "python", "comment_limit": -1}]},
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError,
            r"config\.topics\.test-topic\.sources\.reddit\[0\]\.comment_limit must be a non-negative integer",
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_invalid_reddit_min_score(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"reddit": [{"subreddit": "python", "min_score": -1}]},
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError,
            r"config\.topics\.test-topic\.sources\.reddit\[0\]\.min_score must be a non-negative integer",
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_invalid_max_retries(self) -> None:
        raw_config = {
            "settings": {"youtube_transcript_max_retries": -1},
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
            r"config\.settings\.youtube_transcript_max_retries must be a non-negative integer",
        ):
            parse_config(raw_config)

    def test_parse_config_rejects_invalid_reddit_request_delay(self) -> None:
        raw_config = {
            "settings": {"reddit_request_delay_seconds": -0.5},
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
            r"config\.settings\.reddit_request_delay_seconds must be a non-negative number",
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
            r"config\.topics\.test-topic\.sources\.youtube\[0\] must include a non-empty channel_id, playlist_url, or channel_handle",
        ):
            parse_config(raw_config)

    def test_channel_handle_accepted_as_locator(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"youtube": [{"channel_handle": "@theAIsearch"}]},
                }
            }
        }

        config = parse_config(raw_config)
        sources = config.topics["test-topic"].sources["youtube"]
        self.assertEqual(1, len(sources))
        self.assertEqual("@theAIsearch", sources[0]["channel_handle"])

    def test_no_locator_raises_error_with_updated_message(self) -> None:
        raw_config = {
            "topics": {
                "test-topic": {
                    "name": "Test Topic",
                    "description": "A test topic",
                    "relevance_threshold": 5,
                    "schedule": "0 * * * *",
                    "digest": "daily",
                    "sources": {"youtube": [{"some_other_field": "value"}]},
                }
            }
        }

        with self.assertRaisesRegex(
            ConfigError,
            r"channel_id, playlist_url, or channel_handle",
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


if __name__ == "__main__":
    unittest.main()
