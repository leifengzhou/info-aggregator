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
