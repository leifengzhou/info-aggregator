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
| FUTURE-001 | Non-ASCII slug handling in artifact filenames | senior-dev | todo | - | `_slugify` handles non-ASCII input gracefully (transliterate or fallback token); test coverage |
| P1-BUG-005 | Per-run log file naming | senior-dev | done | - | Each `fetch` run writes to `info-aggregator_{timestamp}.log`; `--log-file` override still works |
| P1-REF-009 | Add `run_id` to fetch log events | senior-dev | done | P1-BUG-005 | `fetch_run_started` and `fetch_run_completed` include `run_id`; value matches log filename timestamp |
| P1-REF-010 | Human-friendly console logging + run audit envelope | senior-dev | done | P1-REF-009 | Console uses readable format while file remains JSON; default logs are per-run files with latest pointer; fetch start/end logs include effective config params and runtime duration |
| P1-BUG-006 | Warn on transcript language fallback | senior-dev | done | - | WARNING logged when `fetch_transcript()` falls back from requested language to alternate language |
| FUTURE-002 | Sanitize source_config from log events | senior-dev | todo | - | Log only known-safe fields from source_config, not the full dict |
| FUTURE-003 | Document log retention strategy | architect | todo | - | Add retention note and example rotation guidance to project docs |
| FUTURE-004 | Analysis pipeline: filter transcript_available=False | senior-dev | todo | - | Analysis pipeline skips items where artifact metadata.transcript_available is false |
| P1-010 | fetch_since per-topic config field | senior-dev | done | - | topic.fetch_since parsed from YAML and used as default since; CLI --since overrides for that run |
| P1-011 | Channel handle auto-resolution | senior-dev | done | - | channel_handle accepted in config YAML; resolved to channel_id via yt-dlp at fetch time; if resolution fails, source is skipped with WARNING |
| P1-012 | Switch transcript backend to yt-dlp | senior-dev | done | P1-011 | `youtube-transcript-api` removed; `yt_dlp.YoutubeDL` Python API used directly; `curl-cffi` added to requirements.txt; retry on 429 (configurable); `youtube_cookies_file` and `youtube_transcript_max_retries` settings added; all existing tests pass with updated mocks |

| P2-001 | PRD + TECH_SPEC updates for Reddit adapter | architect | done | — | US-R01–R05 in PRD.md; Reddit adapter section in TECH_SPEC.md; DEC-009 in DECISIONS.md |
| P2-002 | Config validation for Reddit source fields | senior-dev | todo | P2-001 | `comment_limit` (int ≥ 0, default 0) and `min_score` (int ≥ 0, optional) validated in `_validate_source_entry`; invalid `sort` rejected; `reddit_request_delay_seconds` validated in `_parse_settings`; test_config.py cases added |
| P2-003 | Reddit adapter implementation | senior-dev | todo | P2-001 | `src/adapters/reddit.py` — `RedditAdapter(BaseAdapter)` + `ingest_reddit_source()`; fetches posts via public JSON API; filters by `since`, `min_score`; optionally fetches top-level comments; returns `FetchedItem` per plan spec; artifacts written to `data/content/reddit/` |
| P2-004 | Wire Reddit adapter into fetch pipeline | senior-dev | todo | P2-002, P2-003 | `main.py` handles `source_type == "reddit"` using `ingest_reddit_source`; `FetchSummary` extended with `reddit_sources_processed`; `_print_fetch_summary` updated; `skipped_sources` no longer incremented for reddit |
| P2-005 | Reddit adapter unit tests | senior-dev | todo | P2-003 | `tests/test_reddit_adapter.py` — all HTTP mocked; covers: post fetch, since-filter, min_score filter, comment fetch, 429 retry, 404 graceful skip, dedup across runs, link-post content format |

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

See `ARCHIVE.md` for completion history.
