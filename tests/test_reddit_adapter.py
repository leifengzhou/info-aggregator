"""Tests for the Reddit adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from src.adapters.reddit import (
    RedditAdapter,
    _fetch_json_with_retry,
    ingest_reddit_source,
)
from src.db import get_content_by_topic, init_db


def _make_posts_payload() -> dict:
    return {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": "abc123",
                        "title": "Self post title",
                        "author": "alice",
                        "created_utc": 1772784000,  # 2026-03-05T00:00:00Z
                        "score": 42,
                        "upvote_ratio": 0.97,
                        "num_comments": 2,
                        "link_flair_text": "Discussion",
                        "is_self": True,
                        "selftext": "Body text",
                        "permalink": "/r/MachineLearning/comments/abc123/self_post_title/",
                        "url": "https://www.reddit.com/r/MachineLearning/comments/abc123/self_post_title/",
                    },
                },
                {
                    "kind": "t3",
                    "data": {
                        "id": "def456",
                        "title": "Link post title",
                        "author": "bob",
                        "created_utc": 1772697600,  # 2026-03-04T00:00:00Z
                        "score": 3,
                        "upvote_ratio": 0.88,
                        "num_comments": 0,
                        "link_flair_text": None,
                        "is_self": False,
                        "selftext": "",
                        "permalink": "/r/MachineLearning/comments/def456/link_post_title/",
                        "url": "https://example.com/story",
                    },
                },
            ]
        }
    }


def _make_comments_payload() -> list:
    return [
        {},
        {
            "data": {
                "children": [
                    {"kind": "t1", "data": {"id": "c1", "author": "u1", "body": "first", "score": 5}},
                    {"kind": "t1", "data": {"id": "c2", "author": "u2", "body": "second", "score": 10}},
                    {"kind": "more", "data": {}},
                ]
            }
        },
    ]


class TestRedditAdapterFetch(unittest.TestCase):
    def test_fetch_returns_reddit_items(self) -> None:
        adapter = RedditAdapter(json_fetcher=lambda _url: _make_posts_payload())
        items = adapter.fetch({"subreddit": "MachineLearning", "sort": "new", "limit": 10})

        self.assertEqual(2, len(items))
        self.assertEqual("reddit_abc123", items[0].source_id)
        self.assertEqual("reddit", items[0].source_type)
        self.assertEqual("MachineLearning", items[0].metadata["subreddit"])

    def test_fetch_applies_since_filter(self) -> None:
        adapter = RedditAdapter(json_fetcher=lambda _url: _make_posts_payload())
        items = adapter.fetch(
            {"subreddit": "MachineLearning"},
            since=datetime(2026, 3, 6, tzinfo=timezone.utc),
        )

        self.assertEqual(["reddit_abc123"], [item.source_id for item in items])

    def test_fetch_applies_min_score_filter(self) -> None:
        adapter = RedditAdapter(json_fetcher=lambda _url: _make_posts_payload())
        items = adapter.fetch({"subreddit": "MachineLearning", "min_score": 10})
        self.assertEqual(["reddit_abc123"], [item.source_id for item in items])

    def test_fetch_includes_top_comments_when_enabled(self) -> None:
        responses = [_make_posts_payload(), _make_comments_payload()]
        adapter = RedditAdapter(json_fetcher=lambda _url: responses.pop(0), comment_request_delay_seconds=0)

        items = adapter.fetch(
            {"subreddit": "MachineLearning", "comment_limit": 2},
            since=datetime(2026, 3, 6, tzinfo=timezone.utc),
        )

        self.assertIn("Top Comments (2)", items[0].content)
        self.assertEqual(2, len(items[0].metadata["comments"]))
        self.assertEqual("c2", items[0].metadata["comments"][0]["id"])  # sorted by score desc

    def test_fetch_returns_empty_on_404(self) -> None:
        not_found = HTTPError(
            url="https://www.reddit.com/r/doesnotexist/new.json",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )
        adapter = RedditAdapter(json_fetcher=lambda _url: (_ for _ in ()).throw(not_found))

        items = adapter.fetch({"subreddit": "doesnotexist"})
        self.assertEqual([], items)

    def test_link_post_content_uses_url(self) -> None:
        adapter = RedditAdapter(json_fetcher=lambda _url: _make_posts_payload())
        items = adapter.fetch({"subreddit": "MachineLearning", "min_score": 0})
        link_item = [item for item in items if item.source_id == "reddit_def456"][0]
        self.assertEqual("https://example.com/story", link_item.content)


class TestRedditRetry(unittest.TestCase):
    def test_fetch_json_with_retry_retries_on_429(self) -> None:
        too_many = HTTPError(
            url="https://www.reddit.com/r/test/new.json",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None,
        )
        sleeps: list[float] = []
        with patch("src.adapters.reddit._fetch_json", side_effect=[too_many, {"ok": True}]):
            payload = _fetch_json_with_retry(
                "https://www.reddit.com/r/test/new.json",
                max_retries=2,
                retry_delay_seconds=1.0,
                sleep_func=sleeps.append,
            )
        self.assertEqual({"ok": True}, payload)
        self.assertEqual([1.0], sleeps)


class TestRedditIngest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = init_db(":memory:")

    def tearDown(self) -> None:
        self.conn.close()

    def test_ingest_dedups_across_runs(self) -> None:
        adapter = RedditAdapter(json_fetcher=lambda _url: _make_posts_payload(), comment_request_delay_seconds=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            first = ingest_reddit_source(
                self.conn,
                topic="ai-research",
                source_config={"subreddit": "MachineLearning"},
                content_root=temp_dir,
                adapter=adapter,
            )
            second = ingest_reddit_source(
                self.conn,
                topic="ai-research",
                source_config={"subreddit": "MachineLearning"},
                content_root=temp_dir,
                adapter=adapter,
            )

            self.assertEqual(2, first.inserted)
            self.assertEqual(0, first.deduped)
            self.assertEqual(0, second.inserted)
            self.assertEqual(2, second.deduped)

            rows = get_content_by_topic(self.conn, "ai-research")
            self.assertEqual(2, len(rows))
            artifact_path = Path(temp_dir) / "machinelearning_self-post-title__reddit_abc123.json"
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual("reddit_abc123", payload["source_id"])


if __name__ == "__main__":
    unittest.main()
