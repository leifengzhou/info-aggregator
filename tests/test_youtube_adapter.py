"""Tests for the YouTube adapter."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from src.adapters import FetchedItem
from src.adapters.youtube import (
    YouTubeAdapter,
    _build_artifact_filename,
    _build_feed_url,
    _extract_playlist_id,
    _slugify,
    ingest_youtube_source,
    resolve_channel_handle,
)
from src.db import get_content_by_topic, init_db
from src.transcript import TranscriptNotAvailableError, TranscriptResult, TranscriptSegment

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


def _make_transcript_result(
    segments: list[TranscriptSegment],
    language: str = "English",
    language_code: str = "en",
    is_generated: bool = False,
) -> TranscriptResult:
    return TranscriptResult(
        segments=segments,
        language=language,
        language_code=language_code,
        is_generated=is_generated,
    )


class TestYouTubeAdapterFetch(unittest.TestCase):
    def test_fetch_discovers_videos_from_rss(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result(
                [TranscriptSegment(text="Hello world", start=0.0, duration=1.0)]
            ),
        )

        items = adapter.fetch({"channel_id": "channel-123"})

        self.assertEqual(2, len(items))
        self.assertEqual("vid00000001", items[0].source_id)
        self.assertEqual("Hello world", items[0].content)
        self.assertTrue(items[0].metadata["transcript_available"])
        self.assertFalse(items[0].metadata["transcript_is_generated"])
        self.assertEqual("en", items[0].metadata["transcript_language"])
        self.assertEqual("channel-123", items[0].metadata["channel_id"])

    def test_fetch_applies_since_filter(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result([]),
        )

        items = adapter.fetch(
            {"channel_id": "channel-123"},
            since=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(["vid00000001"], [item.source_id for item in items])

    def test_fetch_formats_multiline_transcript_content(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result(
                [
                    TranscriptSegment(text="Line one", start=0.0, duration=1.0),
                    TranscriptSegment(text="Line two", start=1.0, duration=1.0),
                ]
            ),
        )

        items = adapter.fetch({"channel_id": "channel-123"})

        self.assertEqual("Line one\nLine two", items[0].content)

    def test_fetch_handles_missing_transcript(self) -> None:
        def missing_transcript(_video_id: str):
            raise TranscriptNotAvailableError("No subtitles available")

        adapter = YouTubeAdapter(feed_fetcher=lambda _url: _FEED_XML, transcript_fetcher=missing_transcript)

        items = adapter.fetch({"channel_id": "channel-123"})

        self.assertEqual("", items[0].content)
        self.assertFalse(items[0].metadata["transcript_available"])
        self.assertEqual(0, items[0].metadata["transcript_segment_count"])
        self.assertIsNone(items[0].metadata["transcript_is_generated"])
        self.assertIsNone(items[0].metadata["transcript_language"])

    def test_fetch_logs_warning_and_returns_empty_on_http_error(self) -> None:
        def failing_feed_fetcher(url: str) -> str:
            raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

        adapter = YouTubeAdapter(
            feed_fetcher=failing_feed_fetcher,
            transcript_fetcher=lambda _video_id: [],
        )

        with self.assertLogs("src.adapters.youtube", level="WARNING") as logs:
            items = adapter.fetch({"channel_id": "missing-channel"})

        self.assertEqual([], items)
        self.assertTrue(
            any("youtube_feed_unavailable" in message for message in logs.output),
            logs.output,
        )

    def test_fetch_applies_transcript_delay_between_videos(self) -> None:
        sleep_calls: list[float] = []
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result([]),
            transcript_delay_seconds=0.25,
            sleep_func=sleep_calls.append,
        )

        adapter.fetch({"channel_id": "channel-123"})

        self.assertEqual([0.25], sleep_calls)

    def test_fetch_skips_sleep_when_delay_is_zero(self) -> None:
        sleep_calls: list[float] = []
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result([]),
            transcript_delay_seconds=0,
            sleep_func=sleep_calls.append,
        )

        adapter.fetch({"channel_id": "channel-123"})

        self.assertEqual([], sleep_calls)

    def test_fetch_skips_sleep_for_single_video(self) -> None:
        sleep_calls: list[float] = []
        single_video_feed = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <entry>
    <yt:videoId>vid00000001</yt:videoId>
    <title>Only video</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=vid00000001" />
    <published>2026-03-06T12:00:00+00:00</published>
    <author>
      <name>Channel One</name>
    </author>
  </entry>
</feed>
"""
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: single_video_feed,
            transcript_fetcher=lambda _video_id: _make_transcript_result([]),
            transcript_delay_seconds=0.25,
            sleep_func=sleep_calls.append,
        )

        adapter.fetch({"channel_id": "channel-123"})

        self.assertEqual([], sleep_calls)


class TestYouTubeIngestion(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = init_db(":memory:")

    def tearDown(self) -> None:
        self.conn.close()

    def test_ingest_persists_to_db_and_filesystem(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result([
                TranscriptSegment(text="Line one", start=0.0, duration=1.0),
                TranscriptSegment(text="Line two", start=1.0, duration=1.0),
            ]),
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

            artifact_path = Path(temp_dir) / "channel-one_newest-video__vid00000001.json"
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual("Line one\nLine two", payload["content"])
            self.assertTrue(payload["metadata"]["transcript_available"])

    def test_ingest_dedups_existing_content_and_links_second_topic(self) -> None:
        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result([
                TranscriptSegment(text="Only line", start=0.0, duration=1.0)
            ]),
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
            return _make_transcript_result(
                [TranscriptSegment(text="Available", start=0.0, duration=1.0)]
            )

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
            payload = json.loads((Path(temp_dir) / "channel-one_older-video__vid00000002.json").read_text(encoding="utf-8"))
            self.assertEqual("", payload["content"])
            self.assertFalse(payload["metadata"]["transcript_available"])


class TestYouTubeLocatorHelpers(unittest.TestCase):
    def test_build_feed_url_from_channel_id(self) -> None:
        feed_url, metadata = _build_feed_url({"channel_id": " UC123 "})
        self.assertEqual("https://www.youtube.com/feeds/videos.xml?channel_id=UC123", feed_url)
        self.assertEqual({"channel_id": "UC123"}, metadata)

    def test_build_feed_url_from_playlist_url(self) -> None:
        feed_url, metadata = _build_feed_url(
            {"playlist_url": "https://www.youtube.com/playlist?list=PL123abc"}
        )
        self.assertEqual("https://www.youtube.com/feeds/videos.xml?playlist_id=PL123abc", feed_url)
        self.assertEqual({"playlist_id": "PL123abc"}, metadata)

    def test_build_feed_url_prefers_channel_id_when_both_present(self) -> None:
        feed_url, metadata = _build_feed_url(
            {
                "channel_id": "UCabc123",
                "playlist_url": "https://www.youtube.com/playlist?list=PL123abc",
            }
        )
        self.assertEqual("https://www.youtube.com/feeds/videos.xml?channel_id=UCabc123", feed_url)
        self.assertEqual({"channel_id": "UCabc123"}, metadata)

    def test_build_feed_url_rejects_missing_locator(self) -> None:
        with self.assertRaisesRegex(ValueError, "must include channel_id or playlist_url"):
            _build_feed_url({})

    def test_extract_playlist_id_from_url(self) -> None:
        playlist_id = _extract_playlist_id("https://www.youtube.com/playlist?list=PLabc123")
        self.assertEqual("PLabc123", playlist_id)

    def test_extract_playlist_id_ignores_other_query_params(self) -> None:
        playlist_id = _extract_playlist_id(
            "https://www.youtube.com/watch?v=vid123&list=PLxyz789&index=2"
        )
        self.assertEqual("PLxyz789", playlist_id)

    def test_extract_playlist_id_rejects_missing_list_parameter(self) -> None:
        with self.assertRaisesRegex(ValueError, "Could not extract playlist ID"):
            _extract_playlist_id("https://www.youtube.com/playlist?index=1")

    def test_extract_playlist_id_rejects_blank_list_parameter(self) -> None:
        with self.assertRaisesRegex(ValueError, "Could not extract playlist ID"):
            _extract_playlist_id("https://www.youtube.com/playlist?list=")


class TestSlugifyAndFilename(unittest.TestCase):
    def test_slugify_basic(self) -> None:
        self.assertEqual("hello-world", _slugify("Hello World"))

    def test_slugify_special_chars(self) -> None:
        self.assertEqual("test-video-2024", _slugify("Test Video! @#$ (2024)"))

    def test_slugify_strips_leading_trailing_hyphens(self) -> None:
        self.assertEqual("hello", _slugify("---hello---"))

    def test_slugify_empty_string(self) -> None:
        self.assertEqual("", _slugify(""))

    def test_build_artifact_filename_basic(self) -> None:
        item = FetchedItem(
            source_id="abc123xyz_-",
            source_type="youtube",
            url="https://example.com",
            title="My Great Video",
            author="Some Channel",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            content="",
            metadata={},
        )
        self.assertEqual("some-channel_my-great-video__abc123xyz_-.json", _build_artifact_filename(item))

    def test_build_artifact_filename_missing_author(self) -> None:
        item = FetchedItem(
            source_id="vid123456789",
            source_type="youtube",
            url="https://example.com",
            title="A Title",
            author=None,
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            content="",
            metadata={},
        )
        self.assertEqual("unknown_a-title__vid123456789.json", _build_artifact_filename(item))

    def test_build_artifact_filename_truncates_long_names(self) -> None:
        item = FetchedItem(
            source_id="vid123456789",
            source_type="youtube",
            url="https://example.com",
            title="A" * 300,
            author="B" * 100,
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            content="",
            metadata={},
        )
        filename = _build_artifact_filename(item)
        self.assertTrue(len(filename) <= 205)  # 200 + len(".json")
        self.assertTrue(filename.endswith(".json"))


class TestChannelHandleResolution(unittest.TestCase):
    def test_fetch_resolves_handle_and_uses_channel_id(self) -> None:
        captured_urls: list[str] = []

        def capturing_fetcher(url: str) -> str:
            captured_urls.append(url)
            return _FEED_XML

        adapter = YouTubeAdapter(
            feed_fetcher=capturing_fetcher,
            transcript_fetcher=lambda _video_id: _make_transcript_result([]),
            channel_id_resolver=lambda _handle: "UC_fake_id",
        )

        items = adapter.fetch({"channel_handle": "@testchannel"})

        self.assertEqual(2, len(items))
        self.assertIn("channel_id=UC_fake_id", captured_urls[0])

    def test_fetch_skips_source_on_resolution_failure(self) -> None:
        def failing_resolver(handle: str) -> str:
            raise ValueError(f"yt-dlp failed: {handle}")

        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result([]),
            channel_id_resolver=failing_resolver,
        )

        with self.assertLogs("src.adapters.youtube", level="WARNING") as logs:
            items = adapter.fetch({"channel_handle": "@badchannel"})

        self.assertEqual([], items)
        self.assertTrue(
            any("channel_handle_resolution_failed" in msg for msg in logs.output),
            logs.output,
        )

    def test_channel_id_present_skips_resolution(self) -> None:
        resolver_calls: list[str] = []

        def tracking_resolver(handle: str) -> str:
            resolver_calls.append(handle)
            return "UC_should_not_be_called"

        adapter = YouTubeAdapter(
            feed_fetcher=lambda _url: _FEED_XML,
            transcript_fetcher=lambda _video_id: _make_transcript_result([]),
            channel_id_resolver=tracking_resolver,
        )

        adapter.fetch({"channel_id": "UC_direct_id", "channel_handle": "@ignored"})

        self.assertEqual([], resolver_calls)

    def test_resolve_channel_handle_parses_yt_dlp_output(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "UCIgnGlGkVRhd4qNFcEwLL4A\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            channel_id = resolve_channel_handle("@theAIsearch")

        self.assertEqual("UCIgnGlGkVRhd4qNFcEwLL4A", channel_id)
        called_args = mock_run.call_args[0][0]
        self.assertIn("https://www.youtube.com/@theAIsearch", called_args)

    def test_resolve_channel_handle_strips_leading_at(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "UC123\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            resolve_channel_handle("mychannel")

        called_args = mock_run.call_args[0][0]
        self.assertIn("https://www.youtube.com/@mychannel", called_args)

    def test_resolve_channel_handle_raises_on_nonzero_exit(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Unable to resolve"

        with patch("subprocess.run", return_value=mock_result):
            with self.assertRaisesRegex(ValueError, "yt-dlp failed to resolve handle"):
                resolve_channel_handle("@notfound")


if __name__ == "__main__":
    unittest.main()
