"""Tests for src.db — SQLite schema and operations."""

import unittest
from datetime import datetime

from src.adapters import FetchedItem
from src.db import (
    init_db,
    insert_content,
    link_content_topic,
    content_exists,
    get_content_by_topic,
    insert_digest,
)


def _make_item(source_id="vid_001", source_type="youtube", published_at=None):
    return FetchedItem(
        source_id=source_id,
        source_type=source_type,
        url=f"https://example.com/{source_id}",
        title=f"Title {source_id}",
        author="author",
        published_at=published_at or datetime(2026, 3, 1, 12, 0),
        content="Full text content here.",
        metadata={"extra": "data"},
    )


class TestInitDb(unittest.TestCase):
    def test_init_db_creates_tables(self):
        conn = init_db(":memory:")
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        self.assertIn("content", tables)
        self.assertIn("content_topics", tables)
        self.assertIn("digests", tables)
        conn.close()


class TestInsertContent(unittest.TestCase):
    def setUp(self):
        self.conn = init_db(":memory:")

    def tearDown(self):
        self.conn.close()

    def test_insert_content_and_retrieve(self):
        item = _make_item()
        result = insert_content(self.conn, item, "/data/vid_001.txt")
        self.assertTrue(result)
        row = self.conn.execute("SELECT * FROM content WHERE id = ?", (item.source_id,)).fetchone()
        self.assertEqual(row["id"], "vid_001")
        self.assertEqual(row["source_type"], "youtube")
        self.assertEqual(row["content_path"], "/data/vid_001.txt")

    def test_insert_content_dedup(self):
        item = _make_item()
        first = insert_content(self.conn, item, "/data/vid_001.txt")
        second = insert_content(self.conn, item, "/data/vid_001.txt")
        self.assertTrue(first)
        self.assertFalse(second)
        count = self.conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]
        self.assertEqual(count, 1)


class TestContentExists(unittest.TestCase):
    def setUp(self):
        self.conn = init_db(":memory:")

    def tearDown(self):
        self.conn.close()

    def test_content_exists(self):
        self.assertFalse(content_exists(self.conn, "vid_001"))
        insert_content(self.conn, _make_item(), "/data/vid_001.txt")
        self.assertTrue(content_exists(self.conn, "vid_001"))


class TestLinkContentTopic(unittest.TestCase):
    def setUp(self):
        self.conn = init_db(":memory:")
        insert_content(self.conn, _make_item(), "/data/vid_001.txt")

    def tearDown(self):
        self.conn.close()

    def test_link_content_topic(self):
        link_content_topic(self.conn, "vid_001", "ai-safety")
        rows = get_content_by_topic(self.conn, "ai-safety")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "vid_001")

    def test_link_content_topic_dedup(self):
        link_content_topic(self.conn, "vid_001", "ai-safety")
        link_content_topic(self.conn, "vid_001", "ai-safety")  # no error
        count = self.conn.execute("SELECT COUNT(*) FROM content_topics").fetchone()[0]
        self.assertEqual(count, 1)


class TestGetContentByTopic(unittest.TestCase):
    def setUp(self):
        self.conn = init_db(":memory:")
        insert_content(self.conn, _make_item("old", published_at=datetime(2026, 1, 1)), "/data/old.txt")
        insert_content(self.conn, _make_item("new", published_at=datetime(2026, 3, 1)), "/data/new.txt")
        link_content_topic(self.conn, "old", "tech")
        link_content_topic(self.conn, "new", "tech")

    def tearDown(self):
        self.conn.close()

    def test_get_content_by_topic_since_filter(self):
        rows = get_content_by_topic(self.conn, "tech", since=datetime(2026, 2, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "new")

    def test_get_content_by_topic_no_filter(self):
        rows = get_content_by_topic(self.conn, "tech")
        self.assertEqual(len(rows), 2)


class TestInsertDigest(unittest.TestCase):
    def test_insert_digest(self):
        conn = init_db(":memory:")
        insert_digest(conn, "tech", datetime(2026, 3, 1), datetime(2026, 3, 7), "/digests/tech.md", 5)
        row = conn.execute("SELECT * FROM digests WHERE topic = 'tech'").fetchone()
        self.assertEqual(row["item_count"], 5)
        conn.close()


if __name__ == "__main__":
    unittest.main()
