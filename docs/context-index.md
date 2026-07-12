---
project: BRYES
title: Context Index
updated: 2026-07-12
---

# BRYES Project Context

Structural context for BRYES, localized into this repo alongside the orientation
map (`orientation-map.md`). Universal facts every agent on BRYES should know —
load on relevance.

| File | Description | Tags |
|---|---|---|
| [architecture-overview.md](architecture-overview.md) | What BRYES is (Brain-Eyes vision computer-use agent), the 4-piece HTTP architecture (Screen/Hands/Eyes/Brain), repo layout, OpenRouter model slugs, and load-bearing technical facts (UI-TARS coordinate convention, bare-symbol grounding, DeepSeek text-only + reasoning truncation, gnome-calculator). | computer-use-agent, architecture, ui-tars, deepseek, openrouter, docker |
| [python-conventions.md](python-conventions.md) | Python coding conventions — chiefly: no emoji in console output (Windows cp1252 → UnicodeEncodeError crashes the script); use ASCII markers (PASS:/FAIL:/WARN:). Em-dashes are fine. | python, conventions, encoding, windows, console |

## Quick facts
- **Repo:** github.com/alvseek/BRYES · local `c:\Work\IM\BRYES` · remote `alvseek`, commit identity `alvseek`.
- **Secret:** `OPENROUTER_API_KEY` in gitignored `.env` (one key = Eyes + Brain). Never commit it.
- **Run the Screen:** `cd screen && docker compose up -d` → API `:8000`, live view `:6080/vnc.html`.
- **Phase:** 0–4 done (loop closes); Phase 5 (verify-and-recover) is next and is "the product".
