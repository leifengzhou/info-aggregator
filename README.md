# Info Aggregator

Self-hosted content aggregation system that fetches, stores, and organizes information from configurable topics and sources.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Setup

```bash
# Create virtual environment and install dependencies
uv venv .venv && uv pip install -r requirements.txt

# Activate the environment
source .venv/bin/activate
```

## Configuration

Edit `config/topics.yaml` to define your topics and sources. Each topic has a name, schedule, digest frequency, and one or more sources:

```yaml
topics:
  my-topic:
    name: "My Topic"
    description: "What this topic tracks"
    relevance_threshold: 6
    schedule: "0 */4 * * *"   # cron expression or: hourly, daily, weekly
    digest: daily              # daily, weekly, or on-demand
    sources:
      youtube:
        - channel_id: "UCxxxxxx"
```

Supported source types: `youtube`, `reddit`, `rss` (only YouTube is implemented in Phase 1).

## Usage

### Fetch content for all configured topics

```bash
python -m src.main fetch
```

### Fetch a single topic

```bash
python -m src.main fetch --topic ai-research
```

### Fetch content published after a date

```bash
python -m src.main fetch --since 2026-03-01
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | `config/topics.yaml` | Path to topics config file |
| `--db` | `data/aggregator.db` | Path to SQLite database |
| `--content-root` | `data/content` | Directory for raw content artifacts |
| `--topic` | (all) | Fetch only this topic slug |
| `--since` | (none) | Only fetch content published on or after this date |
| `--log-level` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `--log-file` | `data/logs/info-aggregator.log` | Path to structured JSON log file |

## Project Layout

```
config/         Topic configuration (YAML)
src/            Application source code
  adapters/     Source adapters (YouTube, future: Reddit, RSS)
  transcript/   YouTube transcript extraction library
  config.py     Config loader and validation
  db.py         SQLite storage layer
  main.py       CLI entry point
  logging_setup.py  Structured JSON logging
data/           Runtime data (DB, content artifacts, logs, digests)
tests/          Test suite
```

## Running Tests

```bash
# Install test dependencies
uv pip install -r requirements-dev.txt  # or: pip install pytest

# Run all tests
python -m pytest tests/ -v
```

## Data Storage

- **SQLite database** (`data/aggregator.db`): content metadata, topic mappings, digest records
- **Content artifacts** (`data/content/youtube/`): raw JSON files per fetched item with full transcripts
- **Logs** (`data/logs/`): structured JSON line logs
