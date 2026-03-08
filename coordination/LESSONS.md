# Lessons Learned

Shared lessons across all agents. After ANY correction from the user or a mistake caught during QA, add an entry here so the same mistake doesn't repeat.

## Format

```
### L-XXX: Short title
- Date:
- Agent:
- Context: What happened
- Lesson: The rule to follow going forward
```

---

### L-001: Git history does not replace structured handoff records
- Date: 2026-03-07
- Agent: architect
- Context: When adding git, replaced handoff history tables and completion log with "see git log" pointers. This lost structured fields (risks, approved interfaces, tests run) that commit messages don't capture.
- Lesson: Git tracks *code changes*. Coordination artifacts (handoff context, risks, validation notes) must stay in their structured files. Only remove tracking that git truly duplicates (e.g., "Last Updated" timestamps).

### L-002: Re-run the session start checklist after task completion
- Date: 2026-03-07
- Agent: dev
- Context: After finishing `P1-001`, I moved directly toward the next task without first re-reading the required coordination files for the new session boundary.
- Lesson: When a user explicitly marks a task done or asks for the next task, treat that as a fresh session boundary: re-run the RULES/TASK_BOARD/LESSONS/workspace checklist before claiming new work.

### L-003: Clean up temporary files regardless of short-circuit operators
- Date: 2026-03-07
- Agent: qa
- Context: Ran `python3 qa_smoke.py && rm qa_smoke.py` to test a script and clean it up. The script failed, the `&&` short-circuited, and the `rm` command never ran, leaving a stray file that blocked the dev agent's next git operations.
- Lesson: When writing temporary scratchpad files, clean them up explicitly via independent commands (e.g. `rm -f file.py`), rather than relying on conditional `&&` operators that might fail and strand files in the shared workspace.

### L-004: Convert found issues into actionable TASK_BOARD items
- Date: 2026-03-08
- Agent: qa
- Context: Logged an issue for a crash (ISSUE-001) in `AGENT_QA.md` and passed the related task, leaving the bug "open" but not assigned on the main board. The Dev agent only pulls work from the `TASK_BOARD.md` `todo` column, meaning the bug would never be picked up.
- Lesson: Never log "dead-end" issues in local workspaces. If an issue is found but the current task is still marked as `done`, you MUST explicitly create a new `BUG-XXX` row in the `TASK_BOARD.md` and assign it to the Dev in the `todo` state so the pipeline actually addresses it.
