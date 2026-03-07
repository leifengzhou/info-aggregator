# Task Board

## Status Legend
- `todo`
- `in_progress`
- `blocked`
- `in_review`
- `rejected`
- `done`

## Task Table
| ID | Title | Owner | Status | Depends On | Acceptance Criteria |
|---|---|---|---|---|---|
| P1-001 | Scaffold project structure + example config | senior-dev | todo | - | Dirs created, example topics.yaml with 3 topics |
| P1-002 | Config loader with validation | senior-dev | todo | P1-001 | Loads YAML, rejects invalid config with clear error |
| P1-003 | SQLite schema + db operations | architect | todo | P1-001 | Tables created per TECH_SPEC; insert, dedup, query work |
| P1-004 | Adapter base interface contract | architect | todo | P1-001 | FetchedItem dataclass + BaseAdapter ABC in src/adapters/ |
| P1-005 | Migrate transcript library | senior-dev | todo | P1-004 | Importable fetch_transcript(); formatter tests pass |
| P1-006 | YouTube adapter | senior-dev | todo | P1-003, P1-004, P1-005 | Discovers videos via RSS, fetches transcripts, stores to DB+filesystem, dedup works |
| P1-007 | CLI fetch command (--topic, --since) | senior-dev | todo | P1-002, P1-003, P1-006 | `fetch` runs all topics; `--topic` filters; `--since` sets start date |
| P1-008 | Logging setup | senior-dev | todo | P1-001 | Structured logging (file + console); configurable log level; all adapters and DB ops log key events |
| P1-009 | QA smoke plan for Phase 1 | senior-qa | todo | P1-007 | Smoke checks mapped to US-001 through US-004 acceptance criteria |

## User Story -> Task Mapping
- **US-001** (config): P1-001, P1-002
- **US-002** (YouTube transcripts): P1-004, P1-005, P1-006
- **US-003** (fetch by topic/date): P1-007
- **US-004** (persistence): P1-003, P1-006
- **Cross-cutting**: P1-008 (logging)

## Rules
- Update status and owner before work starts.
- One owner per task at a time. If a task needs multiple roles (e.g. architect designs, dev implements), the current phase owner holds it.
- QA validates only against listed acceptance criteria.

## Completion Log

Completed tasks are recorded by git history. Use `git log --oneline --grep="P1-"` to review.
