"""Tests for the YouTube adapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.adapters.youtube import YouTubeAdapter, ingest_youtube_source
from src.db import get_content_by_topic, init_db
from src.transcript import TranscriptNotAvailableError, TranscriptSegment

_FEED_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <entry>
    <yt:videoId>vid00000001</yt:videoId>
    <title>Newest video</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=vid00000001" />
    <published>2026-03-06T12:00:00+00:00</published>
    <author>
      <name>Channel One</name>
    </author>
  </entry>
  <entry>
    <yt:videoId>vid00000002</yt:videoId>
    <title>Older video</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=vid00000002" />
    <published>2026-02-01T09:30:00+00:00</published>
    <author>
      <name>Channel One</name>
    </author>
  </entry>
</feed>
"""


class TestYouTubeAdapterFetch(unittest.TestCase):
    def test_fetch_discovers_videos_from_rss(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: [
                TranscriptSegment(text="Hello world", start=0.0, duration=1.0)
            ],
        )

        items = adapter.fetch({"channel_id": "channel-123"})

        self.assertEqual(2, len(items))
        self.assertEqual("vid00000001", items[0].source_id)
        self.assertEqual("Hello world", items[0].content)
        self.assertTrue(items[0].metadata["transcript_available"])
        self.assertEqual("channel-123", items[0].metadata["channel_id"])

    def test_fetch_applies_since_filter(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: [],
        )

        items = adapter.fetch(
            {"channel_id": "channel-123"},
            since=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(["vid00000001"], [item.source_id for item in items])

    def test_fetch_handles_missing_transcript(self) -> None:
        def missing_transcript(_video_id: str):
            raise TranscriptNotAvailableError("No subtitles available")

        adapter = YouTubeAdapter(feed_fetcher=lambda _url: _FEED_XML, transcript_fetcher=missing_transcript)

        items = adapter.fetch({"channel_id": "channel-123"})

        self.assertEqual("", items[0].content)
        self.assertFalse(items[0].metadata["transcript_available"])
        self.assertEqual(0, items[0].metadata["transcript_segment_count"])


class TestYouTubeIngestion(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = init_db(":memory:")

    def tearDown(self) -> None:
        self.conn.close()

    def test_ingest_persists_to_db_and_filesystem(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: [
                TranscriptSegment(text="Line one", start=0.0, duration=1.0),
                TranscriptSegment(text="Line two", start=1.0, duration=1.0),
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = ingest_youtube_source(
                self.conn,
                topic="ai-research",
                source_config={"channel_id": "channel-123"},
                content_root=temp_dir,
                adapter=adapter,
            )

            self.assertEqual(2, result.discovered)
            self.assertEqual(2, result.inserted)
            self.assertEqual(0, result.deduped)
            self.assertEqual(2, result.linked)

            rows = get_content_by_topic(self.conn, "ai-research")
            self.assertEqual(2, len(rows))

            artifact_path = Path(temp_dir) / "vid00000001.json"
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual("Line one\nLine two", payload["content"])
            self.assertTrue(payload["metadata"]["transcript_available"])

    def test_ingest_dedups_existing_content_and_links_second_topic(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: [
                TranscriptSegment(text="Only line", start=0.0, duration=1.0)
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            first = ingest_youtube_source(
                self.conn,
                topic="topic-one",
                source_config={"channel_id": "channel-123"},
                content_root=temp_dir,
                adapter=adapter,
            )
            second = ingest_youtube_source(
                self.conn,
                topic="topic-two",
                source_config={"channel_id": "channel-123"},
                content_root=temp_dir,
                adapter=adapter,
            )

            self.assertEqual(2, first.inserted)
            self.assertEqual(0, first.deduped)
            self.assertEqual(0, second.inserted)
            self.assertEqual(2, second.deduped)

            count = self.conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]
            self.assertEqual(2, count)

            topic_links = self.conn.execute(
                "SELECT COUNT(*) FROM content_topics WHERE topic IN ('topic-one', 'topic-two')"
            ).fetchone()[0]
            self.assertEqual(4, topic_links)

    def test_ingest_counts_missing_transcripts(self) -> None:
        def transcript_fetcher(video_id: str):
            if video_id == "vid00000002":
                raise TranscriptNotAvailableError("No transcript")
            return [TranscriptSegment(text="Available", start=0.0, duration=1.0)]

        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=transcript_fetcher,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = ingest_youtube_source(
                self.conn,
                topic="ai-research",
                source_config={"channel_id": "channel-123"},
                content_root=temp_dir,
                adapter=adapter,
            )

            self.assertEqual(1, result.missing_transcripts)
            payload = json.loads((Path(temp_dir) / "vid00000002.json").read_text(encoding="utf-8"))
            self.assertEqual("", payload["content"])
            self.assertFalse(payload["metadata"]["transcript_available"])


if __name__ == "__main__":
    unittest.main()
