"""CLI entry point for the Info Aggregator."""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.adapters.youtube import YouTubeIngestResult, ingest_youtube_source
from src.config import AppConfig, load_config
from src.db import init_db
from src.logging_setup import setup_logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchSummary:
    """Aggregate result of a fetch run."""

    topics_processed: int
    youtube_sources_processed: int
    discovered: int
    inserted: int
    deduped: int
    linked: int
    missing_transcripts: int
    skipped_sources: int


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Info Aggregator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch content for configured topics")
    fetch_parser.add_argument(
        "--config",
        default="config/topics.yaml",
        help="Path to the topics YAML config file",
    )
    fetch_parser.add_argument(
        "--db",
        default="data/aggregator.db",
        help="Path to the SQLite database file",
    )
    fetch_parser.add_argument(
        "--content-root",
        default="data/content",
        help="Directory for raw content artifacts",
    )
    fetch_parser.add_argument(
        "--topic",
        help="Only fetch a single topic slug from the config",
    )
    fetch_parser.add_argument(
        "--since",
        type=parse_since,
        help="Only fetch content published on or after this date/time",
    )
    fetch_parser.add_argument(
        "--log-level",
        default="INFO",
        help="Log level for structured console/file logging",
    )
    fetch_parser.add_argument(
        "--log-file",
        default="data/logs/info-aggregator.log",
        help="Path to the structured log file",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "fetch":
            setup_logging(level=args.log_level, log_file=args.log_file)
            summary = run_fetch(
                config_path=args.config,
                db_path=args.db,
                content_root=args.content_root,
                topic=args.topic,
                since=args.since,
            )
            _print_fetch_summary(summary)
            return 0
    except ValueError as exc:
        parser.exit(status=2, message=f"error: {exc}\n")

    parser.exit(status=2, message=f"error: unsupported command: {args.command}\n")


def run_fetch(
    config_path: str | Path,
    db_path: str | Path,
    content_root: str | Path,
    topic: str | None = None,
    since: datetime | None = None,
    config_loader: Callable[[str | Path], AppConfig] = load_config,
    youtube_ingestor: Callable[..., YouTubeIngestResult] = ingest_youtube_source,
) -> FetchSummary:
    """Execute a fetch run against the configured topics."""

    config = config_loader(config_path)
    topics = _select_topics(config, topic)
    logger.info(
        "fetch_run_started",
        extra={
            "config_path": str(config_path),
            "db_path": str(db_path),
            "content_root": str(content_root),
            "topic": topic,
            "since": since.isoformat() if since else None,
            "topic_count": len(topics),
        },
    )

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    content_root = Path(content_root)

    conn = init_db(str(db_path))
    try:
        topics_processed = 0
        youtube_sources_processed = 0
        discovered = 0
        inserted = 0
        deduped = 0
        linked = 0
        missing_transcripts = 0
        skipped_sources = 0

        for topic_config in topics:
            topics_processed += 1

            for source_type, entries in topic_config.sources.items():
                if source_type != "youtube":
                    logger.info(
                        "source_type_skipped",
                        extra={
                            "topic": topic_config.slug,
                            "source_type": source_type,
                            "entry_count": len(entries),
                        },
                    )
                    skipped_sources += len(entries)
                    continue

                for source_config in entries:
                    logger.info(
                        "youtube_source_processing",
                        extra={"topic": topic_config.slug, "source_config": source_config},
                    )
                    result = youtube_ingestor(
                        conn=conn,
                        topic=topic_config.slug,
                        source_config=source_config,
                        content_root=content_root / "youtube",
                        since=since,
                    )
                    youtube_sources_processed += 1
                    discovered += result.discovered
                    inserted += result.inserted
                    deduped += result.deduped
                    linked += result.linked
                    missing_transcripts += result.missing_transcripts

        summary = FetchSummary(
            topics_processed=topics_processed,
            youtube_sources_processed=youtube_sources_processed,
            discovered=discovered,
            inserted=inserted,
            deduped=deduped,
            linked=linked,
            missing_transcripts=missing_transcripts,
            skipped_sources=skipped_sources,
        )

        logger.info(
            "fetch_run_completed",
            extra={
                "topics_processed": summary.topics_processed,
                "youtube_sources_processed": summary.youtube_sources_processed,
                "discovered": summary.discovered,
                "inserted": summary.inserted,
                "deduped": summary.deduped,
                "linked": summary.linked,
                "missing_transcripts": summary.missing_transcripts,
                "skipped_sources": summary.skipped_sources,
            },
        )
        return summary
    finally:
        conn.close()


def parse_since(value: str) -> datetime:
    """Parse a user-supplied since value into a timezone-aware datetime."""

    candidate = value.strip()
    if len(candidate) == 10:
        return datetime.fromisoformat(candidate).replace(tzinfo=timezone.utc)

    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _select_topics(config: AppConfig, topic: str | None) -> list:
    if topic is None:
        return list(config.topics.values())

    selected = config.topics.get(topic)
    if selected is None:
        available = ", ".join(sorted(config.topics))
        raise ValueError(f"unknown topic '{topic}'. Available topics: {available}")
    return [selected]


def _print_fetch_summary(summary: FetchSummary) -> None:
    print(f"Topics processed: {summary.topics_processed}")
    print(f"YouTube sources processed: {summary.youtube_sources_processed}")
    print(f"Items discovered: {summary.discovered}")
    print(f"Items inserted: {summary.inserted}")
    print(f"Items deduped: {summary.deduped}")
    print(f"Topic links created: {summary.linked}")
    print(f"Missing transcripts: {summary.missing_transcripts}")
    print(f"Skipped non-YouTube sources: {summary.skipped_sources}")


if __name__ == "__main__":
    raise SystemExit(main())
