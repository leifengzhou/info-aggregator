# Info Aggregator

Self-hosted information aggregation for configurable topics and sources.

## Phase 1 Scope

Phase 1 builds the project foundation:
- YAML topic configuration
- YouTube transcript fetching
- SQLite metadata storage
- Filesystem storage for raw content
- CLI-driven fetch workflows

## Project Layout

```text
config/      Topic configuration
src/         Application packages and modules
data/        Runtime content, digests, and SQLite database
tests/       Test suite
coordination/Shared planning, handoff, and QA artifacts
```

## Quick Start

1. Create a Python 3.11+ virtual environment.
2. Install dependencies from `requirements.txt`.
3. Review and edit `config/topics.yaml`.
4. Implement or run the relevant CLI commands under `src/main.py` as tasks land.

## Status

The repository is currently in Phase 1 scaffolding. See `coordination/TASK_BOARD.md` for active task status.
