# Info Aggregator - Technical Specification

This document contains all implementation details for the Info Aggregator. For product requirements, user stories, and acceptance criteria, see `PRD.md`.

## Tech Stack

- **Language**: Python 3.11+
- **Database**: SQLite (metadata, scores, summaries)
- **Storage**: Local filesystem for raw content
- **Scheduling**: cron (system-level) or APScheduler (in-process)
- **LLM**: DeepSeek and MiniMax (default); architecture supports swapping providers
- **YouTube transcripts**: Built-in adapter (migrated from openclaw skill)
- **Location**: `~/projects/info-aggregator/`

## Project Structure

```
~/projects/info-aggregator/
├── config/
│   └── topics.yaml              # All topic + source definitions
├── src/
│   ├── __init__.py
│   ├── main.py                  # CLI entry point
│   ├── config.py                # Load and validate topics.yaml
│   ├── db.py                    # SQLite operations
│   ├── adapters/                # Source adapters (one per platform)
│   │   ├── __init__.py          # Base adapter interface
│   │   ├── youtube.py           # YouTube: RSS feed + transcript extraction
│   │   ├── reddit.py            # Reddit: JSON API
│   │   ├── rss.py               # Generic RSS/Atom feeds
│   │   └── hackernews.py        # Hacker News API
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── pipeline.py          # Orchestrates the analysis steps
│   │   ├── relevance.py         # LLM relevance scoring
│   │   └── summarizer.py        # LLM summarization + tagging
│   ├── transcript/              # YouTube transcript library (migrated)
│   │   ├── __init__.py          # Public API: fetch_transcript()
│   │   ├── extractor.py         # Core extraction logic
│   │   └── formatters.py        # text/json/srt/vtt output formats
│   └── output/
│       ├── __init__.py
│       └── digest.py            # Digest generation (Markdown, JSON)
├── data/
│   ├── content/                 # Raw content organized by source
│   │   ├── youtube/
│   │   ├── reddit/
│   │   ├── rss/
│   │   └── hackernews/
│   ├── aggregator.db            # SQLite database
│   └── digests/                 # Generated digests (per topic, per date)
│       ├── ai-research/
│       ├── market-trends/
│       └── ...
├── requirements.txt
└── README.md
```

## Architecture

```
+------------------------------------------------------------------+
|                      Info Aggregator Service                       |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+                                              |
|  |  Topic Registry  |  topics.yaml -> defines what to monitor     |
|  +--------+---------+                                              |
|           |                                                        |
|           v                                                        |
|  +------------------+  +------------------+  +------------------+  |
|  |  YouTube Adapter |  |  Reddit Adapter  |  |   RSS Adapter    |  |
|  +--------+---------+  +--------+---------+  +--------+---------+  |
|           |                     |                     |            |
|           +----------+----------+----------+----------+            |
|                      |                                             |
|                      v                                             |
|  +-------------------------------------------------------+        |
|  |                   Content Store                        |        |
|  |  SQLite: metadata, scores, summaries, tags             |        |
|  |  Filesystem: raw content (transcripts, posts, articles)|        |
|  +-------------------------------------------------------+        |
|                      |                                             |
|                      v                                             |
|  +-------------------------------------------------------+        |
|  |               Analysis Pipeline (LLM)                  |        |
|  |  1. Relevance scoring (per topic description)          |        |
|  |  2. Summarization                                      |        |
|  |  3. Tag extraction                                     |        |
|  |  4. Cross-source dedup / linking                       |        |
|  +-------------------------------------------------------+        |
|                      |                                             |
|                      v                                             |
|  +-------------------------------------------------------+        |
|  |                  Digest Generator                       |        |
|  |  Per-topic digests (Markdown, JSON)                    |        |
|  |  Configurable: daily, weekly, on-demand                |        |
|  +-------------------------------------------------------+        |
|                                                                    |
+------------------------------------------------------------------+
```

## Config Format

```yaml
# config/topics.yaml

topics:
  ai-research:
    name: "AI Research & News"
    description: >
      Latest developments in artificial intelligence, machine learning,
      LLMs, foundational models, AI safety, and AI product launches.
      Focus on technical breakthroughs, new model releases, and industry shifts.
    relevance_threshold: 6     # 0-10, only items scoring above this make the digest
    schedule: "0 */4 * * *"    # Fetch every 4 hours
    digest: daily
    sources:
      youtube:
        - channel_id: "UCXgGY0wkgOzynnHvSEVmE3A"   # Lex Fridman
        - channel_id: "UCsJAl5x2J97OVJ4AO8QyPMA"   # Andrew Ng
      reddit:
        - subreddit: "MachineLearning"
          sort: "hot"
          limit: 25
        - subreddit: "LocalLLaMA"
          sort: "hot"
          limit: 25
      rss:
        - url: "https://arxiv.org/rss/cs.AI"
        - url: "https://news.ycombinator.com/rss"

  itad-market:
    name: "ITAD Market Intelligence"
    description: >
      IT Asset Disposition industry news: pricing trends for used servers,
      networking equipment, enterprise storage. E-waste regulation,
      data destruction standards, major ITAD company moves.
    relevance_threshold: 5
    schedule: "0 9 * * *"      # Daily at 9am
    digest: weekly
    sources:
      reddit:
        - subreddit: "homelab"
          sort: "hot"
          limit: 15
        - subreddit: "sysadmin"
          sort: "hot"
          limit: 15
      rss:
        - url: "https://www.e-scrap.com/feed/"

  politics-us:
    name: "US Politics"
    description: >
      Major US political developments, legislation, executive orders,
      Supreme Court decisions, and election-related news.
    relevance_threshold: 7
    schedule: "0 */6 * * *"
    digest: daily
    sources:
      reddit:
        - subreddit: "politics"
          sort: "hot"
          limit: 20
        - subreddit: "neutralpolitics"
          sort: "hot"
          limit: 15
      rss:
        - url: "https://feeds.npr.org/1001/rss.xml"
```

## Database Schema

```sql
CREATE TABLE content (
    id TEXT PRIMARY KEY,                -- platform unique ID (e.g., video_id, post_id)
    source_type TEXT NOT NULL,          -- adapter name: youtube, reddit, rss, etc.
    url TEXT,
    title TEXT,
    author TEXT,
    published_at DATETIME,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    content_path TEXT,                  -- path to raw content file
    summary TEXT,
    tags JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- A piece of content can appear in multiple topics with different relevance scores.
-- This is the authoritative mapping between content and topics.
CREATE TABLE content_topics (
    content_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    relevance_score REAL,              -- NULL = not yet scored
    PRIMARY KEY (content_id, topic),
    FOREIGN KEY (content_id) REFERENCES content(id)
);

CREATE TABLE digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    period_start DATETIME,
    period_end DATETIME,
    file_path TEXT,                     -- path to generated digest file
    item_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_source ON content(source_type, published_at);
CREATE INDEX idx_content_topics_topic ON content_topics(topic);
CREATE INDEX idx_content_topics_score ON content_topics(relevance_score);
```

**Note:** The original schema had a `topic` column on the `content` table and a `relevance_score` on both `content` and `content_topics`. This spec removes the redundant `topic` and `relevance_score` from `content` — the `content_topics` table is the authoritative source for topic membership and per-topic relevance scores. Content is topic-independent; its relationship to topics is managed entirely through `content_topics`.

## Adapter Interface Contract

Every source adapter implements this contract:

```python
# src/adapters/__init__.py

from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod

@dataclass
class FetchedItem:
    """Standardized content item returned by all adapters."""
    source_id: str           # Platform's unique ID
    source_type: str         # "youtube", "reddit", "rss", etc.
    url: str
    title: str
    author: str | None
    published_at: datetime
    content: str             # Full text content (transcript, post body, article)
    metadata: dict           # Adapter-specific extras (thumbnail, score, etc.)

class BaseAdapter(ABC):
    @abstractmethod
    def fetch(self, source_config: dict, since: datetime | None = None) -> list[FetchedItem]:
        """Fetch new content from the source since the given timestamp."""
        ...
```

Adding a new source (e.g., Bluesky, Mastodon, Substack) requires writing one file under `src/adapters/` that subclasses `BaseAdapter`.

## UI Compatibility

There is no UI in early phases — all interaction is CLI + config files. However, the architecture must support a future UI without restructuring:

- **Clean separation of concerns**: All business logic lives in importable modules (`config.py`, `db.py`, adapters, pipeline), not in CLI command handlers. The CLI is a thin layer that calls into these modules.
- **Queryable data layer**: `db.py` exposes functions for listing topics, querying content by topic/source/date, fetching stats, and reading digests. A future web server calls the same functions.
- **No CLI-only state**: All state lives in SQLite + filesystem, never in CLI session variables or stdout parsing.
- **Structured output**: Digest generation produces files on disk (Markdown/JSON), not just terminal output. The UI can serve these directly or render from the same data.

## Transcript Library Migration

The YouTube transcript tool currently lives at `~/.openclaw/skills/youtube-transcript/transcript.py` as a standalone CLI script. It should be migrated into this project as a proper importable library.

**Current state** (skill):
- Monolithic CLI script with argparse
- Called via subprocess from other tools
- Tightly coupled to CLI concerns (printing, file I/O)

**Target state** (library under `src/transcript/`):
- `extractor.py` — Core logic: `fetch_transcript(video_id, lang, proxy) -> list[dict]`
- `formatters.py` — Pure functions: `to_text()`, `to_json()`, `to_srt()`, `to_vtt()`
- `__init__.py` — Clean public API
- The YouTube adapter imports `from src.transcript import fetch_transcript` directly
- Optionally keep a thin CLI wrapper (`python -m src.transcript ...`) for standalone use

This eliminates the subprocess dependency and makes transcripts a first-class capability of the aggregator.

## CLI Command Reference

The CLI is minimal — most runs will be scheduled. No stats or topic-listing commands; that information lives in config files and the database directly.

```bash
# Fetch content for all topics
python -m src.main fetch

# Fetch content for a specific topic
python -m src.main fetch --topic ai-research

# Fetch with a start date (initial backfill)
python -m src.main fetch --since 2026-03-01

# Analyze unscored content (relevance + summarization)
python -m src.main analyze

# Analyze for a specific topic only
python -m src.main analyze --topic itad-market

# Generate digest
python -m src.main digest --topic ai-research

# Generate all pending digests
python -m src.main digest --all

# Full pipeline: fetch -> analyze -> digest
python -m src.main run
```
