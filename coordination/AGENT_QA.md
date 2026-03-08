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
