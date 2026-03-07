# Decisions (ADR-lite)

Use one entry per decision.

## Template
### DEC-XXX: Title
- Date:
- Status: proposed | accepted | superseded
- Context:
- Decision:
- Consequences:
- Owner:

---

### DEC-001: Coordination Workspace Structure
- Date: 2026-03-06
- Status: accepted
- Context: Multiple LLMs will collaborate with explicit role boundaries.
- Decision: Use a centralized `coordination/` folder containing project source-of-truth docs and per-agent logs.
- Consequences: Better traceability and lower merge conflict risk; requires disciplined updates.
- Owner: architect
