# Senior QA Workspace

## Role
- Validate behavior against acceptance criteria and guard against regressions.
- Maintain the issue log as the team's bug backlog.
- Sign off on tasks or reject them back to dev with clear repro steps.

## Active Validation
- Task ID:
- Status:
- Started:

## Test Plan
**Phase 1 Smoke Plan (US-001 through US-004)**

**US-001: Configure topics and sources**
- [x] Setup: verify `config/topics.yaml` has multiple topics and valid YAML structure.
- [x] Action: Run `python3 -m src.main fetch` with bad config; expect clear rejection.
- [x] Action: Run with valid config; expect system to load topics correctly.

**US-002 & US-004: Fetch YouTube transcripts & Persistence**
- [x] Action: Run `python3 -m src.main fetch --db test_p1.db --content-root test_p1_data`
- [x] Check: Verify SQLite `test_p1.db` has entries in `content` and `content_topics` tables.
- [x] Check: Verify raw JSON files are created in `test_p1_data/youtube/` containing metadata and transcripts.
- [x] Check: Run fetch again and verify `Items inserted` is 0 (deduplication works).

**US-003: Fetch by topic or date range**
- [x] Action: Run `python3 -m src.main fetch --topic ai-research --db test_p1.db --content-root test_p1_data`
- [x] Check: System only processes the single requested topic.
- [x] Action: Run `python3 -m src.main fetch --since 2026-03-01T00:00:00 --db test_p1.db --content-root test_p1_data`
- [x] Check: System passes the since date correctly to adapters (fewer/different items discovered depending on date).

## Issue Log

Track all findings here. Rejected tasks should reference an issue ID.

| Issue | Task | Severity | Status | Description |
|-------|------|----------|--------|-------------|
| ISSUE-001 | P1-007, P1-BUG-001 | low | fixed | `config/topics.yaml` has a YouTube channel (`UCsJAl5x2J97OVJ4AO8QyPMA`) that 404s, causing `fetch` to crash if unhandled. Adapter needs resilient 404 handling. |
| ISSUE-002 | P1-012 | high | fixed | `fetch_transcript` crashes with unhandled `urllib.error.HTTPError: HTTP Error 429` when downloading subtitle payloads via `urllib.request.urlopen`. The retry logic only wraps the `yt-dlp` metadata extraction, not the raw text download. |

**Severity**: critical | high | medium | low
**Status**: open | fixed | wont-fix


## Findings Detail

Use this section for detailed repro steps when an issue needs more context.

### Template
```
### ISSUE-XXX
- Task ID:
- Severity:
- Repro steps:
- Expected:
- Actual:
- Affected files:
```

### ISSUE-002
- Task ID: P1-012
- Severity: high
- Repro steps: Run `python -m src fetch` against a channel with many videos (e.g. `@mkbhd`). Wait for multiple transcript payloads to be fetched sequentially.
- Expected: Rate limits (429) from YouTube on the raw subtitle text URLs are caught, retried (using the configurable max_retries), and eventually gracefully handled if exhausted.
- Actual: The script crashes with an unhandled `urllib.error.HTTPError: HTTP Error 429: Too Many Requests` traceback emanating from `_download_subtitle_content` in `src/transcript/extractor.py`.
- Affected files: `src/transcript/extractor.py`

### ISSUE-001
- Task ID: P1-007
- Severity: low
- Repro steps: Run `python3 -m src.main fetch` using the default `config/topics.yaml` provided in scaffolding.
- Expected: Adapter skips the missing channel or logs a warning instead of crashing the whole topic fetch.
- Actual: `urllib.error.HTTPError: HTTP Error 404: Not Found` is thrown unhandled in `_fetch_feed`, halting execution.
- Affected files: `src/adapters/youtube.py`, `config/topics.yaml`
- Resolution: Fixed in P1-BUG-001 via try/except blocks around feed fetching in YouTube adapter.

## Sign-off
- Task ID:
- Result:
- Residual risks:
- Date:

## Sign-off History

| Task ID | Date | Result | Residual Risks | Notes |
|---------|------|--------|----------------|-------|
| P1-001 | 2026-03-07 | pass | Modules are placeholders | Dirs created, topics.yaml with 3 topics verified |
| P1-002 | 2026-03-07 | pass | Cron validation is structural only | YAML configs validated properly and bad ones rejected |
| P1-005 | 2026-03-07 | pass | Network dependencies, `youtube-transcript-api` required at runtime | Tested extraction + formatting over real YouTube transcripts |
| P1-006 | 2026-03-07 | pass | Network dependent, artifacts are full JSON payloads | Validated live fetching, db insertion, and topic deduplication via script |
| P1-007 | 2026-03-08 | pass-with-risk | Adapter crashes on 404s (ISSUE-001) | CLI itself meets acceptance criteria (routes arguments and outputs stats correctly). |
| P1-BUG-001 | 2026-03-08 | pass | Transcript fetch errors not handled here | Validated that 404s gracefully degrade to 0 items via CLI |
| P1-008 | 2026-03-08 | pass | JSON lines directly to stderr can be noisy | Validated structured logging configuration and db/adapter records |
| P1-009 | 2026-03-08 | pass | None | Formally verified all Phase 1 User Stories via smoke script |
| P1-CLEANUP-001 | 2026-03-08 | pass | None | Verified stale files are gone |
| P1-CLEANUP-002 | 2026-03-08 | pass | None | Validated fix of broken channel ID in config |
| P1-REF-001 | 2026-03-08 | pass | None | Verified main refactoring via tests |
| P1-REF-002 | 2026-03-08 | pass | None | Verified youtube adapter refactoring via tests |
| P1-REF-003 | 2026-03-08 | pass | None | Verified `python3 -m src fetch --help` behaves equivalently to `src.main` |
| P1-REF-004 | 2026-03-08 | pass | None | Verified explicit dev dependencies |
| P1-BUG-002 | 2026-03-08 | pass | None | Verified timezone-aware logic via automated suite |
| P1-REF-005 | 2026-03-08 | pass | None | Transcript metadata (language, is_generated) correctly surfaced and tested |
| P1-REF-006 | 2026-03-08 | pass | Artifact filenames can be very long | Human-readable filenames implemented with slugification and truncation |
| P1-BUG-004 | 2026-03-08 | pass | Network dependent | Rate limiting between transcript fetches implemented and tested via mocks |
| P1-REF-007 | 2026-03-08 | pass | None | Adapter now uses transcript_to_text() formatter; verified multiline content tests |
| P1-CLEANUP-003 | 2026-03-08 | pass | None | Removed content_exists() from db.py and its test from test_db.py |
| P1-REF-008 | 2026-03-08 | pass | None | Comprehensive tests for playlist_url support and feed URL building; DEC-005 logged |
| P1-BUG-005 | 2026-03-08 | pass | Concurrent same-second runs may collide | Verified per-run auto log files and explicit override |
| P1-REF-009 | 2026-03-08 | pass | None | run_id correctly matches timestamp and is included in run events |
| P1-BUG-006 | 2026-03-08 | pass | None | Fallback warning logged during transcript fetch |
| P1-010 | 2026-03-08 | pass | None | topic.fetch_since parsed and applied as default; CLI --since overrides properly |
| P1-011 | 2026-03-08 | pass | yt-dlp must be installed in PATH | Verified @handle resolution and appropriate warning when invalid |
| P1-012 | 2026-03-08 | pass | External API limits apply | Verified via test suite that urlopen 429 errors are caught, retried, and gracefully handled (ISSUE-002 resolved). |
| P1-REF-010 | 2026-03-09 | pass | None | Human-friendly console output, JSON file logs, and latest.log pointer verified via manual runs and automated tests. |
| P2-002..P2-005 | 2026-03-10 | pass | API rate limits | Verified Reddit fetching, config parsing, 404 handling, and stats logging via automated tests and live run against /r/Python. |


