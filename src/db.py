"""SQLite storage layer for content and digests."""

import logging
import sqlite3
from datetime import datetime, timezone

from src.adapters import FetchedItem

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS content (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    url TEXT,
    title TEXT,
    author TEXT,
    published_at DATETIME,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    content_path TEXT,
    summary TEXT,
    tags JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_topics (
    content_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    relevance_score REAL,
    PRIMARY KEY (content_id, topic),
    FOREIGN KEY (content_id) REFERENCES content(id)
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    period_start DATETIME,
    period_end DATETIME,
    file_path TEXT,
    item_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_content_source ON content(source_type, published_at);
CREATE INDEX IF NOT EXISTS idx_content_topics_topic ON content_topics(topic);
CREATE INDEX IF NOT EXISTS idx_content_topics_score ON content_topics(relevance_score);
"""


def _normalize_datetime(value: datetime) -> datetime:
    """Normalize datetimes to timezone-aware UTC values for consistent storage/querying."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def init_db(db_path: str) -> sqlite3.Connection:
    """Create tables if not exist, enable WAL mode and foreign keys, return connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    logger.info("db_initialized", extra={"db_path": db_path})
    return conn


def insert_content(conn: sqlite3.Connection, item: FetchedItem, content_path: str) -> bool:
    """Insert a content row. Returns False if already exists (dedup by primary key)."""
    published_at = _normalize_datetime(item.published_at) if item.published_at else None
    cursor = conn.execute(
        """INSERT OR IGNORE INTO content (id, source_type, url, title, author, published_at, content_path)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (item.source_id, item.source_type, item.url, item.title,
         item.author, published_at.isoformat() if published_at else None,
         content_path),
    )
    conn.commit()
    inserted = cursor.rowcount > 0
    logger.debug(
        "content_insert_attempt",
        extra={
            "content_id": item.source_id,
            "source_type": item.source_type,
            "inserted": inserted,
            "content_path": content_path,
        },
    )
    return inserted


def link_content_topic(conn: sqlite3.Connection, content_id: str, topic: str) -> None:
    """Insert content_topics row (ignore if exists)."""
    cursor = conn.execute(
        "INSERT OR IGNORE INTO content_topics (content_id, topic) VALUES (?, ?)",
        (content_id, topic),
    )
    conn.commit()
    logger.debug(
        "content_topic_linked",
        extra={
            "content_id": content_id,
            "topic": topic,
            "inserted": cursor.rowcount > 0,
        },
    )


def content_exists(conn: sqlite3.Connection, content_id: str) -> bool:
    """Check if content with the given ID already exists."""
    row = conn.execute("SELECT 1 FROM content WHERE id = ?", (content_id,)).fetchone()
    exists = row is not None
    logger.debug("content_exists_checked", extra={"content_id": content_id, "exists": exists})
    return exists


def get_content_by_topic(conn: sqlite3.Connection, topic: str, since: datetime | None = None) -> list[sqlite3.Row]:
    """Query content linked to a topic, optionally filtered by published_at >= since."""
    if since is not None:
        normalized_since = _normalize_datetime(since)
        rows = conn.execute(
            """SELECT c.* FROM content c
               JOIN content_topics ct ON c.id = ct.content_id
               WHERE ct.topic = ? AND c.published_at >= ?
               ORDER BY c.published_at DESC""",
            (topic, normalized_since.isoformat()),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT c.* FROM content c
               JOIN content_topics ct ON c.id = ct.content_id
               WHERE ct.topic = ?
               ORDER BY c.published_at DESC""",
            (topic,),
        ).fetchall()
    logger.info(
        "content_by_topic_queried",
        extra={
            "topic": topic,
            "since": _normalize_datetime(since).isoformat() if since else None,
            "row_count": len(rows),
        },
    )
    return rows


def insert_digest(conn: sqlite3.Connection, topic: str, period_start: datetime,
                  period_end: datetime, file_path: str, item_count: int) -> None:
    """Record a generated digest."""
    normalized_start = _normalize_datetime(period_start)
    normalized_end = _normalize_datetime(period_end)
    conn.execute(
        """INSERT INTO digests (topic, period_start, period_end, file_path, item_count)
           VALUES (?, ?, ?, ?, ?)""",
        (topic, normalized_start.isoformat(), normalized_end.isoformat(), file_path, item_count),
    )
    conn.commit()
    logger.info(
        "digest_inserted",
        extra={
            "topic": topic,
            "period_start": normalized_start.isoformat(),
            "period_end": normalized_end.isoformat(),
            "file_path": file_path,
            "item_count": item_count,
        },
    )
