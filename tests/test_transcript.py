"""Tests for transcript extraction and formatting."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.transcript import (
    TranscriptNotAvailableError,
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
    @patch("src.transcript.extractor._build_api")
    def test_fetch_transcript_returns_normalized_segments(self, build_api_mock) -> None:
        fake_api = build_api_mock.return_value
        fake_api.fetch.return_value = SimpleNamespace(
            snippets=[
                SimpleNamespace(text="Hello", start=0.0, duration=1.2),
                SimpleNamespace(text="World", start=1.2, duration=0.8),
            ]
        )

        entries = fetch_transcript("dQw4w9WgXcQ")

        self.assertEqual(
            [
                TranscriptSegment(text="Hello", start=0.0, duration=1.2),
                TranscriptSegment(text="World", start=1.2, duration=0.8),
            ],
            entries,
        )
        fake_api.fetch.assert_called_once_with(
            "dQw4w9WgXcQ", languages=["en"], preserve_formatting=False
        )

    @patch("src.transcript.extractor._build_api")
    def test_fetch_transcript_falls_back_to_any_language(self, build_api_mock) -> None:
        fake_api = build_api_mock.return_value
        fake_api.fetch.side_effect = [
            RuntimeError("missing requested language"),
            SimpleNamespace(snippets=[SimpleNamespace(text="Hola", start=0.0, duration=1.0)]),
        ]

        entries = fetch_transcript("dQw4w9WgXcQ", lang="en")

        self.assertEqual([TranscriptSegment(text="Hola", start=0.0, duration=1.0)], entries)
        self.assertEqual(2, fake_api.fetch.call_count)
        self.assertEqual(
            ("dQw4w9WgXcQ",),
            fake_api.fetch.call_args_list[1].args,
        )
        self.assertEqual(
            {"preserve_formatting": False},
            fake_api.fetch.call_args_list[1].kwargs,
        )

    @patch("src.transcript.extractor._build_api")
    def test_fetch_transcript_raises_when_no_transcript_available(self, build_api_mock) -> None:
        fake_api = build_api_mock.return_value
        fake_api.fetch.side_effect = RuntimeError("no transcript")

        with self.assertRaisesRegex(
            TranscriptNotAvailableError, "No subtitles available for video dQw4w9WgXcQ"
        ):
            fetch_transcript("https://youtu.be/dQw4w9WgXcQ")


if __name__ == "__main__":
    unittest.main()
