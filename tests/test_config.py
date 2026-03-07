"""Tests for configuration loading and validation."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from src.config import AppConfig, ConfigError, load_config, parse_config


class ConfigLoaderTests(unittest.TestCase):
    def test_load_example_config(self) -> None:
        config = load_config(Path("config/topics.yaml"))

        self.assertIsInstance(config, AppConfig)
        self.assertEqual({"ai-research", "itad-market", "politics-us"}, set(config.topics))
        self.assertEqual("daily", config.topics["ai-research"].digest)
        self.assertEqual("weekly", config.topics["itad-market"].digest)
        self.assertIn("youtube", config.topics["ai-research"].sources)

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


if __name__ == "__main__":
    unittest.main()
