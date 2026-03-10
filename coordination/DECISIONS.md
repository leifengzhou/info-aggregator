# Decisions (ADR-lite)

Use one entry per decision.

## Template
### DEC-XXX: Title
- Date:
- Status: proposed | accepted | superseded
- Context:
- Decision:
- Consequences:
- Owner:

---

### DEC-001: Coordination Workspace Structure
- Date: 2026-03-06
- Status: accepted
- Context: Multiple LLMs will collaborate with explicit role boundaries.
- Decision: Use a centralized `coordination/` folder containing project source-of-truth docs and per-agent logs.
- Consequences: Better traceability and lower merge conflict risk; requires disciplined updates.
- Owner: architect

---

### DEC-002: Plain sqlite3 functional API for db.py
- Date: 2026-03-07
- Status: accepted
- Context: Need a storage layer for content and digests. Options: ORM (SQLAlchemy), class wrapper, or plain functions with sqlite3 stdlib.
- Decision: Use plain sqlite3 with a functional API — standalone functions that take a Connection parameter. No ORM, no class wrapper.
- Consequences: Minimal dependencies; easy to test with :memory: DBs; no migration tooling yet (acceptable for Phase 1). If schema grows complex, revisit.
- Owner: architect

---

### DEC-003: Adapter contract matches TECH_SPEC exactly
- Date: 2026-03-07
- Status: accepted
- Context: Defining the BaseAdapter ABC and FetchedItem dataclass for Phase 1.
- Decision: Transcribe the spec verbatim — no extensions (e.g., async, batch callbacks, error types) until a concrete adapter demands them.
- Consequences: Simple contract; easy for dev to implement first adapter (YouTube). Extensions deferred to when needed.
- Owner: architect

---

### DEC-004: fetch_transcript() returns TranscriptResult instead of list[TranscriptSegment]
- Date: 2026-03-08
- Status: accepted
- Context: No visibility into whether transcripts are manual or auto-generated. The upstream `youtube-transcript-api` provides `is_generated`, `language`, and `language_code` on the transcript object, but we were discarding this metadata.
- Decision: Introduce a `TranscriptResult` dataclass wrapping segments + metadata. `fetch_transcript()` returns `TranscriptResult` instead of a bare list. YouTube adapter surfaces `transcript_is_generated` and `transcript_language` in item metadata.
- Consequences: Breaking change to `fetch_transcript()` return type — all callers updated. Enables downstream consumers (digests, UI) to distinguish manual vs auto-generated transcripts.
- Owner: architect

---

### DEC-005: Accept playlist_url as an unofficial YouTube locator
- Date: 2026-03-08
- Status: accepted
- Context: Dev implemented playlist_url support alongside channel_id in the YouTube adapter, but it was not in the TECH_SPEC. playlist_url allows subscribing to a specific YouTube playlist rather than an entire channel.
- Decision: Accept as an official extension. Add tests. Update DECISIONS.md.
- Consequences: Slightly wider config surface than spec; no migration required.
- Owner: architect

---

### DEC-006: Config file over CLI for persistent settings
- Date: 2026-03-08
- Status: accepted
- Context: As settings accumulated on the CLI (--log-level, --since, --db, etc.), the fetch command became harder to use and settings were not persisted across runs.
- Decision: Persistent settings belong in config/topics.yaml under `settings:` or as per-topic fields. CLI flags are reserved for: bootstrap paths (--config), ad-hoc one-off overrides (--since, --topic), and automation/testing hooks (--db, --log-file). New settings default to config; a CLI flag is added only when an override use case exists.
- Consequences: Config becomes the authoritative source of run behavior; CLI stays minimal.
- Owner: architect

---

### DEC-007: Channel handle resolution via yt-dlp (per-run, no write-back)
- Date: 2026-03-08
- Status: accepted
- Context: Users know channel handles, not IDs. yt-dlp is already a dependency.
- Decision: Accept channel_handle as a config locator. At fetch time, if channel_id is absent, call yt-dlp to resolve the handle. No config mutation. Resolution is per-run (cheap — one subprocess call per handle, not per video).
- Consequences: Slight per-run overhead for unresolved handles (~1-2s). No new dependencies. If resolution fails, source is skipped with a WARNING.
- Owner: architect

---

### DEC-009: Reddit adapter design (Phase 2)
- Date: 2026-03-10
- Status: accepted
- Context: Phase 2 adds Reddit as the first non-YouTube source. Several design choices needed logging before dev starts implementation.
- Decision (5 sub-decisions):
  1. **No PRAW** — public JSON API (append `.json` to any subreddit URL) avoids auth dependency and OAuth registration. ~10 req/min unauthenticated is sufficient for personal use.
  2. **Top-level comments only in Phase 2** — nested reply expansion (`more` objects) deferred to Phase 3. Keeps the adapter simple; the common case (top N comments) is fully covered.
  3. **`source_id` prefix** — use `reddit_{post_id}` (e.g. `reddit_1abc23`) rather than the bare post ID to avoid theoretical collision with other source types that use numeric IDs.
  4. **`since` as a post-filter, not a URL param** — Reddit has no native date filter on its public JSON API. All sorts fetch up to `limit` posts, then filter by `created_utc >= since` in code. For `hot` sort with a tight `since` window this may return fewer than `limit` results — expected and documented behaviour.
  5. **`comment_limit` defaults to 0** — comment fetching is opt-in. Each post requires one extra HTTP request; defaulting to disabled keeps the common case fast and respects rate limits.
- Consequences: Config gains two new optional per-source fields (`comment_limit`, `min_score`) and one new global setting (`reddit_request_delay_seconds`). No schema changes. No interface changes to `FetchedItem` or `BaseAdapter`.
- Owner: architect

---

### DEC-008: Use yt-dlp Python API as the transcript backend
- Date: 2026-03-08
- Status: accepted
- Context: `youtube-transcript-api` fails silently on videos with auto-generated captions because YouTube's bot detection blocks its page-scraping approach. yt-dlp is already a project dependency (channel handle resolution), has active YouTube anti-bot maintenance, and naturally accesses the same subtitle data used by tools like NotebookLM and Tactiq. A 429 rate-limit error hit when testing yt-dlp directly — root cause is missing `curl-cffi` for browser impersonation.
- Decision:
  - Replace `youtube-transcript-api` with the `yt_dlp.YoutubeDL` Python API in `src/transcript/extractor.py`.
  - Do not use subprocess; use the Python library directly.
  - Prefer `json3` subtitle format (YouTube-native: `events[].segs[].utf8`); fall back to `vtt`.
  - Add `curl-cffi` as a runtime dependency — yt-dlp uses it automatically for Chrome impersonation when present.
  - Add retry-with-exponential-backoff on HTTP 429 inside the extractor (catch `yt_dlp.utils.DownloadError` with "429" in message).
  - Add optional `youtube_cookies_file` setting (path to cookies.txt) as a third-layer fallback for persistent 429s.
  - Public interface (`TranscriptResult`, `TranscriptSegment`, `fetch_transcript()` signature) is preserved — zero breaking changes to callers.
- Consequences:
  - `youtube-transcript-api` removed from requirements.txt; `curl-cffi>=0.7,<1.0` added.
  - Two new private seam functions (`_extract_info`, `_download_subtitle_content`) replace `_build_api`; extractor tests mock these instead.
  - Two new `Settings` fields: `youtube_transcript_max_retries: int = 3`, `youtube_cookies_file: str | None = None`.
  - Retry adds up to `max_retries × retry_delay` latency on persistent 429; acceptable since delay is configurable.
- Owner: architect
