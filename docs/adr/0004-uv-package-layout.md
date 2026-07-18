# UV + installable package layout for v3

v3 is developed as an installable Python package under `src/gtp/` with `pyproject.toml` and **uv** for env, lockfile, and `uv run` (not pip/`requirements.txt` as the primary workflow). Tests live in `tests/` with **pytest**; lint/format with **ruff**; CI (GitHub Actions) runs on PRs into the rewrite line. Python baseline for v3 is **3.11+**. One-file script layout and pip-centric docs are retired at 3.0 cutover; until then `main` keeps the v2 script story.
