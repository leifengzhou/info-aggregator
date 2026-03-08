"""YouTube source adapter."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen
from xml.etree import ElementTree

from src.adapters import BaseAdapter, FetchedItem
from src.db import content_exists, insert_content, link_content_topic
from src.transcript import TranscriptNotAvailableError, fetch_transcript

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
        transcript_fetcher: Callable[[str], list] | None = None,
    ) -> None:
        self._feed_fetcher = feed_fetcher or _fetch_feed
        self._transcript_fetcher = transcript_fetcher or fetch_transcript

    def fetch(
        self, source_config: dict, since: datetime | None = None
    ) -> list[FetchedItem]:
        feed_url, locator_metadata = _build_feed_url(source_config)
        try:
            feed_xml = self._feed_fetcher(feed_url)
            discovered_videos = _parse_feed(feed_xml, since=since)
        except (HTTPError, URLError, TimeoutError, ElementTree.ParseError) as exc:
            logger.warning("youtube_feed_unavailable url=%s error=%s", feed_url, exc)
            return []

        items: list[FetchedItem] = []
        for video in discovered_videos:
            try:
                transcript_segments = self._transcript_fetcher(video.video_id)
                transcript_text = "\n".join(segment.text for segment in transcript_segments)
                transcript_available = True
            except TranscriptNotAvailableError:
                transcript_segments = []
                transcript_text = ""
                transcript_available = False

            metadata = {
                **locator_metadata,
                "video_id": video.video_id,
                "channel_title": video.author,
                "transcript_available": transcript_available,
                "transcript_segment_count": len(transcript_segments),
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
    adapter: YouTubeAdapter | None = None,
) -> YouTubeIngestResult:
    """Fetch, persist, and link YouTube items for a single topic/source."""

    active_adapter = adapter or YouTubeAdapter()
    items = active_adapter.fetch(source_config, since=since)
    output_dir = Path(content_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    inserted = 0
    deduped = 0
    linked = 0
    missing_transcripts = 0

    for item in items:
        already_exists = content_exists(conn, item.source_id)
        artifact_path = output_dir / f"{item.source_id}.json"

        if not already_exists:
            _write_item_artifact(artifact_path, item)
            if insert_content(conn, item, str(artifact_path)):
                inserted += 1
        else:
            deduped += 1

        link_content_topic(conn, item.source_id, topic)
        linked += 1

        if not item.metadata.get("transcript_available", True):
            missing_transcripts += 1

    return YouTubeIngestResult(
        discovered=len(items),
        inserted=inserted,
        deduped=deduped,
        linked=linked,
        missing_transcripts=missing_transcripts,
    )


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
