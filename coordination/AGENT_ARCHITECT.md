# Architect Workspace

## Role
- Own architecture, interfaces, schema direction, and cross-module contracts.
- Produce designs and interface specs before handing to dev for implementation.
- Review schema changes and module boundary shifts.

## Active Work
- Current Task ID: (none)
- Status: idle
- Started:

## Handoff to Dev — fetch_since Per-Topic Config Field
- Date: 2026-03-08
- Tasks: P1-010
- Priority order:
  1. **P1-010** — config.py + main.py + tests (medium effort)
  2. **P2-FUTURE-003** — log retention docs (architect-owned, defer)
- Constraints:
  - Precedence: CLI `--since` > topic's `fetch_since` > None (fetch all)
  - Do NOT import `parse_since` from main.py into config.py — avoid circular imports; add `_parse_fetch_since()` private helper in config.py
  - No DB schema changes
  - No signature change to `run_fetch()` — `since: datetime | None` remains the CLI override
- Spec:
  - `TopicConfig` gains `fetch_since: datetime | None = None`
  - `_parse_fetch_since(value, path)` in config.py handles ISO 8601 date and datetime strings
  - In `run_fetch()`, compute `effective_since = since if since is not None else topic_config.fetch_since` per topic
  - Tests: `TestFetchSince` in test_config.py (5 cases) + 3 since-precedence tests in test_main.py
- DEC-006 logged; see DECISIONS.md

## Decisions Pending
- None yet.

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

## Handoff to Dev
- Task ID: P1-005, P1-006
- Approved interfaces: `FetchedItem`, `BaseAdapter` (src/adapters/__init__.py), all db.py functions
- Constraints: Adapters must return `FetchedItem`; use `insert_content` + `link_content_topic` for storage; call `content_exists` before expensive fetches (dedup)
- Risks: No async support yet — fine for Phase 1 sequential fetching
- Date: 2026-03-07

## Handoff History

| Task ID | Date | Approved Interfaces | Constraints | Risks |
|---------|------|---------------------|-------------|-------|
| P1-005, P1-006 | 2026-03-07 | FetchedItem, BaseAdapter, db.py API | Adapters return FetchedItem; dedup via content_exists | No async yet |
