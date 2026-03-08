# Senior Dev Workspace

## Role
- Implement approved architecture in production-quality code.
- Follow contracts defined by the architect. Flag mismatches early.
- Hand off to QA with clear context on what changed and how to validate.

## Active Work
- Current Task ID: P1-BUG-002
- Status: in_review
- Started: 2026-03-08

## Blockers
- None yet.

## Handoff to QA
- Task ID: P1-BUG-002
- Behavior changed: Normalized `published_at`, digest period timestamps, and parsed `--since` values to timezone-aware UTC before storage and filtering. This removes offset-dependent string comparison bugs in SQLite and makes `--since` behavior consistent across mixed source timezones.
- Files touched: src/db.py, src/main.py, tests/test_db.py, tests/test_main.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md
- Tests run: `python3 -m unittest tests.test_db tests.test_main`; `python3 -m compileall src tests`
- Known risks: Existing adapters other than YouTube are still unimplemented, so this fix is validated through DB and CLI regression tests rather than through multiple live source types.
- Suggested validation: Run `python3 -m unittest tests.test_db tests.test_main` and verify that a record published with a non-UTC offset still matches an equivalent UTC `--since` cutoff.
- Date: 2026-03-08

## Handoff History

| Task ID | Date | Files Touched | Tests Run | Known Risks |
|---------|------|---------------|-----------|-------------|
| P1-001 | 2026-03-07 | .gitignore, README.md, requirements.txt, config/topics.yaml, src/, tests/, data/ placeholders, coordination files | `python3 -m compileall src tests`; `python3 src/main.py`; topic count check on config | Implementation modules are placeholders; downstream architect handoffs still pending |
| P1-002 | 2026-03-07 | src/config.py, tests/test_config.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md, coordination/LESSONS.md | `python3 -m unittest tests.test_config`; example config load smoke; `python3 -m compileall src tests` | Cron validation is structural, not semantic; only Phase 1 source types are accepted |
| P1-005 | 2026-03-07 | src/transcript/, tests/test_transcript.py, requirements.txt, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_transcript tests.test_config tests.test_db`; `python3 -m compileall src tests`; transcript import smoke | Live fetching still depends on external network and transcript availability; playlist/title CLI helpers were not migrated in this slice |
| P1-006 | 2026-03-07 | src/adapters/youtube.py, tests/test_youtube_adapter.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_youtube_adapter`; full unit suite; `python3 -m compileall src tests` | Live RSS/transcript fetching not smoke-tested; artifacts are JSON payloads, not transcript-only text files |
| P1-007 | 2026-03-08 | src/main.py, tests/test_main.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_main`; full unit suite; `python3 -m compileall src tests` | CLI skips non-YouTube sources for now; expected parser errors print to stderr in negative-path tests |
| P1-BUG-001 | 2026-03-08 | src/adapters/youtube.py, tests/test_youtube_adapter.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_youtube_adapter`; full unit suite; `python3 -m compileall src tests` | Only feed discovery failures are downgraded; transcript fetch failures beyond missing subtitles still bubble |
| P1-008 | 2026-03-08 | src/logging_setup.py, src/main.py, src/db.py, src/adapters/youtube.py, tests/test_logging_setup.py, tests/test_main.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_logging_setup`; full unit suite; `python3 -m compileall src tests` | Console/file logs are intentionally verbose JSON lines; transcript fetch failures remain separate from feed warnings |
| P1-CLEANUP-001 | 2026-03-08 | coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `find . -maxdepth 2 \( -path './.git' -o -path './coordination/.git' \) -prune -o -type d -name '.venv' -print`; `git status --short --untracked-files=all` | Root `.venv/` remains intentionally; task scope only covered nested `coordination/.venv/` and stray `test_p1.db*` artifacts |
| P1-CLEANUP-002 | 2026-03-08 | config/topics.yaml, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_config`; live RSS `curl` check for every configured `channel_id` in `config/topics.yaml` | `TECH_SPEC.md` still references the stale old channel example until architect syncs the document |
| P1-REF-001 | 2026-03-08 | src/main.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_main`; `python3 -m compileall src tests` | Internal refactor only; adapter error-path aggregation remains covered indirectly rather than by dedicated new tests |
| P1-REF-002 | 2026-03-08 | src/adapters/youtube.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_youtube_adapter tests.test_db`; `python3 -m compileall src tests` | DB insert is now the sole dedup gate; filesystem write failures after insert are not specially recovered |
| P1-REF-003 | 2026-03-08 | src/__main__.py, tests/test_module_entrypoint.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_module_entrypoint`; `python3 -m src --help`; `python3 -m compileall src tests` | Help/entrypoint path is covered; full live fetch via `python -m src` is not separately exercised |
| P1-REF-004 | 2026-03-08 | requirements-dev.txt, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `cat requirements-dev.txt`; `python3 -m unittest tests.test_db`; `python3 -m compileall src tests` | `pytest` is declared but not installed in the current environment until the dev requirements are installed |
| P1-BUG-002 | 2026-03-08 | src/db.py, src/main.py, tests/test_db.py, tests/test_main.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `python3 -m unittest tests.test_db tests.test_main`; `python3 -m compileall src tests` | Fix is covered for DB and CLI normalization paths; additional source adapters will inherit it once implemented |
