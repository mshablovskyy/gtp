# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Google Takeout Processor (GTP)** — a small Python CLI that restores original creation/modification dates on Google Photos Takeout dumps and copies them into an organized output tree. Source files are never modified; everything is **copied**.

Repo: https://github.com/mshablovskyy/gtp

## Commands

```bash
# deps (uv is available in this environment; pip may not be)
uv pip install -r requirements.txt
# or: python3 -m pip install -r requirements.txt

# main processor
python3 gtp.py -p /path/to/unpacked-takeout
python3 gtp.py -p /path/to/takeout -d /path/to/output
python3 gtp.py -p /path/to/takeout -s "-sticker" -s "-edited"

# helper: split jsons vs media for safer re-runs with new suffixes
python3 separate.py -s /path/to/source -d /path/to/out

python3 gtp.py -h
python3 separate.py -h
```

No test suite, linter, typecheck, or CI exists yet. When adding tests, put them under `tests/` and document the single-test command here.

## Architecture

Two scripts, one library-style module:

| File | Role |
|------|------|
| `gtp.py` | All processing logic + CLI entry (`parse` → `main`) |
| `separate.py` | Thin CLI that imports helpers from `gtp` to split JSON vs non-JSON copies |

**Core pipeline (`gtp.main`):**

1. Walk input → split into JSON paths vs media file dicts (`get_file_names`), each media item tagged with album folder name.
2. For each JSON: `unpack_json` → title + `photoTakenTime.timestamp`.
3. `find_file` matches media by reconstructing candidate names from title + **suffixes** + album folder (Google often shares one JSON across `photo.jpg` and `photo-edited.jpg`).
4. Matches → copy into `gtpOutput/Processed/<album>/` and set created/modified via `filedate` (`copy_modify`).
5. Unmatched media + orphan JSONs → `gtpOutput/Unprocessed/`.
6. Write `logs.txt` + `detailed_logs.txt`.

**Important domain quirks (do not “simplify” away without evidence):**

- **Suffixes** (`""`, `"-edited"`, user-supplied): Google omits separate JSON for edited/variant filenames; one JSON titles the base name.
- **Title truncation**: matching shortens names when `title` length > 51 (Takeout filesystem naming).
- **Bracketed JSON names** (`foo(1).json`): duplicated titles; brackets are reattached when searching for media.
- **Album = parent folder name** of the media/JSON — output preserves Takeout’s album layout, not “by year only”.
- **Non-destructive**: always `shutil.copy`; collisions get `(n)` suffixes via `get_unique_path`.

Deps: `filedate`, `tqdm` (see `requirements.txt`). Python 3.9+ preferred per README.

## Git / commits

**Never** add Claude (or any AI) as co-author, contributor, or trailer on commits or PRs. No `Co-Authored-By: Claude …`, no “Generated with Claude Code” footers, no AI-as-author. Commits and PR attribution are the human’s only.

## Agent skills

### Issue tracker

GitHub Issues via `gh` CLI (`mshablovskyy/gtp`). See `docs/agents/issue-tracker.md`.

### Triage labels

Defaults: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.
