"""Tests for transcript extraction and formatting."""

from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from src.transcript import (
    TranscriptNotAvailableError,
    TranscriptResult,
    TranscriptSegment,
    extract_video_id,
    fetch_transcript,
    format_timestamp,
    format_timestamp_vtt,
    transcript_to_json,
    transcript_to_srt,
    transcript_to_text,
    transcript_to_vtt,
)


class TranscriptUtilityTests(unittest.TestCase):
    def test_extract_video_id_from_watch_url(self) -> None:
        self.assertEqual(
            "dQw4w9WgXcQ",
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
        )

    def test_extract_video_id_from_id(self) -> None:
        self.assertEqual("dQw4w9WgXcQ", extract_video_id("dQw4w9WgXcQ"))

    def test_extract_video_id_rejects_invalid_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "Could not extract a YouTube video ID"):
            extract_video_id("https://example.com/not-youtube")


class FormatterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = [
            TranscriptSegment(text="Hello world", start=1.25, duration=2.5),
            TranscriptSegment(text="Second line", start=4.0, duration=1.0),
        ]

    def test_format_timestamp(self) -> None:
        self.assertEqual("00:00:01,250", format_timestamp(1.25))

    def test_format_timestamp_vtt(self) -> None:
        self.assertEqual("00:00:01.250", format_timestamp_vtt(1.25))

    def test_transcript_to_text(self) -> None:
        self.assertEqual("Hello world\nSecond line", transcript_to_text(self.entries))

    def test_transcript_to_json(self) -> None:
        payload = json.loads(transcript_to_json(self.entries))
        self.assertEqual("Hello world", payload[0]["text"])
        self.assertEqual(4.0, payload[1]["start"])

    def test_transcript_to_srt(self) -> None:
        rendered = transcript_to_srt(self.entries)
        self.assertIn("1\n00:00:01,250 --> 00:00:03,750\nHello world\n", rendered)
        self.assertIn("2\n00:00:04,000 --> 00:00:05,000\nSecond line\n", rendered)

    def test_transcript_to_vtt(self) -> None:
        rendered = transcript_to_vtt(self.entries)
        self.assertTrue(rendered.startswith("WEBVTT\n\n"))
        self.assertIn("00:00:01.250 --> 00:00:03.750", rendered)


class FetchTranscriptTests(unittest.TestCase):
    @patch("src.transcript.extractor._download_subtitle_content")
    @patch("src.transcript.extractor._extract_info")
    def test_fetch_transcript_returns_transcript_result(
        self,
        extract_info_mock,
        download_mock,
    ) -> None:
        extract_info_mock.return_value = {
            "subtitles": {
                "en": [
                    {"ext": "json3", "url": "https://example.com/en.json3", "name": "English"}
                ]
            },
            "automatic_captions": {},
        }
        download_mock.return_value = json.dumps(
            {
                "events": [
                    {"tStartMs": 0, "dDurationMs": 1200, "segs": [{"utf8": "Hello"}]},
                    {"tStartMs": 1200, "dDurationMs": 800, "segs": [{"utf8": "World"}]},
                ]
            }
        )

        result = fetch_transcript("dQw4w9WgXcQ")

        self.assertIsInstance(result, TranscriptResult)
        self.assertEqual(
            [
                TranscriptSegment(text="Hello", start=0.0, duration=1.2),
                TranscriptSegment(text="World", start=1.2, duration=0.8),
            ],
            result.segments,
        )
        self.assertEqual("English", result.language)
        self.assertEqual("en", result.language_code)
        self.assertFalse(result.is_generated)

    @patch("src.transcript.extractor._download_subtitle_content")
    @patch("src.transcript.extractor._extract_info")
    def test_fetch_transcript_falls_back_to_any_language(
        self,
        extract_info_mock,
        download_mock,
    ) -> None:
        extract_info_mock.return_value = {
            "subtitles": {},
            "automatic_captions": {
                "es": [{"ext": "json3", "url": "https://example.com/es.json3", "name": "Spanish"}]
            },
        }
        download_mock.return_value = json.dumps(
            {"events": [{"tStartMs": 0, "dDurationMs": 1000, "segs": [{"utf8": "Hola"}]}]}
        )

        with self.assertLogs("src.transcript.extractor", level="WARNING") as logs:
            result = fetch_transcript("dQw4w9WgXcQ", lang="en")

        self.assertEqual([TranscriptSegment(text="Hola", start=0.0, duration=1.0)], result.segments)
        self.assertTrue(result.is_generated)
        self.assertEqual("es", result.language_code)
        self.assertTrue(any("transcript_language_fallback" in message for message in logs.output))

    @patch("src.transcript.extractor._extract_info")
    def test_fetch_transcript_retries_on_429(self, extract_info_mock) -> None:
        from yt_dlp.utils import DownloadError

        calls: list[float] = []
        extract_info_mock.side_effect = [
            DownloadError("HTTP Error 429: Too Many Requests"),
            {"subtitles": {"en": [{"ext": "vtt", "url": "https://example.com/en.vtt"}]}},
        ]

        with patch(
            "src.transcript.extractor._download_subtitle_content",
            return_value="WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHi\n",
        ):
            result = fetch_transcript(
                "dQw4w9WgXcQ",
                max_retries=2,
                retry_delay_seconds=1.5,
                _sleep_func=calls.append,
                _random_func=lambda: 0.0,
            )

        self.assertEqual("en", result.language_code)
        self.assertEqual([1.5], calls)
        self.assertEqual(2, extract_info_mock.call_count)

    @patch("src.transcript.extractor._extract_info")
    def test_fetch_transcript_retries_when_subtitle_download_hits_429(self, extract_info_mock) -> None:
        extract_info_mock.return_value = {
            "subtitles": {"en": [{"ext": "vtt", "url": "https://example.com/en.vtt"}]},
            "automatic_captions": {},
        }
        calls: list[float] = []
        too_many_requests = HTTPError(
            url="https://example.com/en.vtt",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None,
        )

        with patch(
            "src.transcript.extractor._download_subtitle_content",
            side_effect=[
                too_many_requests,
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHi\n",
            ],
        ) as download_mock:
            result = fetch_transcript(
                "dQw4w9WgXcQ",
                max_retries=2,
                retry_delay_seconds=1.5,
                _sleep_func=calls.append,
                _random_func=lambda: 0.0,
            )

        self.assertEqual("en", result.language_code)
        self.assertEqual([TranscriptSegment(text="Hi", start=0.0, duration=1.0)], result.segments)
        self.assertEqual([1.5], calls)
        self.assertEqual(2, download_mock.call_count)

    @patch("src.transcript.extractor._extract_info")
    def test_fetch_transcript_raises_not_available_after_subtitle_download_429_retries(self, extract_info_mock) -> None:
        extract_info_mock.return_value = {
            "subtitles": {"en": [{"ext": "vtt", "url": "https://example.com/en.vtt"}]},
            "automatic_captions": {},
        }
        too_many_requests = HTTPError(
            url="https://example.com/en.vtt",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None,
        )
        calls: list[float] = []

        with patch(
            "src.transcript.extractor._download_subtitle_content",
            side_effect=[too_many_requests, too_many_requests, too_many_requests],
        ):
            with self.assertRaisesRegex(
                TranscriptNotAvailableError,
                "No subtitles available for video dQw4w9WgXcQ",
            ):
                fetch_transcript(
                    "dQw4w9WgXcQ",
                    max_retries=2,
                    retry_delay_seconds=1.5,
                    _sleep_func=calls.append,
                    _random_func=lambda: 0.0,
                )

        self.assertEqual([1.5, 3.0], calls)

    @patch("src.transcript.extractor._extract_info")
    def test_fetch_transcript_raises_when_no_transcript_available(self, extract_info_mock) -> None:
        extract_info_mock.return_value = {"subtitles": {}, "automatic_captions": {}}

        with self.assertRaisesRegex(
            TranscriptNotAvailableError, "No subtitles available for video dQw4w9WgXcQ"
        ):
            fetch_transcript("https://youtu.be/dQw4w9WgXcQ")


if __name__ == "__main__":
    unittest.main()
