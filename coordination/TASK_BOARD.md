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
| P1-001 | Scaffold project structure + example config | senior-dev | done | - | Dirs created, example topics.yaml with 3 topics |
| P1-002 | Config loader with validation | senior-dev | done | P1-001 | Loads YAML, rejects invalid config with clear error |
| P1-003 | SQLite schema + db operations | architect | done | P1-001 | Tables created per TECH_SPEC; insert, dedup, query work |
| P1-004 | Adapter base interface contract | architect | done | P1-001 | FetchedItem dataclass + BaseAdapter ABC in src/adapters/ |
| P1-005 | Migrate transcript library | senior-dev | done | P1-004 | Importable fetch_transcript(); formatter tests pass |
| P1-006 | YouTube adapter | senior-dev | done | P1-003, P1-004, P1-005 | Discovers videos via RSS, fetches transcripts, stores to DB+filesystem, dedup works |
| P1-007 | CLI fetch command (--topic, --since) | senior-dev | done | P1-002, P1-003, P1-006 | `fetch` runs all topics; `--topic` filters; `--since` sets start date |
| P1-BUG-001 | Resilient 404 handling in YouTube Adapter | senior-dev | done | P1-007 | Adapter catches 404/HTTP errors from feed fetching, logs a warning, and returns empty list instead of crashing. |
| P1-008 | Logging setup | senior-dev | done | P1-001 | Structured logging (file + console); configurable log level; all adapters and DB ops log key events |
| P1-009 | QA smoke plan for Phase 1 | senior-qa | done | P1-007 | Smoke checks mapped to US-001 through US-004 acceptance criteria |
| P1-CLEANUP-001 | Remove stale files from workspace | senior-dev | in_review | - | `coordination/.venv/`, `test_p1.db*` removed; no untracked junk in repo |
| P1-CLEANUP-002 | Fix broken channel ID in default config | senior-dev | in_review | - | All channel_ids in `config/topics.yaml` return valid RSS feeds |
| P1-REF-001 | Simplify FetchSummary accumulation in main.py | senior-dev | in_review | - | FetchSummary no longer rebuilt from scratch each iteration; mutable counters or equivalent |
| P1-REF-002 | Remove redundant content_exists check in YouTube adapter | senior-dev | in_review | - | `ingest_youtube_source` uses `insert_content` return value for dedup instead of separate query; test_youtube_adapter still passes |
| P1-REF-003 | Add `__main__.py` for `src` package | senior-dev | in_review | - | `python -m src fetch` works as equivalent to `python -m src.main fetch` |
| P1-REF-004 | Add requirements-dev.txt for test dependencies | senior-dev | in_review | - | `pytest` and other dev-only deps listed separately from runtime deps |
| P1-BUG-002 | Timezone inconsistency in --since filtering | senior-dev | in_review | - | `published_at` values stored with consistent timezone handling; `--since` filter works correctly regardless of source timezone |

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

Filled by QA at sign-off (task moves to `done`). Git history tracks the code; this log tracks the context.

### Template
```
### P1-XXX: Title
- Completed: <date>
- Owner: <role>
- Commit: <short hash>
- Files touched: ...
- Tests run: ...
- Notes: ...
```

### P1-001: Scaffold project structure + example config
- Completed: 2026-03-07
- Owner: senior-dev
- Commit: 6e81958
- Files touched: .gitignore, README.md, requirements.txt, config/topics.yaml, src/, tests/, data/, coordination/
- Tests run: `python3 -m compileall src tests`, `python3 src/main.py`
- Notes: Acceptance criteria met. Directory scaffold is correct based on TECH_SPEC.md. Config has 3 topics.

### P1-002: Config loader with validation
- Completed: 2026-03-07
- Owner: senior-dev
- Commit: 0a8f902
- Files touched: src/config.py, tests/test_config.py, coordination/
- Tests run: `python3 -m unittest tests.test_config`, QA smoke tests
- Notes: Acceptance criteria met. YAML is parsed correctly, invalid configs are rejected with clear ConfigError messages.

### P1-004: Adapter base interface contract
- Completed: 2026-03-07
- Owner: architect
- Commit: d559cfb
- Files touched: src/adapters/__init__.py
- Tests run: `python3 -c "from src.adapters import FetchedItem, BaseAdapter"` (import verification)
- Notes: FetchedItem dataclass + BaseAdapter ABC transcribed directly from TECH_SPEC.md lines 221-245. DEC-003 logged.

### P1-005: Migrate transcript library
- Completed: 2026-03-07
- Owner: senior-dev
- Commit: 15f1b8b
- Files touched: src/transcript/__init__.py, src/transcript/extractor.py, src/transcript/formatters.py, tests/test_transcript.py, requirements.txt, coordination/
- Tests run: unit tests, `fetch_transcript` smoke test against actual video, validation of formatters using protocol-compliant objects.
- Notes: Acceptance criteria met. Reusable importable library extracted successfully, error handling is explicit.

### P1-003: SQLite schema + db operations
- Completed: 2026-03-07
- Owner: architect
- Commit: 1696142
- Files touched: src/db.py, tests/test_db.py
- Tests run: `python3 -m pytest tests/test_db.py -v` (9 passed)
- Notes: 3 tables, 3 indexes per TECH_SPEC schema. 6 functions (init_db, insert_content, link_content_topic, content_exists, get_content_by_topic, insert_digest). DEC-002 logged.

### P1-006: YouTube adapter
- Completed: 2026-03-07
- Owner: senior-dev
- Commit: 8130ec8
- Files touched: src/adapters/youtube.py, tests/test_youtube_adapter.py, coordination/
- Tests run: unit tests, manual live integration check with Google Developers channel to verify discovery, db insertion, and topic deduplication.
- Notes: Acceptance criteria met. Live fetching successfully pulls and parses feeds, creates db entries, links topics, and skips duplicate inserts on re-runs.

### P1-007: CLI fetch command (--topic, --since)
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: a6fc940
- Files touched: src/main.py, tests/test_main.py, coordination/
- Tests run: unit tests, CLI smoke test against default config with no args, with `--topic` filter, and with `--since` filter.
- Notes: Acceptance criteria met. CLI correctly routes the args, outputs processing summary, and ignores non-YouTube sources as intended for this phase. Logged an issue for the default config having a 404 channel ID.

### P1-BUG-001: Resilient 404 handling in YouTube Adapter
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: 6db14e5
- Files touched: src/adapters/youtube.py, tests/test_youtube_adapter.py, coordination/
- Tests run: unit tests, `python3 -m src.main fetch` via CLI against default config containing broken channel.
- Notes: Acceptance criteria met. Fetching no longer crashes on HTTP/URL/Parse errors from YouTube RSS feeds; instead, logs a warning and gracefully continues with zero items.

### P1-008: Logging setup
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: cd2339b
- Files touched: src/logging_setup.py, src/main.py, src/db.py, src/adapters/youtube.py, tests/
- Tests run: unit tests, CLI smoke test generating file logs.
- Notes: Acceptance criteria met. JSON line logs work correctly and record DB, ingest, and fetch boundaries.

### P1-009: QA smoke plan for Phase 1
- Completed: 2026-03-08
- Owner: senior-qa
- Commit: pending
- Files touched: coordination/AGENT_QA.md, coordination/TASK_BOARD.md
- Tests run: Execution of the mapped Phase 1 smoke test suite.
- Notes: Phase 1 smoke plan created and executed successfully. US-001 through US-004 acceptance criteria have been systematically validated. Phase 1 is verified complete.
