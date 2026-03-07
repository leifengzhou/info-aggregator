# Project Source of Truth

## Project
- Name: `info-aggregator`
- PRD: `/home/neo/projects/info-aggregator/PRD.md`
- Current Phase: `Phase 1 - Foundation`

See `RULES.md` for workflow, guardrails, and coordination protocols.

## Objectives
- Build a self-hosted information aggregator with modular source adapters.
- Fetch, deduplicate, score, summarize, tag, and digest content per topic.
- Keep architecture simple, testable, and incrementally extensible.

## Non-Negotiables
- Python 3.11+
- SQLite for metadata and scores
- Local filesystem for raw content and digest output
- Adapter interface contract in `src/adapters/__init__.py`
- Per-topic relevance scoring semantics

## Definition of Done (Global)
- Feature behavior matches PRD acceptance criteria.
- CLI command behavior is documented and works end-to-end.
- Data model and migrations are backward-safe for local usage.
- Tests added or updated for core logic and edge cases.
- Handoff notes completed in the relevant `AGENT_*.md`.
