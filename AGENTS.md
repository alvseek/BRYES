# AGENTS.md

Guidance for AI agents working in the **BRYES** repo (Brain-Eyes — a vision-based
computer-use agent: screenshot → decide → click).

## House rules
- **Never commit `.env`** — it holds `OPENROUTER_API_KEY`. Only `.env.example` is tracked.
- **No emoji in Python that prints to the console** — Windows `cp1252` can't encode them and
  the script crashes on the `print`. Use ASCII markers (`PASS:` / `FAIL:` / `WARN:`).
  See [docs/python-conventions.md](docs/python-conventions.md).
- **Prove each piece live before chaining** — this project is built empirically, phase by
  phase from `roadmap.md`.

## Agent Orientation
This repo maintains a structured orientation map at `docs/orientation-map.md`.
Load it before starting work for architecture and navigation context.

## Procedures

Two project procedures live in `docs/procedures/`, each also served as a skill:

- **[Make a lesson](docs/procedures/make-a-lesson.md)** (`/make-lesson`) — build a teaching page
  from real screenshots (`capture.py` + `lesson.py`, output under `lessons/`).
- **[Drive the desktop](docs/procedures/drive-the-desktop.md)** (`/drive-desktop`) — operate a real
  Windows application through the host body, which needs `BRYES_ALLOW_HOST=1` and targets a window
  handle it started.

To use both from another project, install them globally: `setup-scripts\setup-all-claude-code.bat`
(Claude Code commands) or `setup-scripts\setup-all-opencode.bat` (OpenCode skills). The installed
file is a copy of the procedure, so re-run the installer after editing `docs/procedures/`.

## Agent Memory
Fleet-authored work-product for this project lives in `.agents/` — session history
(`.agents/session/`) and project knowledge (`.agents/knowledge/`). Any agent working here
can read and extend it. See [.agents/README.md](.agents/README.md).
