# Senior Dev Workspace

## Role
- Implement approved architecture in production-quality code.
- Follow contracts defined by the architect. Flag mismatches early.
- Hand off to QA with clear context on what changed and how to validate.

## Active Work
- Current Task ID: P1-012
- Status: todo
- Started: 2026-03-08

## Blockers
- None yet.

## Handoff from Architect — P1-012: Switch transcript backend to yt-dlp

**Decision:** DEC-008. Full rationale in `coordination/DECISIONS.md`.

**Why:** `youtube-transcript-api` fails on auto-generated captions due to YouTube bot detection. yt-dlp is already a dependency and has active anti-bot maintenance. A `curl-cffi` gap caused a 429 in testing; adding that package fixes it transparently.

### Files to change

| File | Change |
|------|--------|
| `src/transcript/extractor.py` | Replace `youtube-transcript-api` with `yt_dlp.YoutubeDL` Python API; add `_extract_info`, `_download_subtitle_content`, `_parse_json3`, `_parse_vtt`; add retry loop |
| `tests/test_transcript.py` | Replace `@patch("src.transcript.extractor._build_api")` mocks with mocks for `_extract_info` and `_download_subtitle_content`; update mock data to info-dict structure |
| `requirements.txt` | Remove `youtube-transcript-api>=1.2,<2.0`; add `curl-cffi>=0.7,<1.0` |
| `src/config.py` | Add `youtube_transcript_max_retries: int = 3` and `youtube_cookies_file: str \| None = None` to `Settings` dataclass |
| `src/adapters/youtube.py` | Forward `cookies_file=settings.youtube_cookies_file` and `max_retries=settings.youtube_transcript_max_retries` through `YouTubeAdapter` constructor into transcript fetcher calls |

### `fetch_transcript()` new signature (public interface)
```python
def fetch_transcript(
    video: str,
    lang: str = "en",
    proxy_url: str | None = None,
    preserve_formatting: bool = False,  # kept for API compat, ignored by yt-dlp
    cookies_file: str | None = None,    # NEW: path to cookies.txt
    max_retries: int = 3,               # NEW: retry count on 429
    retry_delay_seconds: float = 60.0,  # NEW: base delay, doubles each attempt
    _sleep_func=time.sleep,             # injectable for tests
) -> TranscriptResult:
```
Return type `TranscriptResult` and `TranscriptSegment` are **unchanged**.

### New private functions (testability seams)
```python
def _extract_info(video_id: str, ydl_opts: dict) -> dict:
    """Wraps yt_dlp.YoutubeDL.extract_info(). Mockable in tests."""

def _download_subtitle_content(url: str) -> str:
    """Downloads subtitle text from URL. Mockable in tests."""
```

### Language resolution logic (mirrors current behavior)
1. `info['subtitles'][lang]` → manual upload, `is_generated=False`
2. `info['automatic_captions'][lang]` → auto-generated, `is_generated=True`
3. Any other available language → log `transcript_language_fallback` WARNING
4. Nothing available → raise `TranscriptNotAvailableError`

### json3 parse contract
- Iterate `events[]`; for each event: concatenate `segs[].utf8`; skip if result is empty or `"\n"`
- `tStartMs / 1000.0` → `TranscriptSegment.start`
- `dDurationMs / 1000.0` → `TranscriptSegment.duration`

### Retry contract
- Catch `yt_dlp.utils.DownloadError` where `"429"` appears in the message string
- On retry `i` (0-indexed): sleep `retry_delay_seconds * (2 ** i)` via `_sleep_func`
- After `max_retries` exhausted, re-raise

### Verification commands
```bash
# All tests pass
.venv/bin/python -m pytest tests/ -q

# Config loads new settings with defaults
.venv/bin/python -c "
from src.config import load_config
c = load_config('config/topics.yaml')
print(c.settings.youtube_transcript_max_retries)  # → 3
print(c.settings.youtube_cookies_file)             # → None
"

# Live fetch (after curl-cffi install + 429 cooldown)
.venv/bin/python -c "
from src.transcript import fetch_transcript
r = fetch_transcript('KRE8JqTAEQk')
print(r.language_code, r.is_generated, len(r.segments))
"
```

## Handoff to QA
- Task ID: P1-010
- Behavior changed: Added optional `topic.fetch_since` config field parsing (ISO date/datetime, normalized to UTC) and wired `run_fetch()` to use it as the per-topic default `since` when CLI `--since` is omitted. Explicit CLI `--since` now overrides topic defaults for the run.
- Files touched: src/config.py, src/main.py, tests/test_config.py, tests/test_main.py, config/topics.example.yaml, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md
- Tests run: `.venv/bin/python -m pytest -q tests/test_config.py tests/test_main.py`; `.venv/bin/python -m pytest -q`
- Known risks: `fetch_since` is topic-level only; current Phase 1 fetch path still executes YouTube sources only, so non-YouTube behavior remains unchanged/skipped.
- Suggested validation: Run `python -m src fetch --config config/topics.example.yaml` without `--since` to confirm topic defaults are used; rerun with `--since` to confirm CLI override across topics.
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
| P1-BUG-004 | 2026-03-08 | src/config.py, src/main.py, src/adapters/youtube.py, tests/test_config.py, tests/test_main.py, tests/test_youtube_adapter.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `.venv/bin/python -m pytest -q tests/test_config.py tests/test_main.py tests/test_youtube_adapter.py`; `.venv/bin/python -m pytest -q` | Delay is blocking by design for Phase 1 CLI; live pacing validated via unit tests rather than external API timing |
| P1-REF-007 | 2026-03-08 | src/adapters/youtube.py, tests/test_youtube_adapter.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `.venv/bin/python -m pytest -q tests/test_youtube_adapter.py tests/test_transcript.py`; `.venv/bin/python -m pytest -q` | Refactor-only change; behavior parity relies on unit tests rather than live API smoke |
| P1-CLEANUP-003 | 2026-03-08 | src/db.py, tests/test_db.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `.venv/bin/python -m pytest -q tests/test_db.py tests/test_youtube_adapter.py`; `.venv/bin/python -m pytest -q` | Dead-code removal only; no runtime behavior change expected |
| P1-REF-008 | 2026-03-08 | tests/test_youtube_adapter.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `.venv/bin/python -m pytest -q tests/test_youtube_adapter.py`; `.venv/bin/python -m pytest -q` | Test-only change; no production behavior modifications |
| P1-BUG-005 | 2026-03-08 | src/main.py, tests/test_main.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `.venv/bin/python -m pytest -q tests/test_main.py`; `.venv/bin/python -m pytest -q` | Timestamp precision is per-second; concurrent same-second runs may collide |
| P1-REF-009 | 2026-03-08 | src/main.py, tests/test_main.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `.venv/bin/python -m pytest -q tests/test_main.py`; `.venv/bin/python -m pytest -q` | run_id propagation is scoped to fetch lifecycle events and summary |
| P1-BUG-006 | 2026-03-08 | src/transcript/extractor.py, tests/test_transcript.py, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `.venv/bin/python -m pytest -q tests/test_transcript.py`; `.venv/bin/python -m pytest -q` | Warning depends on fallback success path; hard failure path remains exception-based |
| P1-010 | 2026-03-08 | src/config.py, src/main.py, tests/test_config.py, tests/test_main.py, config/topics.example.yaml, coordination/TASK_BOARD.md, coordination/AGENT_DEV.md | `.venv/bin/python -m pytest -q tests/test_config.py tests/test_main.py`; `.venv/bin/python -m pytest -q` | Topic defaults apply only when CLI `--since` is omitted; non-YouTube sources remain skipped in Phase 1 fetch flow |
