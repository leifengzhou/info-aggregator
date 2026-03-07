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
| *(none yet)* | | | | |

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
