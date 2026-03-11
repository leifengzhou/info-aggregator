"""Reddit source adapter."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.adapters import BaseAdapter, FetchedItem
from src.db import insert_content, link_content_topic

logger = logging.getLogger(__name__)

_REDDIT_BASE_URL = "https://www.reddit.com"
_USER_AGENT = "python:info-aggregator:v0.1 (personal use)"


@dataclass(frozen=True)
class RedditIngestResult:
    """Summary of a Reddit ingestion run."""

    discovered: int
    inserted: int
    deduped: int
    linked: int


class RedditAdapter(BaseAdapter):
    """Fetch Reddit posts from public subreddit JSON endpoints."""

    def __init__(
        self,
        json_fetcher: Callable[[str], object] | None = None,
        comment_request_delay_seconds: float = 1.0,
        sleep_func: Callable[[float], None] | None = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self._json_fetcher = json_fetcher or (
            lambda url: _fetch_json_with_retry(
                url,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                sleep_func=sleep_func or time.sleep,
            )
        )
        self._comment_request_delay_seconds = comment_request_delay_seconds
        self._sleep = sleep_func or time.sleep

    def fetch(self, source_config: dict, since: datetime | None = None) -> list[FetchedItem]:
        subreddit = str(source_config["subreddit"]).strip()
        sort = str(source_config.get("sort", "new")).strip().lower()
        limit = int(source_config.get("limit", 25))
        comment_limit = int(source_config.get("comment_limit", 0))
        min_score = source_config.get("min_score")
        min_score_int = int(min_score) if min_score is not None else None

        posts_url = _build_posts_url(subreddit=subreddit, sort=sort, limit=limit)
        logger.info(
            "reddit_fetch_started",
            extra={
                "subreddit": subreddit,
                "sort": sort,
                "limit": limit,
                "comment_limit": comment_limit,
                "min_score": min_score_int,
                "since": since.isoformat() if since else None,
                "url": posts_url,
            },
        )

        try:
            listing = self._json_fetcher(posts_url)
        except HTTPError as exc:
            if exc.code == 404:
                logger.warning(
                    "reddit_subreddit_unavailable",
                    extra={"subreddit": subreddit, "status_code": 404},
                )
                return []
            logger.warning(
                "reddit_fetch_failed",
                extra={"subreddit": subreddit, "status_code": exc.code},
            )
            return []
        except (URLError, TimeoutError, ValueError) as exc:
            logger.warning(
                "reddit_fetch_failed",
                extra={"subreddit": subreddit, "error": str(exc)},
            )
            return []

        items: list[FetchedItem] = []
        children = _extract_listing_children(listing)
        comment_request_count = 0
        for child in children:
            data = child.get("data", {})
            post_id = str(data.get("id", "")).strip()
            if not post_id:
                continue

            published_at = _parse_created_utc(data.get("created_utc"))
            if published_at is None:
                continue
            if since is not None and published_at < since:
                continue

            score = _as_int(data.get("score"))
            if min_score_int is not None and score < min_score_int:
                logger.debug(
                    "reddit_post_skipped_min_score",
                    extra={"subreddit": subreddit, "post_id": post_id, "score": score, "min_score": min_score_int},
                )
                continue

            comments: list[dict] = []
            if comment_limit > 0:
                comments_url = _build_comments_url(subreddit=subreddit, post_id=post_id, limit=comment_limit)
                if comment_request_count > 0 and self._comment_request_delay_seconds > 0:
                    self._sleep(self._comment_request_delay_seconds)
                comment_request_count += 1
                try:
                    comments_payload = self._json_fetcher(comments_url)
                    comments = _extract_top_level_comments(comments_payload, comment_limit)
                except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                    logger.warning(
                        "reddit_comments_fetch_failed",
                        extra={"subreddit": subreddit, "post_id": post_id, "error": str(exc)},
                    )
                    comments = []

            permalink = str(data.get("permalink") or f"/r/{subreddit}/comments/{post_id}/")
            post_url = f"{_REDDIT_BASE_URL}{permalink}" if permalink.startswith("/") else permalink
            is_self = bool(data.get("is_self", False))
            external_url = str(data.get("url") or post_url)
            selftext = str(data.get("selftext") or "")
            content = _build_post_content(
                is_self=is_self,
                selftext=selftext,
                external_url=external_url,
                comments=comments,
            )

            flair = data.get("link_flair_text")
            author = data.get("author")
            normalized_author = None if not author or author == "[deleted]" else str(author)
            item = FetchedItem(
                source_id=f"reddit_{post_id}",
                source_type="reddit",
                url=post_url,
                title=str(data.get("title") or ""),
                author=normalized_author,
                published_at=published_at,
                content=content,
                metadata={
                    "subreddit": subreddit,
                    "score": score,
                    "upvote_ratio": data.get("upvote_ratio"),
                    "num_comments": _as_int(data.get("num_comments")),
                    "flair": flair,
                    "is_self": is_self,
                    "post_type": "self" if is_self else "link",
                    "comments": comments,
                },
            )
            items.append(item)

        logger.info(
            "reddit_fetch_completed",
            extra={"subreddit": subreddit, "item_count": len(items)},
        )
        return items


def ingest_reddit_source(
    conn,
    topic: str,
    source_config: dict,
    content_root: str | Path,
    since: datetime | None = None,
    request_delay_seconds: float = 1.0,
    adapter: RedditAdapter | None = None,
) -> RedditIngestResult:
    """Fetch, persist, and link Reddit items for a single topic/source."""

    logger.info(
        "reddit_ingest_started",
        extra={"topic": topic, "since": since.isoformat() if since else None},
    )
    active_adapter = adapter or RedditAdapter(comment_request_delay_seconds=request_delay_seconds)
    items = active_adapter.fetch(source_config, since=since)

    output_dir = Path(content_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    inserted = 0
    deduped = 0
    linked = 0
    for item in items:
        artifact_path = output_dir / _build_artifact_filename(item)

        if insert_content(conn, item, str(artifact_path)):
            _write_item_artifact(artifact_path, item)
            inserted += 1
        else:
            deduped += 1

        link_content_topic(conn, item.source_id, topic)
        linked += 1

    result = RedditIngestResult(
        discovered=len(items),
        inserted=inserted,
        deduped=deduped,
        linked=linked,
    )
    logger.info(
        "reddit_ingest_completed",
        extra={
            "topic": topic,
            "discovered": result.discovered,
            "inserted": result.inserted,
            "deduped": result.deduped,
            "linked": result.linked,
        },
    )
    return result


def _fetch_json_with_retry(
    url: str,
    *,
    max_retries: int,
    retry_delay_seconds: float,
    sleep_func: Callable[[float], None],
) -> object:
    for attempt in range(max_retries + 1):
        try:
            return _fetch_json(url)
        except HTTPError as exc:
            if exc.code != 429 or attempt >= max_retries:
                raise
            sleep_func(retry_delay_seconds * (2 ** attempt))

    raise RuntimeError("unreachable")


def _fetch_json(url: str) -> object:
    request = Request(
        url=url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _build_posts_url(subreddit: str, sort: str, limit: int) -> str:
    query = urlencode({"limit": limit, "raw_json": 1})
    return f"{_REDDIT_BASE_URL}/r/{subreddit}/{sort}.json?{query}"


def _build_comments_url(subreddit: str, post_id: str, limit: int) -> str:
    query = urlencode({"limit": limit, "raw_json": 1, "sort": "top"})
    return f"{_REDDIT_BASE_URL}/r/{subreddit}/comments/{post_id}.json?{query}"


def _extract_listing_children(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise ValueError("Invalid Reddit listing response")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Invalid Reddit listing response")
    children = data.get("children")
    if not isinstance(children, list):
        raise ValueError("Invalid Reddit listing response")
    return [child for child in children if isinstance(child, dict)]


def _extract_top_level_comments(payload: object, limit: int) -> list[dict]:
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("Invalid Reddit comments response")

    listing = payload[1]
    if not isinstance(listing, dict):
        raise ValueError("Invalid Reddit comments response")
    data = listing.get("data")
    if not isinstance(data, dict):
        raise ValueError("Invalid Reddit comments response")
    children = data.get("children")
    if not isinstance(children, list):
        raise ValueError("Invalid Reddit comments response")

    comments: list[dict] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        if child.get("kind") != "t1":
            continue
        comment = child.get("data")
        if not isinstance(comment, dict):
            continue
        comments.append(
            {
                "id": str(comment.get("id") or ""),
                "author": str(comment.get("author") or "[deleted]"),
                "body": str(comment.get("body") or ""),
                "score": _as_int(comment.get("score")),
            }
        )

    comments.sort(key=lambda item: item["score"], reverse=True)
    return comments[:limit]


def _build_post_content(
    *,
    is_self: bool,
    selftext: str,
    external_url: str,
    comments: list[dict],
) -> str:
    base = selftext.strip() if is_self else external_url.strip()
    if not comments:
        return base

    comment_lines = [
        f"- u/{comment['author']} ({comment['score']}): {comment['body']}"
        for comment in comments
    ]
    return f"{base}\n\n---\nTop Comments ({len(comments)}):\n" + "\n".join(comment_lines)


def _parse_created_utc(value: object) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _build_artifact_filename(item: FetchedItem) -> str:
    subreddit = _slugify(str(item.metadata.get("subreddit") or "reddit"))
    title = _slugify(item.title or "untitled")
    base = f"{subreddit}_{title}__{item.source_id}"
    return base[:200] + ".json"


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
