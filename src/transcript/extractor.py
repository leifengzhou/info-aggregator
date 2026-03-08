"""Core transcript extraction logic."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import parse_qs, urlparse


class TranscriptError(RuntimeError):
    """Base transcript extraction error."""


class TranscriptDependencyError(TranscriptError):
    """Raised when the transcript dependency is unavailable."""


class TranscriptNotAvailableError(TranscriptError):
    """Raised when no transcript can be fetched for the requested video."""


_VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


@dataclass(frozen=True)
class TranscriptSegment:
    """Normalized transcript segment."""

    text: str
    start: float
    duration: float


@dataclass(frozen=True)
class TranscriptResult:
    """Full transcript fetch result with metadata."""

    segments: list[TranscriptSegment]
    language: str
    language_code: str
    is_generated: bool


def extract_video_id(value: str) -> str:
    """Extract a YouTube video ID from a URL or accept an 11-character ID directly."""

    candidate = value.strip()
    if _VIDEO_ID_PATTERN.fullmatch(candidate):
        return candidate

    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if host in {"youtu.be", "www.youtu.be"} and _VIDEO_ID_PATTERN.fullmatch(path):
        return path

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_ids = parse_qs(parsed.query).get("v", [])
            if video_ids and _VIDEO_ID_PATTERN.fullmatch(video_ids[0]):
                return video_ids[0]

        if parsed.path.startswith("/live/") or parsed.path.startswith("/embed/"):
            maybe_id = path.split("/", 1)[1] if "/" in path else ""
            if _VIDEO_ID_PATTERN.fullmatch(maybe_id):
                return maybe_id

    raise ValueError(f"Could not extract a YouTube video ID from: {value}")


def fetch_transcript(
    video: str,
    lang: str = "en",
    proxy_url: str | None = None,
    preserve_formatting: bool = False,
) -> TranscriptResult:
    """Fetch transcript entries for a YouTube video ID or URL."""

    video_id = extract_video_id(video)
    api = _build_api(proxy_url)
    languages = [lang] if lang else None

    try:
        transcript = _fetch(api, video_id, languages, preserve_formatting)
    except Exception as primary_exc:
        if languages is None:
            raise TranscriptNotAvailableError(
                f"No subtitles available for video {video_id}"
            ) from primary_exc
        try:
            transcript = _fetch(api, video_id, None, preserve_formatting)
        except Exception as fallback_exc:
            raise TranscriptNotAvailableError(
                f"No subtitles available for video {video_id}"
            ) from fallback_exc

    return TranscriptResult(
        segments=_normalize_snippets(transcript.snippets),
        language=transcript.language,
        language_code=transcript.language_code,
        is_generated=transcript.is_generated,
    )


def _build_api(proxy_url: str | None):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.proxies import ProxyConfig
    except ImportError as exc:
        raise TranscriptDependencyError(
            "youtube-transcript-api is not installed. Add it to the environment to fetch transcripts."
        ) from exc

    if proxy_url:
        return YouTubeTranscriptApi(proxy_config=ProxyConfig.from_url(proxy_url))
    return YouTubeTranscriptApi()


def _fetch(api, video_id: str, languages: list[str] | None, preserve_formatting: bool):
    kwargs = {"preserve_formatting": preserve_formatting}
    if languages is not None:
        kwargs["languages"] = languages
    return api.fetch(video_id, **kwargs)


def _normalize_snippets(snippets: Iterable[object]) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            text=getattr(snippet, "text"),
            start=float(getattr(snippet, "start")),
            duration=float(getattr(snippet, "duration")),
        )
        for snippet in snippets
    ]
