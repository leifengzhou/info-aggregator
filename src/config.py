"""Configuration loading and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the topic configuration is invalid."""


@dataclass(frozen=True)
class TopicConfig:
    """Validated topic configuration."""

    slug: str
    name: str
    description: str
    relevance_threshold: float
    schedule: str
    digest: str
    fetch_since: datetime | None
    sources: dict[str, list[dict[str, Any]]]


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    settings: "Settings"
    topics: dict[str, TopicConfig]


@dataclass(frozen=True)
class Settings:
    """Global runtime settings."""

    youtube_transcript_delay_seconds: float = 1.0
    youtube_transcript_max_retries: int = 3
    youtube_cookies_file: str | None = None
    reddit_request_delay_seconds: float = 1.0


VALID_DIGEST_FREQUENCIES = {"daily", "weekly", "on-demand"}
SUPPORTED_SOURCE_TYPES = {"youtube", "reddit", "rss"}
SCHEDULE_ALIASES = {"hourly", "daily", "weekly"}


def load_config(path: str | Path) -> AppConfig:
    """Load and validate the topics configuration file."""

    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc

    if raw_config is None:
        raise ConfigError(f"Config file is empty: {config_path}")

    return parse_config(raw_config)


def parse_config(raw_config: Any) -> AppConfig:
    """Validate already-parsed config data."""

    config = _expect_mapping(raw_config, "config")
    settings = _parse_settings(config.get("settings"))
    raw_topics = config.get("topics")
    if raw_topics is None:
        raise ConfigError("config.topics is required")

    topics_map = _expect_mapping(raw_topics, "config.topics")
    if not topics_map:
        raise ConfigError("config.topics must define at least one topic")

    topics: dict[str, TopicConfig] = {}
    for slug, raw_topic in topics_map.items():
        if not isinstance(slug, str) or not slug.strip():
            raise ConfigError("config.topics keys must be non-empty strings")

        topic_path = f"config.topics.{slug}"
        topic = _parse_topic(slug, raw_topic, topic_path)
        topics[slug] = topic

    return AppConfig(settings=settings, topics=topics)


def _parse_settings(raw_settings: Any) -> Settings:
    if raw_settings is None:
        return Settings()

    settings = _expect_mapping(raw_settings, "config.settings")

    delay = settings.get("youtube_transcript_delay_seconds", 1.0)
    if not isinstance(delay, (int, float)) or isinstance(delay, bool) or delay < 0:
        raise ConfigError("config.settings.youtube_transcript_delay_seconds must be a non-negative number")

    max_retries = settings.get("youtube_transcript_max_retries", 3)
    if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0:
        raise ConfigError("config.settings.youtube_transcript_max_retries must be a non-negative integer")

    cookies_file = settings.get("youtube_cookies_file")
    if cookies_file is not None:
        if not _is_non_empty_string(cookies_file):
            raise ConfigError("config.settings.youtube_cookies_file must be a non-empty string when provided")
        cookies_file = cookies_file.strip()

    reddit_delay = settings.get("reddit_request_delay_seconds", 1.0)
    if not isinstance(reddit_delay, (int, float)) or isinstance(reddit_delay, bool) or reddit_delay < 0:
        raise ConfigError("config.settings.reddit_request_delay_seconds must be a non-negative number")

    return Settings(
        youtube_transcript_delay_seconds=float(delay),
        youtube_transcript_max_retries=max_retries,
        youtube_cookies_file=cookies_file,
        reddit_request_delay_seconds=float(reddit_delay),
    )


def _parse_topic(slug: str, raw_topic: Any, path: str) -> TopicConfig:
    topic = _expect_mapping(raw_topic, path)
    name = _require_non_empty_string(topic, "name", path)
    description = _require_non_empty_string(topic, "description", path)
    schedule = _require_non_empty_string(topic, "schedule", path)
    digest = _require_non_empty_string(topic, "digest", path)
    fetch_since = _parse_optional_since(topic.get("fetch_since"), f"{path}.fetch_since")
    _validate_schedule(schedule, path)

    if digest not in VALID_DIGEST_FREQUENCIES:
        allowed = ", ".join(sorted(VALID_DIGEST_FREQUENCIES))
        raise ConfigError(f"{path}.digest must be one of: {allowed}")

    threshold = topic.get("relevance_threshold")
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ConfigError(f"{path}.relevance_threshold must be a number between 0 and 10")
    if threshold < 0 or threshold > 10:
        raise ConfigError(f"{path}.relevance_threshold must be between 0 and 10")

    raw_sources = topic.get("sources")
    if raw_sources is None:
        raise ConfigError(f"{path}.sources is required")

    sources_map = _expect_mapping(raw_sources, f"{path}.sources")
    if not sources_map:
        raise ConfigError(f"{path}.sources must define at least one source type")

    validated_sources: dict[str, list[dict[str, Any]]] = {}
    for source_type, raw_entries in sources_map.items():
        if source_type not in SUPPORTED_SOURCE_TYPES:
            supported = ", ".join(sorted(SUPPORTED_SOURCE_TYPES))
            raise ConfigError(
                f"{path}.sources.{source_type} is not supported; expected one of: {supported}"
            )

        source_path = f"{path}.sources.{source_type}"
        entries = _expect_list(raw_entries, source_path)
        if not entries:
            raise ConfigError(f"{source_path} must contain at least one entry")

        validated_entries: list[dict[str, Any]] = []
        for index, raw_entry in enumerate(entries):
            entry_path = f"{source_path}[{index}]"
            entry = _expect_mapping(raw_entry, entry_path)
            validated_entries.append(_validate_source_entry(source_type, entry, entry_path))

        validated_sources[source_type] = validated_entries

    return TopicConfig(
        slug=slug,
        name=name,
        description=description,
        relevance_threshold=float(threshold),
        schedule=schedule,
        digest=digest,
        fetch_since=fetch_since,
        sources=validated_sources,
    )


def _parse_optional_since(value: Any, path: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path} must be a non-empty ISO date/datetime string")

    candidate = value.strip()
    try:
        if len(candidate) == 10:
            return datetime.fromisoformat(candidate).replace(tzinfo=timezone.utc)

        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ConfigError(f"{path} must be a valid ISO date/datetime string") from exc

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_source_entry(
    source_type: str, entry: dict[str, Any], path: str
) -> dict[str, Any]:
    if source_type == "youtube":
        channel_id = entry.get("channel_id")
        playlist_url = entry.get("playlist_url")
        channel_handle = entry.get("channel_handle")
        if (not _is_non_empty_string(channel_id)
                and not _is_non_empty_string(playlist_url)
                and not _is_non_empty_string(channel_handle)):
            raise ConfigError(
                f"{path} must include a non-empty channel_id, playlist_url, or channel_handle"
            )

    elif source_type == "reddit":
        _require_entry_string(entry, "subreddit", path)

        sort = entry.get("sort")
        if sort is not None:
            normalized_sort = _require_entry_string(entry, "sort", path).lower()
            if normalized_sort not in {"hot", "new"}:
                raise ConfigError(f"{path}.sort must be one of: hot, new")
            entry["sort"] = normalized_sort

        if "limit" in entry:
            limit = entry["limit"]
            if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 100:
                raise ConfigError(f"{path}.limit must be an integer between 1 and 100")

        if "comment_limit" in entry:
            comment_limit = entry["comment_limit"]
            if not isinstance(comment_limit, int) or isinstance(comment_limit, bool) or comment_limit < 0:
                raise ConfigError(f"{path}.comment_limit must be a non-negative integer")

        if "min_score" in entry:
            min_score = entry["min_score"]
            if not isinstance(min_score, int) or isinstance(min_score, bool) or min_score < 0:
                raise ConfigError(f"{path}.min_score must be a non-negative integer")

    elif source_type == "rss":
        _require_entry_string(entry, "url", path)

    return entry


def _require_non_empty_string(data: dict[str, Any], key: str, path: str) -> str:
    value = data.get(key)
    if not _is_non_empty_string(value):
        raise ConfigError(f"{path}.{key} must be a non-empty string")
    return value.strip()


def _require_entry_string(entry: dict[str, Any], key: str, path: str) -> str:
    value = entry.get(key)
    if not _is_non_empty_string(value):
        raise ConfigError(f"{path}.{key} must be a non-empty string")
    return value.strip()


def _expect_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{path} must be a mapping")
    return value


def _expect_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError(f"{path} must be a list")
    return value


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_schedule(schedule: str, path: str) -> None:
    normalized = schedule.strip()
    if normalized in SCHEDULE_ALIASES:
        return

    parts = normalized.split()
    if len(parts) != 5:
        aliases = ", ".join(sorted(SCHEDULE_ALIASES))
        raise ConfigError(
            f"{path}.schedule must be one of: {aliases}, or a 5-field cron expression"
        )
