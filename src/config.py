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

    topics: dict[str, TopicConfig]


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

    return AppConfig(topics=topics)


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

        if "sort" in entry:
            _require_entry_string(entry, "sort", path)

        if "limit" in entry:
            limit = entry["limit"]
            if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
                raise ConfigError(f"{path}.limit must be a positive integer")

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
