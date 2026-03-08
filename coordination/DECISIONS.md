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

---

### DEC-004: fetch_transcript() returns TranscriptResult instead of list[TranscriptSegment]
- Date: 2026-03-08
- Status: accepted
- Context: No visibility into whether transcripts are manual or auto-generated. The upstream `youtube-transcript-api` provides `is_generated`, `language`, and `language_code` on the transcript object, but we were discarding this metadata.
- Decision: Introduce a `TranscriptResult` dataclass wrapping segments + metadata. `fetch_transcript()` returns `TranscriptResult` instead of a bare list. YouTube adapter surfaces `transcript_is_generated` and `transcript_language` in item metadata.
- Consequences: Breaking change to `fetch_transcript()` return type — all callers updated. Enables downstream consumers (digests, UI) to distinguish manual vs auto-generated transcripts.
- Owner: architect

---

### DEC-005: Accept playlist_url as an unofficial YouTube locator
- Date: 2026-03-08
- Status: accepted
- Context: Dev implemented playlist_url support alongside channel_id in the YouTube adapter, but it was not in the TECH_SPEC. playlist_url allows subscribing to a specific YouTube playlist rather than an entire channel.
- Decision: Accept as an official extension. Add tests. Update DECISIONS.md.
- Consequences: Slightly wider config surface than spec; no migration required.
- Owner: architect

---

### DEC-006: Config file over CLI for persistent settings
- Date: 2026-03-08
- Status: accepted
- Context: As settings accumulated on the CLI (--log-level, --since, --db, etc.), the fetch command became harder to use and settings were not persisted across runs.
- Decision: Persistent settings belong in config/topics.yaml under `settings:` or as per-topic fields. CLI flags are reserved for: bootstrap paths (--config), ad-hoc one-off overrides (--since, --topic), and automation/testing hooks (--db, --log-file). New settings default to config; a CLI flag is added only when an override use case exists.
- Consequences: Config becomes the authoritative source of run behavior; CLI stays minimal.
- Owner: architect

---

### DEC-007: Channel handle resolution via yt-dlp (per-run, no write-back)
- Date: 2026-03-08
- Status: accepted
- Context: Users know channel handles, not IDs. yt-dlp is already a dependency.
- Decision: Accept channel_handle as a config locator. At fetch time, if channel_id is absent, call yt-dlp to resolve the handle. No config mutation. Resolution is per-run (cheap — one subprocess call per handle, not per video).
- Consequences: Slight per-run overhead for unresolved handles (~1-2s). No new dependencies. If resolution fails, source is skipped with a WARNING.
- Owner: architect
