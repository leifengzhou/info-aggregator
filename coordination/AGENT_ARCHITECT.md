# Architect Workspace

## Role
- Own architecture, interfaces, schema direction, and cross-module contracts.
- Produce designs and interface specs before handing to dev for implementation.
- Review schema changes and module boundary shifts.

## Active Work
- Current Task ID: (none)
- Status: idle
- Started:

## Handoff to Dev — Channel Handle Auto-Resolution (P1-011)
- Date: 2026-03-08
- Tasks: P1-010, P1-011
- Priority order:
  1. **P1-011** — config.py + youtube.py + tests (medium effort)
  2. **P1-010** — config.py + main.py + tests (medium effort)
  3. **P2-FUTURE-003** — log retention docs (architect-owned, defer)
- Constraints (P1-011):
  - No config write-back; resolution is per-run only
  - `channel_id` takes priority over `channel_handle` if both present (existing behaviour preserved)
  - `_build_feed_url` stays pure — no changes needed there
  - Resolution failure → WARNING + return [] (source skipped, run continues)
  - Injectable `channel_id_resolver` for testability
- Spec (P1-011):
  - `src/config.py`: extend `_validate_source_entry` to accept `channel_handle` as a third valid locator
  - `src/adapters/youtube.py`: add `resolve_channel_handle(handle)` + inject into `__init__` + pre-step in `fetch()`
  - Tests: 4 new cases in test_youtube_adapter.py + 2 new cases in test_config.py
- DEC-007 logged; see DECISIONS.md

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
