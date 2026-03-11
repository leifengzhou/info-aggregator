"""YouTube source adapter."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen
from xml.etree import ElementTree

from src.adapters import BaseAdapter, FetchedItem
from src.db import insert_content, link_content_topic
from src.transcript import (
    TranscriptError,
    TranscriptResult,
    fetch_transcript,
    transcript_to_text,
)

def resolve_channel_handle(handle: str) -> str:
    """Resolve a YouTube @handle to a channel_id via yt-dlp.

    Raises ValueError if yt-dlp returns a non-zero exit code or empty output.
    """
    url = f"https://www.youtube.com/@{handle.lstrip('@')}"
    result = subprocess.run(
        ["yt-dlp", "--print", "channel_id", "--playlist-end", "1", url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    channel_id = result.stdout.strip()
    if result.returncode != 0 or not channel_id:
        raise ValueError(
            f"yt-dlp failed to resolve handle '{handle}': {result.stderr.strip()}"
        )
    return channel_id


_ATOM_NAMESPACE = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class YouTubeIngestResult:
    """Summary of a YouTube ingestion run."""

    discovered: int
    inserted: int
    deduped: int
    linked: int
    missing_transcripts: int


class YouTubeAdapter(BaseAdapter):
    """Discover YouTube videos from RSS and fetch transcript-backed items."""

    def __init__(
        self,
        feed_fetcher: Callable[[str], str] | None = None,
        transcript_fetcher: Callable[[str], TranscriptResult] | None = None,
        transcript_delay_seconds: float = 1.0,
        youtube_cookies_file: str | None = None,
        transcript_max_retries: int = 3,
        transcript_retry_delay_seconds: float = 60.0,
        sleep_func: Callable[[float], None] | None = None,
        channel_id_resolver: Callable[[str], str] | None = None,
    ) -> None:
        self._feed_fetcher = feed_fetcher or _fetch_feed
        if transcript_fetcher is not None:
            self._transcript_fetcher = transcript_fetcher
        else:
            self._transcript_fetcher = lambda video_id: fetch_transcript(
                video_id,
                cookies_file=youtube_cookies_file,
                max_retries=transcript_max_retries,
                retry_delay_seconds=transcript_retry_delay_seconds,
            )
        self._transcript_delay_seconds = transcript_delay_seconds
        self._sleep = sleep_func or time.sleep
        self._channel_id_resolver = channel_id_resolver or resolve_channel_handle

    def fetch(
        self, source_config: dict, since: datetime | None = None
    ) -> list[FetchedItem]:
        # Resolve handle → channel_id if needed
        if not source_config.get("channel_id") and source_config.get("channel_handle"):
            handle = source_config["channel_handle"]
            try:
                channel_id = self._channel_id_resolver(handle)
                logger.info(
                    "channel_handle_resolved",
                    extra={"handle": handle, "channel_id": channel_id},
                )
            except (ValueError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
                logger.warning(
                    "channel_handle_resolution_failed",
                    extra={"handle": handle, "error": str(exc)},
                )
                return []
            source_config = {**source_config, "channel_id": channel_id}

        feed_url, locator_metadata = _build_feed_url(source_config)
        logger.info(
            "youtube_fetch_started",
            extra={"feed_url": feed_url, "since": since.isoformat() if since else None, **locator_metadata},
        )
        try:
            feed_xml = self._feed_fetcher(feed_url)
            discovered_videos = _parse_feed(feed_xml, since=since)
        except (HTTPError, URLError, TimeoutError, ElementTree.ParseError) as exc:
            logger.warning("youtube_feed_unavailable url=%s error=%s", feed_url, exc)
            return []

        items: list[FetchedItem] = []
        for index, video in enumerate(discovered_videos):
            if index > 0 and self._transcript_delay_seconds > 0:
                logger.debug(
                    "youtube_transcript_throttled",
                    extra={
                        "video_id": video.video_id,
                        "delay_seconds": self._transcript_delay_seconds,
                    },
                )
                self._sleep(self._transcript_delay_seconds)
            try:
                result = self._transcript_fetcher(video.video_id)
                transcript_segments = result.segments
                transcript_text = transcript_to_text(transcript_segments)
                transcript_available = True
                is_generated = result.is_generated
                transcript_language = result.language_code
            except TranscriptError:
                transcript_segments = []
                transcript_text = ""
                transcript_available = False
                is_generated = None
                transcript_language = None
                logger.warning(
                    "youtube_transcript_missing",
                    extra={"video_id": video.video_id, "url": video.url},
                )

            metadata = {
                **locator_metadata,
                "video_id": video.video_id,
                "channel_title": video.author,
                "transcript_available": transcript_available,
                "transcript_segment_count": len(transcript_segments),
                "transcript_is_generated": is_generated,
                "transcript_language": transcript_language,
            }

            items.append(
                FetchedItem(
                    source_id=video.video_id,
                    source_type="youtube",
                    url=video.url,
                    title=video.title,
                    author=video.author,
                    published_at=video.published_at,
                    content=transcript_text,
                    metadata=metadata,
                )
            )

        logger.info(
            "youtube_fetch_completed",
            extra={"feed_url": feed_url, "item_count": len(items), **locator_metadata},
        )
        return items


@dataclass(frozen=True)
class _DiscoveredVideo:
    """A video entry discovered from the YouTube RSS feed."""

    video_id: str
    title: str
    author: str | None
    published_at: datetime
    url: str


def ingest_youtube_source(
    conn,
    topic: str,
    source_config: dict,
    content_root: str | Path,
    since: datetime | None = None,
    transcript_delay_seconds: float = 1.0,
    youtube_cookies_file: str | None = None,
    transcript_max_retries: int = 3,
    adapter: YouTubeAdapter | None = None,
) -> YouTubeIngestResult:
    """Fetch, persist, and link YouTube items for a single topic/source."""

    logger.info(
        "youtube_ingest_started",
        extra={"topic": topic, "since": since.isoformat() if since else None},
    )
    active_adapter = adapter or YouTubeAdapter(
        transcript_delay_seconds=transcript_delay_seconds,
        youtube_cookies_file=youtube_cookies_file,
        transcript_max_retries=transcript_max_retries,
    )
    items = active_adapter.fetch(source_config, since=since)
    output_dir = Path(content_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    inserted = 0
    deduped = 0
    linked = 0
    missing_transcripts = 0

    for item in items:
        artifact_path = output_dir / _build_artifact_filename(item)

        if insert_content(conn, item, str(artifact_path)):
            _write_item_artifact(artifact_path, item)
            inserted += 1
        else:
            deduped += 1

        link_content_topic(conn, item.source_id, topic)
        linked += 1

        if not item.metadata.get("transcript_available", True):
            missing_transcripts += 1

    result = YouTubeIngestResult(
        discovered=len(items),
        inserted=inserted,
        deduped=deduped,
        linked=linked,
        missing_transcripts=missing_transcripts,
    )
    logger.info(
        "youtube_ingest_completed",
        extra={
            "topic": topic,
            "discovered": result.discovered,
            "inserted": result.inserted,
            "deduped": result.deduped,
            "linked": result.linked,
            "missing_transcripts": result.missing_transcripts,
        },
    )
    return result


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _build_artifact_filename(item: FetchedItem) -> str:
    """Build a human-readable artifact filename from item metadata."""
    channel = _slugify(item.author or "unknown")
    title = _slugify(item.title or "untitled")
    base = f"{channel}_{title}__{item.source_id}"
    # Truncate to 200 chars to stay under ext4's 255 limit with .json suffix
    return base[:200] + ".json"


def _build_feed_url(source_config: dict) -> tuple[str, dict[str, str]]:
    channel_id = source_config.get("channel_id")
    if isinstance(channel_id, str) and channel_id.strip():
        normalized = channel_id.strip()
        query = urlencode({"channel_id": normalized})
        return (
            f"https://www.youtube.com/feeds/videos.xml?{query}",
            {"channel_id": normalized},
        )

    playlist_url = source_config.get("playlist_url")
    if isinstance(playlist_url, str) and playlist_url.strip():
        playlist_id = _extract_playlist_id(playlist_url)
        query = urlencode({"playlist_id": playlist_id})
        return (
            f"https://www.youtube.com/feeds/videos.xml?{query}",
            {"playlist_id": playlist_id},
        )

    raise ValueError("YouTube source_config must include channel_id or playlist_url")


def _extract_playlist_id(playlist_url: str) -> str:
    parsed = urlparse(playlist_url)
    playlist_ids = parse_qs(parsed.query).get("list", [])
    if playlist_ids and playlist_ids[0].strip():
        return playlist_ids[0].strip()
    raise ValueError(f"Could not extract playlist ID from: {playlist_url}")


def _fetch_feed(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def _parse_feed(feed_xml: str, since: datetime | None = None) -> list[_DiscoveredVideo]:
    root = ElementTree.fromstring(feed_xml)
    videos: list[_DiscoveredVideo] = []

    for entry in root.findall("atom:entry", _ATOM_NAMESPACE):
        video_id = _require_text(entry, "yt:videoId")
        title = _require_text(entry, "atom:title")
        published_text = _require_text(entry, "atom:published")
        published_at = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
        if since is not None and published_at < since:
            continue

        author_name = entry.findtext("atom:author/atom:name", default=None, namespaces=_ATOM_NAMESPACE)
        link = entry.find("atom:link[@rel='alternate']", _ATOM_NAMESPACE)
        url = link.attrib["href"] if link is not None else f"https://www.youtube.com/watch?v={video_id}"

        videos.append(
            _DiscoveredVideo(
                video_id=video_id,
                title=title,
                author=author_name,
                published_at=published_at,
                url=url,
            )
        )

    return videos


def _require_text(entry: ElementTree.Element, selector: str) -> str:
    value = entry.findtext(selector, default="", namespaces=_ATOM_NAMESPACE)
    if not value:
        raise ValueError(f"Missing required RSS field: {selector}")
    return value


def _write_item_artifact(path: Path, item: FetchedItem) -> None:
    payload = {
        "source_id": item.source_id,
        "source_type": item.source_type,
        "url": item.url,
        "title": item.title,
        "author": item.author,
        "published_at": item.published_at.isoformat(),
        "content": item.content,
        "metadata": item.metadata,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
