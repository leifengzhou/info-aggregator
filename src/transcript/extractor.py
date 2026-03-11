"""Core transcript extraction logic."""

from __future__ import annotations

import json
import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Callable, TypeVar
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

logger = logging.getLogger(__name__)


class TranscriptError(RuntimeError):
    """Base transcript extraction error."""


class TranscriptDependencyError(TranscriptError):
    """Raised when the transcript dependency is unavailable."""


class TranscriptNotAvailableError(TranscriptError):
    """Raised when no transcript can be fetched for the requested video."""


_VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")
_JSON3_EXTENSIONS = {"json3", "srv3"}
_RETRY_JITTER_SECONDS = 0.25
_T = TypeVar("_T")


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
    cookies_file: str | None = None,
    max_retries: int = 3,
    retry_delay_seconds: float = 60.0,
    _sleep_func: Callable[[float], None] = time.sleep,
    _random_func: Callable[[], float] = random.random,
) -> TranscriptResult:
    """Fetch transcript entries for a YouTube video ID or URL."""

    _ = preserve_formatting
    video_id = extract_video_id(video)
    ydl_opts: dict[str, object] = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }
    if proxy_url:
        ydl_opts["proxy"] = proxy_url
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    info = _retry_on_429(
        lambda: _extract_info(video_id, ydl_opts),
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
        sleep_func=_sleep_func,
        random_func=_random_func,
    )

    subtitles = info.get("subtitles") or {}
    automatic_captions = info.get("automatic_captions") or {}
    requested_lang = (lang or "").strip()

    selected = _select_language_track(subtitles, automatic_captions, requested_lang)
    if selected is None:
        raise TranscriptNotAvailableError(f"No subtitles available for video {video_id}")

    language_code, tracks, is_generated = selected
    language_label = _language_label_for_track(tracks, language_code)

    if requested_lang and language_code != requested_lang:
        logger.warning(
            "transcript_language_fallback",
            extra={
                "video_id": video_id,
                "requested_language": requested_lang,
                "resolved_language_code": language_code,
                "resolved_language": language_label,
            },
        )

    track = _select_preferred_track(tracks)
    if not track:
        raise TranscriptNotAvailableError(f"No subtitles available for video {video_id}")

    subtitle_url = str(track.get("url") or "").strip()
    if not subtitle_url:
        raise TranscriptNotAvailableError(f"No subtitles available for video {video_id}")

    try:
        subtitle_payload = _retry_on_429(
            lambda: _download_subtitle_content(subtitle_url),
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            sleep_func=_sleep_func,
            random_func=_random_func,
        )
    except Exception as exc:
        if _is_429_error(exc):
            raise TranscriptNotAvailableError(f"No subtitles available for video {video_id}") from exc
        raise
    ext = str(track.get("ext") or "").lower()
    if ext in _JSON3_EXTENSIONS:
        segments = _parse_json3(subtitle_payload)
    else:
        segments = _parse_vtt(subtitle_payload)
    if not segments:
        raise TranscriptNotAvailableError(f"No subtitles available for video {video_id}")

    return TranscriptResult(
        segments=segments,
        language=language_label,
        language_code=language_code,
        is_generated=is_generated,
    )


def _extract_info(video_id: str, ydl_opts: dict) -> dict:
    """Wrap yt-dlp extraction in a mockable seam."""

    try:
        import yt_dlp
    except ImportError as exc:
        raise TranscriptDependencyError(
            "yt-dlp is not installed. Add it to the environment to fetch transcripts."
        ) from exc

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    if not isinstance(info, dict):
        raise TranscriptNotAvailableError(f"No subtitles available for video {video_id}")
    return info


def _download_subtitle_content(url: str) -> str:
    """Download subtitle text from a URL."""

    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _retry_on_429(
    operation: Callable[[], _T],
    *,
    max_retries: int,
    retry_delay_seconds: float,
    sleep_func: Callable[[float], None],
    random_func: Callable[[], float],
) -> _T:
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as exc:
            if not _is_429_error(exc) or attempt >= max_retries:
                raise
            delay = retry_delay_seconds * (2 ** attempt)
            jitter = _RETRY_JITTER_SECONDS * random_func()
            sleep_func(delay + jitter)

    raise RuntimeError("unreachable")


def _is_429_error(exc: Exception) -> bool:
    if isinstance(exc, HTTPError):
        return exc.code == 429

    try:
        from yt_dlp.utils import DownloadError
    except ImportError:
        return False

    return isinstance(exc, DownloadError) and "429" in str(exc)


def _select_language_track(
    subtitles: dict,
    automatic_captions: dict,
    requested_lang: str,
) -> tuple[str, list[dict], bool] | None:
    if requested_lang:
        manual = subtitles.get(requested_lang)
        if isinstance(manual, list) and manual:
            return requested_lang, manual, False

        generated = automatic_captions.get(requested_lang)
        if isinstance(generated, list) and generated:
            return requested_lang, generated, True

    for language_code, tracks in subtitles.items():
        if isinstance(tracks, list) and tracks:
            return str(language_code), tracks, False

    for language_code, tracks in automatic_captions.items():
        if isinstance(tracks, list) and tracks:
            return str(language_code), tracks, True

    return None


def _language_label_for_track(tracks: list[dict], fallback_code: str) -> str:
    for track in tracks:
        name = track.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return fallback_code


def _select_preferred_track(tracks: list[dict]) -> dict | None:
    for preferred_ext in ("json3", "srv3", "vtt"):
        for track in tracks:
            ext = str(track.get("ext") or "").lower()
            if ext == preferred_ext and track.get("url"):
                return track

    for track in tracks:
        if track.get("url"):
            return track
    return None


def _parse_json3(payload: str) -> list[TranscriptSegment]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []

    events = data.get("events")
    if not isinstance(events, list):
        return []

    segments: list[TranscriptSegment] = []
    for event in events:
        if not isinstance(event, dict):
            continue

        raw_segs = event.get("segs") or []
        if not isinstance(raw_segs, list):
            continue

        text = "".join(
            seg.get("utf8", "")
            for seg in raw_segs
            if isinstance(seg, dict) and isinstance(seg.get("utf8"), str)
        )
        if text in {"", "\n"}:
            continue

        start_ms = event.get("tStartMs", 0)
        duration_ms = event.get("dDurationMs", 0)
        start = float(start_ms) / 1000.0 if isinstance(start_ms, (int, float)) else 0.0
        duration = (
            float(duration_ms) / 1000.0 if isinstance(duration_ms, (int, float)) else 0.0
        )
        segments.append(TranscriptSegment(text=text, start=start, duration=duration))

    return segments


def _parse_vtt(payload: str) -> list[TranscriptSegment]:
    lines = payload.splitlines()
    segments: list[TranscriptSegment] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx].strip()
        if not line or line == "WEBVTT":
            idx += 1
            continue

        if "-->" not in line and idx + 1 < len(lines) and "-->" in lines[idx + 1]:
            idx += 1
            line = lines[idx].strip()

        if "-->" not in line:
            idx += 1
            continue

        start_text, end_text = [part.strip() for part in line.split("-->", 1)]
        try:
            start = _parse_vtt_timestamp(start_text)
            end = _parse_vtt_timestamp(end_text.split(" ", 1)[0])
        except ValueError:
            idx += 1
            continue

        idx += 1
        text_lines: list[str] = []
        while idx < len(lines) and lines[idx].strip():
            text_lines.append(lines[idx].strip())
            idx += 1

        text = "\n".join(text_lines).strip()
        if text:
            segments.append(
                TranscriptSegment(text=text, start=start, duration=max(0.0, end - start))
            )

        idx += 1

    return segments


def _parse_vtt_timestamp(value: str) -> float:
    value = value.strip()
    parts = value.split(":")
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2].replace(",", "."))
    elif len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1].replace(",", "."))
    else:
        raise ValueError(f"Invalid VTT timestamp: {value}")
    return (hours * 3600) + (minutes * 60) + seconds
