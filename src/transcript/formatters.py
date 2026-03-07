"""Transcript output formatters."""

from __future__ import annotations

import json
from typing import Iterable, Protocol


class TranscriptEntry(Protocol):
    """Minimal transcript entry contract used by formatters."""

    text: str
    start: float
    duration: float


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format."""

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(round((seconds % 1) * 1000))

    if milliseconds == 1000:
        secs += 1
        milliseconds = 0
    if secs == 60:
        minutes += 1
        secs = 0
    if minutes == 60:
        hours += 1
        minutes = 0

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Convert seconds to VTT timestamp format."""

    return format_timestamp(seconds).replace(",", ".")


def transcript_to_text(entries: Iterable[TranscriptEntry]) -> str:
    """Render transcript entries as plain text."""

    return "\n".join(entry.text for entry in entries)


def transcript_to_json(entries: Iterable[TranscriptEntry]) -> str:
    """Render transcript entries as JSON."""

    payload = [
        {"text": entry.text, "start": entry.start, "duration": entry.duration}
        for entry in entries
    ]
    return json.dumps(payload, indent=2, ensure_ascii=False)


def transcript_to_srt(entries: Iterable[TranscriptEntry]) -> str:
    """Render transcript entries as SRT."""

    lines: list[str] = []
    for index, entry in enumerate(entries, start=1):
        start = format_timestamp(entry.start)
        end = format_timestamp(entry.start + entry.duration)
        lines.extend([str(index), f"{start} --> {end}", entry.text, ""])
    return "\n".join(lines)


def transcript_to_vtt(entries: Iterable[TranscriptEntry]) -> str:
    """Render transcript entries as WebVTT."""

    lines = ["WEBVTT", ""]
    for entry in entries:
        start = format_timestamp_vtt(entry.start)
        end = format_timestamp_vtt(entry.start + entry.duration)
        lines.extend([f"{start} --> {end}", entry.text, ""])
    return "\n".join(lines)
