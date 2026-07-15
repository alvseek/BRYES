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

## Agent Memory
Fleet-authored work-product for this project lives in `.agents/` — session history
(`.agents/session/`) and project knowledge (`.agents/knowledge/`). Any agent working here
can read and extend it. See [.agents/README.md](.agents/README.md).
