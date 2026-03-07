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

---

### DEC-002: Plain sqlite3 functional API for db.py
- Date: 2026-03-07
- Status: accepted
- Context: Need a storage layer for content and digests. Options: ORM (SQLAlchemy), class wrapper, or plain functions with sqlite3 stdlib.
- Decision: Use plain sqlite3 with a functional API — standalone functions that take a Connection parameter. No ORM, no class wrapper.
- Consequences: Minimal dependencies; easy to test with :memory: DBs; no migration tooling yet (acceptable for Phase 1). If schema grows complex, revisit.
- Owner: architect

---

### DEC-003: Adapter contract matches TECH_SPEC exactly
- Date: 2026-03-07
- Status: accepted
- Context: Defining the BaseAdapter ABC and FetchedItem dataclass for Phase 1.
- Decision: Transcribe the spec verbatim — no extensions (e.g., async, batch callbacks, error types) until a concrete adapter demands them.
- Consequences: Simple contract; easy for dev to implement first adapter (YouTube). Extensions deferred to when needed.
- Owner: architect
