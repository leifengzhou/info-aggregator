# RULES.md - Shared Rules for All Agents

Every agent working on this project (Codex, Claude Code, Gemini) MUST follow these rules. Agent-specific configuration lives in each agent's own file (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`), but these shared rules take precedence on any overlap.

## Project Context

- **Name**: info-aggregator
- **PRD**: `PRD.md` (product requirements, user stories, acceptance criteria)
- **Tech Spec**: `TECH_SPEC.md` (architecture, schemas, interfaces, CLI reference)
- **Stack**: Python 3.11+, SQLite, local filesystem, DeepSeek/MiniMax LLM

## Agent Roles

| Agent | Role | Config File | Workspace |
|-------|------|-------------|-----------|
| Claude Code | Architect | `CLAUDE.md` | `coordination/AGENT_ARCHITECT.md` |
| Codex (GPT-5) | Senior Dev | `AGENTS.md` | `coordination/AGENT_DEV.md` |
| Gemini CLI | Senior QA | `GEMINI.md` | `coordination/AGENT_QA.md` |

## Coordination Folder

The `coordination/` folder is the shared workspace for multi-agent collaboration:

| File | Purpose |
|------|---------|
| `PROJECT.md` | Project source of truth — objectives, non-negotiables, definition of done |
| `TASK_BOARD.md` | Kanban-style task tracking — all agents read/write task status here |
| `DECISIONS.md` | Architecture Decision Records (ADR-lite) — log all design decisions |
| `LESSONS.md` | Shared lessons learned — mistakes and patterns to avoid repeating |
| `AGENT_ARCHITECT.md` | Architect's workspace — approved contracts, handoffs to dev |
| `AGENT_DEV.md` | Dev's workspace — implementation log, handoffs to QA |
| `AGENT_QA.md` | QA's workspace — issue log, sign-offs, test plans |

**Rules for coordination files:**
- Update `TASK_BOARD.md` status and owner BEFORE starting work
- One owner per task at a time
- Schema or interface disagreements go to `DECISIONS.md` before code changes
- Handoff notes are mandatory when passing work between roles

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: add an entry to `coordination/LESSONS.md`
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review `coordination/LESSONS.md` at session start

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Check `coordination/TASK_BOARD.md` for the next task; claim it before starting
2. **Track Progress**: Update task status in `TASK_BOARD.md` as you go
3. **Log Decisions**: Record design choices in `coordination/DECISIONS.md`
4. **Handoff**: Write handoff notes in your `coordination/AGENT_*.md` workspace
5. **Capture Lessons**: After any correction, add to `coordination/LESSONS.md`

## Task Lifecycle

```
architect claims task -> designs interface/contract -> writes DECISIONS.md entry -> hands off to dev
dev claims task -> implements -> runs tests -> hands off to QA
QA validates against acceptance criteria -> signs off or rejects back to dev
```

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## Git Rules

### Branch Strategy
- `main` only — no feature branches until CI or multi-dev parallelism requires them

### Who Can Commit
- Any agent can commit work they own (per `TASK_BOARD.md` ownership)
- Do not commit someone else's in-progress work

### When to Commit
- **Commit at task completion** — when moving a task to `done` or handing off to the next role
- **Commit doc/coordination changes** in a single batch when a planning session ends
- Do not commit mid-task partial work; the repo should always be in a coherent state

### Commit Message Format
```
P1-XXX: short imperative description

Optional body with context if the "why" isn't obvious.
```
- Prefix with the task ID from `TASK_BOARD.md`
- Use `docs:` prefix for documentation-only changes with no task ID
- Use `chore:` prefix for tooling/config changes with no task ID

### What Not to Commit
- `.env`, secrets, API keys (enforced by `.gitignore`)
- Generated data (`data/` directory)
- IDE and editor config (`.vscode/`, `.idea/`)

## Guardrails

- Do not change module boundaries without an entry in `DECISIONS.md`
- Do not change DB schema without architect review
- Follow existing project layout from `TECH_SPEC.md`
- Keep adapters contract-compliant with the interface in `src/adapters/__init__.py`
