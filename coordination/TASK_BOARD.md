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
| P1-CLEANUP-001 | Remove stale files from workspace | senior-dev | done | - | `coordination/.venv/`, `test_p1.db*` removed; no untracked junk in repo |
| P1-CLEANUP-002 | Fix broken channel ID in default config | senior-dev | done | - | All channel_ids in `config/topics.yaml` return valid RSS feeds |
| P1-REF-001 | Simplify FetchSummary accumulation in main.py | senior-dev | done | - | FetchSummary no longer rebuilt from scratch each iteration; mutable counters or equivalent |
| P1-REF-002 | Remove redundant content_exists check in YouTube adapter | senior-dev | done | - | `ingest_youtube_source` uses `insert_content` return value for dedup instead of separate query; test_youtube_adapter still passes |
| P1-REF-003 | Add `__main__.py` for `src` package | senior-dev | done | - | `python -m src fetch` works as equivalent to `python -m src.main fetch` |
| P1-REF-004 | Add requirements-dev.txt for test dependencies | senior-dev | done | - | `pytest` and other dev-only deps listed separately from runtime deps |
| P1-BUG-002 | Timezone inconsistency in --since filtering | senior-dev | done | - | `published_at` values stored with consistent timezone handling; `--since` filter works correctly regardless of source timezone |
| P1-REF-005 | Surface transcript generation type metadata | architect | done | - | `fetch_transcript()` returns `TranscriptResult` with `is_generated`, `language`, `language_code`; adapter surfaces in metadata; db.py log levels demoted |
| P1-REF-006 | Human-readable artifact file naming | architect | done | P1-REF-005 | Artifacts named `{channel}_{title}__{id}.json`; truncated to 200 chars; video ID guarantees uniqueness |
| P1-BUG-004 | Rate limiting for YouTube transcript fetches | senior-dev | done | - | Config `settings.youtube_transcript_delay_seconds` drives delay between transcript calls; default 1.0s; existing tests unaffected |

| P1-REF-007 | Wire `transcript_to_text()` into YouTube adapter | senior-dev | done | - | Adapter uses `transcript_to_text` from formatters; inline join removed; all tests pass |

| P1-CLEANUP-003 | Remove `content_exists` dead code | senior-dev | done | - | Function and its test removed; no remaining references; suite passes |

| P1-REF-008 | Tests + DECISIONS.md for `playlist_url` | senior-dev | done | - | `_build_feed_url` and `_extract_playlist_id` fully tested for both paths and error cases; DEC-005 logged |

| P2-FUTURE-001 | Non-ASCII slug handling in artifact filenames | senior-dev | todo | - | `_slugify` handles non-ASCII input gracefully (transliterate or fallback token); test coverage |
| P1-BUG-005 | Per-run log file naming | senior-dev | done | - | Each `fetch` run writes to `info-aggregator_{timestamp}.log`; `--log-file` override still works |
| P1-REF-009 | Add `run_id` to fetch log events | senior-dev | done | P1-BUG-005 | `fetch_run_started` and `fetch_run_completed` include `run_id`; value matches log filename timestamp |
| P1-BUG-006 | Warn on transcript language fallback | senior-dev | done | - | WARNING logged when `fetch_transcript()` falls back from requested language to alternate language |
| P2-FUTURE-002 | Sanitize source_config from log events | senior-dev | todo | - | Log only known-safe fields from source_config, not the full dict |
| P2-FUTURE-003 | Document log retention strategy | architect | todo | - | Add retention note and example rotation guidance to project docs |
| P2-FUTURE-004 | Analysis pipeline: filter transcript_available=False | senior-dev | todo | - | Analysis pipeline skips items where artifact metadata.transcript_available is false |
| P1-010 | fetch_since per-topic config field | senior-dev | todo | - | topic.fetch_since parsed from YAML and used as default since; CLI --since overrides for that run |

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
- Commit: 0c89859
- Files touched: coordination/AGENT_QA.md, coordination/TASK_BOARD.md
- Tests run: Execution of the mapped Phase 1 smoke test suite.
- Notes: Phase 1 smoke plan created and executed successfully. US-001 through US-004 acceptance criteria have been systematically validated. Phase 1 is verified complete.

### P1-CLEANUP-001: Remove stale files from workspace
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: coordination/
- Tests run: Verified working directory matches expectations.
- Notes: Cleanup complete.

### P1-CLEANUP-002: Fix broken channel ID in default config
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: config/topics.yaml
- Tests run: Validated default configs.
- Notes: Configured channel IDs verified.

### P1-REF-001: Simplify FetchSummary accumulation in main.py
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/main.py
- Tests run: Unit tests.
- Notes: Refactoring complete.

### P1-REF-002: Remove redundant content_exists check in YouTube adapter
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/adapters/youtube.py
- Tests run: Full unit test suite.
- Notes: Refactoring complete.

### P1-REF-003: Add `__main__.py` for `src` package
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/__main__.py
- Tests run: `python3 -m src fetch --help`
- Notes: CLI usage simplified.

### P1-REF-004: Add requirements-dev.txt for test dependencies
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: requirements-dev.txt
- Tests run: N/A
- Notes: Dependency split complete.

### P1-BUG-002: Timezone inconsistency in --since filtering
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/db.py, src/main.py
- Tests run: Full suite.
- Notes: Timezone filtering tested and working smoothly.

### P1-REF-005: Surface transcript generation type metadata
- Completed: 2026-03-08
- Owner: architect
- Commit: pending
- Files touched: src/transcript/extractor.py, src/adapters/youtube.py
- Tests run: `pytest tests/test_transcript.py tests/test_youtube_adapter.py`
- Notes: TranscriptResult now includes metadata, surfaced in YouTube adapter.

### P1-REF-006: Human-readable artifact file naming
- Completed: 2026-03-08
- Owner: architect
- Commit: pending
- Files touched: src/adapters/youtube.py
- Tests run: `pytest tests/test_youtube_adapter.py`
- Notes: Artifacts now named with channel, title, and ID. Truncation verified.

### P1-BUG-004: Rate limiting for YouTube transcript fetches
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/adapters/youtube.py, tests/test_youtube_adapter.py
- Tests run: `pytest tests/test_youtube_adapter.py`
- Notes: Throttling between transcript calls implemented and verified with mock sleep.

### P1-REF-007: Wire `transcript_to_text()` into YouTube adapter
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/adapters/youtube.py
- Tests run: `pytest tests/test_youtube_adapter.py`
- Notes: Refactored YouTube adapter to use shared transcript formatter.

### P1-CLEANUP-003: Remove `content_exists` dead code
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/db.py, tests/test_db.py
- Tests run: `pytest tests/test_db.py`
- Notes: Redundant content_exists removed after P1-REF-002 refactor.

### P1-REF-008: Tests + DECISIONS.md for `playlist_url`
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: tests/test_youtube_adapter.py, coordination/DECISIONS.md
- Tests run: `pytest tests/test_youtube_adapter.py`
- Notes: Covered YouTube feed locator logic for both channel_id and playlist_url.

### P1-BUG-005: Per-run log file naming
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/main.py, tests/test_main.py
- Tests run: `pytest tests/test_main.py`
- Notes: Automatic log file generation tested.

### P1-REF-009: Add `run_id` to fetch log events
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/main.py, tests/test_main.py
- Tests run: `pytest tests/test_main.py`
- Notes: run_id correctly propagated to fetch start/end events.

### P1-BUG-006: Warn on transcript language fallback
- Completed: 2026-03-08
- Owner: senior-dev
- Commit: pending
- Files touched: src/transcript/extractor.py, tests/test_transcript.py
- Tests run: `pytest tests/test_transcript.py`
- Notes: Warning logic correctly triggers on fallback.
