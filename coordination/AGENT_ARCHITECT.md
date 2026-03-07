# Architect Workspace

## Role
- Own architecture, interfaces, schema direction, and cross-module contracts.
- Produce designs and interface specs before handing to dev for implementation.
- Review schema changes and module boundary shifts.

## Active Work
- Current Task ID: P1-003, P1-004
- Status: in_progress
- Started: 2026-03-07

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
- Task ID:
- Approved interfaces:
- Constraints:
- Risks:
- Date:

## Handoff History

| Task ID | Date | Approved Interfaces | Constraints | Risks |
|---------|------|---------------------|-------------|-------|
| *(none yet)* | | | | |
