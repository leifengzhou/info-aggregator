# Architect Workspace

## Role
- Own architecture, interfaces, schema direction, and cross-module contracts.
- Produce designs and interface specs before handing to dev for implementation.
- Review schema changes and module boundary shifts.

## Active Work
- Current Task ID: P2-001
- Status: done
- Started: 2026-03-10

## Handoff to Dev — Reddit Adapter (P2-002 through P2-005)
- Date: 2026-03-10
- Tasks: P2-002, P2-003, P2-004, P2-005
- Priority order:
  1. **P2-002** — config validation (quick; unblocks P2-003 and P2-004)
  2. **P2-003** — Reddit adapter implementation (main effort)
  3. **P2-004** — wire adapter into fetch pipeline (depends on P2-002, P2-003)
  4. **P2-005** — unit tests (can start alongside P2-003)
- Constraints:
  - Use `urllib.request.urlopen` for HTTP — no new dependencies (no `requests`, no `httpx`)
  - `User-Agent` header is mandatory: `python:info-aggregator:v0.1 (personal use)`
  - `source_id` must be prefixed: `reddit_{post_id}` — see DEC-009
  - `comment_limit` defaults to 0; comment fetching is opt-in
  - `since` filter applied in code against `created_utc` — no native API date param
  - 429 handling: respect `Retry-After` if present, otherwise 60s back-off, retry once
  - Subreddit errors (404/403/network) → WARNING + return `[]` (never crash the run)
  - Comment fetch failure for one post → WARNING + skip that post's comments (don't abort)
  - Artifact naming: `reddit_{subreddit}_{slug(title)}__{post_id}.json`, 200 char cap
  - All behaviour specified in TECH_SPEC.md "Reddit Adapter" section — treat it as the implementation spec
- Files to create/modify:
  - `src/adapters/reddit.py` — new file
  - `src/config.py` — extend `_validate_source_entry` (reddit branch) + `_parse_settings`
  - `src/main.py` — wire `ingest_reddit_source`; extend `FetchSummary`
  - `tests/test_reddit_adapter.py` — new file, all HTTP mocked
- DEC-009 logged; see DECISIONS.md

## Decisions Pending
- None.

## Approved Contracts

Track ratified interfaces here so dev and QA have a stable reference.

| Contract | Location | Decision | Notes |
|----------|----------|----------|-------|
| FetchedItem + BaseAdapter | `src/adapters/__init__.py` | DEC-003 | Exact TECH_SPEC transcription |
| db.py functional API | `src/db.py` | DEC-002 | Plain sqlite3, no ORM |

## Review Checklist
- Adapter interface compatibility
- Schema implications and migration safety
- CLI/API consistency
- Failure modes and retry strategy

## Handoff History

| Task ID | Date | Approved Interfaces | Constraints | Risks |
|---------|------|---------------------|-------------|-------|
| P1-005, P1-006 | 2026-03-07 | FetchedItem, BaseAdapter, db.py API | Adapters return FetchedItem; dedup via insert_content | No async yet |
| P1-010, P1-011 | 2026-03-08 | channel_handle in config; resolve_channel_handle() | No config write-back; per-run resolution; injectable resolver | yt-dlp subprocess per handle |
| P2-001 | 2026-03-10 | Reddit adapter spec in TECH_SPEC.md | DEC-009; urllib only; source_id prefix; comment_limit=0 default | — |
