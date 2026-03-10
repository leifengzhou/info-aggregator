# Info Aggregator - Product Requirements Document

## Vision

A personal, self-hosted information aggregator that monitors configurable sources across any domain — AI news, market trends, politics, hobbies, industry verticals — and delivers curated, summarized digests. The user defines **topics**, each with its own set of **sources** (YouTube channels, subreddits, RSS feeds, etc.), and the system fetches, deduplicates, analyzes, and summarizes content on a schedule.

This is not another RSS reader. The LLM layer is the differentiator: it scores relevance against your stated interests, cross-references across sources, identifies emerging themes, and produces digestible summaries so you get signal without the noise.

## Core Concepts

### Topics

A **topic** is a named area of interest with its own configuration:

- **Name**: e.g., "AI Research", "Texas Politics", "ITAD Market"
- **Description**: Natural language description of what you care about (used as context for relevance scoring)
- **Sources**: List of source configurations (channels, subreddits, feeds)
- **Schedule**: How often to fetch (hourly, daily, custom cron)
- **Digest frequency**: How often to generate summaries (daily, weekly, on-demand)
- **Relevance threshold**: Minimum score (0-10) for content to appear in digests

### Sources (Adapters)

Each source type is a modular adapter with a consistent interface:

| Source Type | Input | Content Pulled |
|-------------|-------|----------------|
| YouTube | Channel IDs, playlist URLs | Video metadata + transcripts |
| Reddit | Subreddit names | Posts + top comments |
| RSS | Feed URLs | Articles (title, body, links) |
| Hacker News | Front page / specific tags | Stories + comment threads |
| X | User handles (if API available) | Posts |

Adding a new source type is a matter of writing one adapter module.

### Analysis Pipeline

For each piece of fetched content:

1. **Dedup** — Skip if already collected
2. **Relevance scoring** — Score content against the topic's description (0-10)
3. **Summarize** — Generate a concise summary for items above the relevance threshold
4. **Tag extraction** — Auto-tag with categories, entities, themes
5. **Cross-reference** — Flag when multiple sources cover the same story

## User Stories — Phase 1: Foundation

### US-001: Configure topics and sources

> As a user, I can define topics with named sources in a YAML config file so the system knows what content to monitor and where to find it.

**Acceptance Criteria:**
- Each topic has a name, description, relevance threshold, schedule, and digest frequency
- Each topic has one or more source types (YouTube, Reddit, RSS) with source-specific config
- Invalid config is rejected with a clear error message on startup
- A default example config with 3 topics is provided

### US-002: Fetch YouTube transcripts

> As a user, I can fetch transcripts from recent videos on configured YouTube channels so I have raw content to analyze.

**Acceptance Criteria:**
- Discovers recent videos from a YouTube channel without requiring an API key
- Extracts video transcript when available
- Stores video metadata (title, author, publish date, URL) and transcript text
- Skips videos already fetched (deduplication)
- Gracefully handles missing transcripts (stores metadata without transcript)

### US-003: Fetch content by topic or date range

> As a user, I can fetch content for a specific topic or since a specific date so I can do targeted or backfill fetches.

**Acceptance Criteria:**
- A topic filter limits fetching to a single topic
- A date filter sets a start date for fetching
- Without filters, fetches all topics

### US-004: Content persists across runs

> As a user, fetched content is stored durably so I don't lose data between sessions and duplicates are prevented.

**Acceptance Criteria:**
- Content metadata stored in a local database
- Raw content (transcripts, text) stored as files on disk
- Re-running fetch does not create duplicate entries
- Same content appearing in multiple topics is tracked per-topic

## Interface Philosophy

In early phases, the system has **no UI**. All configuration lives in YAML files, all output is Markdown on disk, and all interaction happens through the CLI. This keeps the scope tight and the feedback loop fast.

However, the system must be **UI-compatible from day one**. Data models, storage, and APIs should be structured so that a frontend can be layered on top without restructuring the backend. When a UI is introduced (Phase 4), it should be able to read topics, browse collected content, view digests, and trigger fetches — all by consuming the same data and interfaces the CLI uses.

## Phases Overview

### Phase 1: Foundation (detailed above)
- Topic and source configuration via YAML files
- YouTube adapter with transcript extraction
- Content storage and deduplication
- CLI for fetching (all topics, by topic, by date range)

### Phase 2: More Sources + Analysis
- Reddit adapter (public subreddits, no auth required)
- RSS/Atom feed adapter
- LLM-powered relevance scoring and summarization
- Per-topic digest generation (Markdown output)

## User Stories — Phase 2: Reddit Adapter

### US-R01: Fetch posts from public subreddits

> As a user, I can configure subreddits in topics.yaml and fetch posts without logging in or registering an app.

**Acceptance Criteria:**
- `subreddit` field in source config is the only required field
- Fetches post title + body text (selftext for self-posts; URL for link posts)
- Stores post metadata (author, score, upvote_ratio, flair, num_comments)
- Deduplicates by Reddit post ID across runs
- Gracefully skips subreddit on network/API error (logs WARNING, continues)

### US-R02: Control sort order and fetch size

> As a user, I can sort subreddit results by hotness or recency and control how many posts to fetch.

**Acceptance Criteria:**
- `sort` field accepts: `hot`, `new` (default: `new`)
- `limit` field caps posts fetched (1–100, default: 25)
- Invalid sort value rejected at config load with clear error

### US-R03: Fetch posts since a given date

> As a user, fetched Reddit posts are filtered by publish date using the same `fetch_since` / `--since` mechanism as YouTube.

**Acceptance Criteria:**
- Topic-level `fetch_since` and CLI `--since` both filter by `created_utc`
- Posts older than `since` are skipped, not stored
- `new` sort is recommended for since-date fetches (documented); other sorts apply `since` as a post-filter
- Without `since`, fetches up to `limit` posts regardless of date

### US-R04: Optionally capture top-level comments

> As a user, I can configure how many top-level comments to capture per post.

**Acceptance Criteria:**
- `comment_limit: N` per source (default: 0 — no comment fetching)
- When > 0, fetches top N comments by score from each post (1 extra HTTP request per post)
- Comments appended to post content as formatted text; raw comment data stored in artifact metadata
- Top-level only — nested replies excluded in Phase 2
- A configurable delay (`settings.reddit_request_delay_seconds`) applies between per-post comment requests

### US-R05: Filter low-quality posts by score

> As a user, I can set a minimum upvote score to skip low-engagement posts.

**Acceptance Criteria:**
- `min_score: N` per source (optional, default: no filter)
- Posts with `score < min_score` are skipped before storage
- Skipped posts are logged at DEBUG level

### Phase 3: Polish + Scheduling
- Hacker News adapter
- Cross-source deduplication (detect same story from multiple sources)
- Automated scheduling (cron or in-process scheduler)
- Error handling and retry logic for flaky sources

### Phase 4: UI + Notifications
- Web dashboard for browsing topics, content, and digests
- Trigger fetches and view stats from the UI
- Push notifications (Telegram, email, or messaging integration)

### Phase 5: Optional Enhancements
- X.com adapter (if API becomes accessible)
- Semantic search over historical content
- Topic auto-suggestion based on reading patterns

## Verification Scenarios

1. **Setup** — Configure a test topic with 1 YouTube channel. Verify the system accepts the config and displays it correctly.
2. **First fetch** — Fetch content since a recent date. Verify items appear in storage (both database and filesystem).
3. **Analysis** — Run analysis on unscored content. Verify relevance scores and summaries are generated.
4. **Digest** — Generate a digest for the topic. Verify a readable summary is produced, grouped by topic.
5. **Deduplication** — Re-run fetch. Verify no duplicate entries are created.
6. **Multi-topic overlap** — Add a second topic with overlapping sources. Verify the same content can belong to multiple topics with different relevance scores.

## Design Rationale

**Why SQLite?** Single-user, self-hosted, no external dependencies. Content volume is modest (hundreds of items/day, not millions). SQLite handles this with zero ops burden.

**Why per-topic relevance scoring?** The same Reddit post about "GPU prices dropping" is highly relevant to an ITAD topic but irrelevant to a politics topic. Scoring is always relative to the topic's description.

**Why migrate the transcript tool?** Subprocess calls are fragile, hard to test, and add latency. An importable library is faster, testable, and reusable.

**Why not async?** Fetching is I/O-bound but volume is low. Sequential fetching with rate limiting is simpler and sufficient. Can add async later if source count grows significantly.
