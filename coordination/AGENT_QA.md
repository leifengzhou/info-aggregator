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
- Unit:
- Integration:
- CLI smoke:
- Regression:

## Issue Log

Track all findings here. Rejected tasks should reference an issue ID.

| Issue | Task | Severity | Status | Description |
|-------|------|----------|--------|-------------|
| ISSUE-001 | P1-007 | low | open | `config/topics.yaml` has a YouTube channel (`UCsJAl5x2J97OVJ4AO8QyPMA`) that 404s, causing `fetch` to crash if unhandled. Adapter needs resilient 404 handling. |

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
