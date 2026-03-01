# AGENTS.md

## Cursor Cloud specific instructions

**AgentEval** is a pure Python library/CLI tool for evaluating AI agent responses. It has zero runtime dependencies (stdlib only); the only dev dependency is `pytest`.

### Quick reference

- **Install**: `pip install -e ".[dev]"` (see `pyproject.toml`)
- **Test**: `pytest` (24 tests, runs in < 1 s)
- **CLI**: `agent-eval --config config.json --tasks tasks.json --outputs outputs.json`
- **Python API**: see `README.md` Quick Start section

### Non-obvious notes

- The `agent-eval` CLI entry-point and `pytest` are installed to `~/.local/bin`. That directory must be on `PATH` (the VM snapshot includes this in `~/.bashrc`).
- There is no linter explicitly configured in the project. The `.gitignore` references `.mypy_cache/` and `.ruff_cache/` but neither mypy nor ruff is in the dev dependencies.
- There are no services to start — no database, no web server, no Docker. Tests and CLI run instantly.
