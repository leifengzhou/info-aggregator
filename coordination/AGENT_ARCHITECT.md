# Architect Workspace

## Role
- Own architecture, interfaces, schema direction, and cross-module contracts.
- Produce designs and interface specs before handing to dev for implementation.
- Review schema changes and module boundary shifts.

## Active Work
- Current Task ID: (none)
- Status: idle
- Started:

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
