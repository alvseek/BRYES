---
project: BRYES
title: Architecture Overview
updated: 2026-07-11
tags: [computer-use-agent, vision, openrouter, docker, ui-tars, deepseek, architecture]
---

# BRYES — Architecture Overview

**BRYES = Brain-Eyes.** A vision-based **computer-use agent**: it screenshots a
desktop, decides an action, and clicks/types — the perception→action loop. Built
phase-by-phase from a `roadmap.md` Alvi hands over one phase at a time.
GitHub: **github.com/alvseek/BRYES** (remote named `alvseek`, commit identity
`alvseek`). Local: `c:\Work\IM\BRYES`. Windows + Docker Desktop (WSL2).

## The four pieces (all talk over HTTP; none runs inside another)

| Piece | What | Where |
|---|---|---|
| **Screen** | disposable Ubuntu desktop (Xvfb + fluxbox), screenshots + input | local Docker container, `screen/` |
| **Hands** | `xdotool` click/type/key inside that container | same container |
| **Eyes** | UI-TARS-1.5-7B — screenshot → element coordinates (grounding) | rented, OpenRouter, `eyes/` |
| **Brain** | DeepSeek V4 — state → next action (reasoning) | rented, OpenRouter, `brain/` |

**Two rules from the roadmap:** rent everything until it hurts (local GPU 3060 Ti 8GB
is a last resort, Phase 6); prove ONE real task end-to-end before generalizing.

## Repo layout

- `screen/` — Dockerfile + Flask control API (`/health`, `/screenshot`, `/action`),
  `docker-compose.yml`, `test_phase1.py`. `/action` verbs: `click`, `move`, `type`, `key`.
  Live view: noVNC at `http://localhost:6080/vnc.html`; control API on `:8000`.
- `eyes/client.py` — `describe(img)` (what's on screen, for the Brain) + `locate(img, instr)` (pixel x,y).
- `brain/client.py` — `decide(goal, observation, history)` → structured JSON action.
- `agent/loop.py` — `run(goal)` chains screenshot → describe → decide → locate → act.
- `.env` (gitignored) holds `OPENROUTER_API_KEY` (one key covers Eyes + Brain). Template: `.env.example`.

## Models (OpenRouter slugs — verified live)

- **Eyes / grounding:** `bytedance/ui-tars-1.5-7b` — the ONLY UI-TARS on OpenRouter
  (no 72B, no UI-TARS-2 yet). $0.10/M in, $0.20/M out, images free. Prefer 7B; 72B only
  if 7B underperforms (Alvi's cost call).
- **Brain / reasoning:** `deepseek/deepseek-v4-flash` (default, $0.077/$0.15 per M, 1M ctx,
  **text-only**) or `-pro` ($0.35/$0.70, stronger). Both text-only → Brain cannot see;
  it needs a text observation. Avoid legacy `deepseek-chat`/`deepseek-reasoner` (retire 2026-07-24).

## Load-bearing technical facts (costly to re-discover)

- **UI-TARS-1.5 coordinate convention:** Qwen2.5-VL based → outputs coords in the
  `smart_resize`d image space (sides rounded to multiples of 28, area clamped by
  MIN/MAX_PIXELS). Convert back: `actual = model_coord * original_dim / resized_dim`.
  For 1280×800 the resized size is 1288×812 (~1:1). Implemented in `eyes/client.py:smart_resize`.
- **Bare-symbol grounding is unreliable:** UI-TARS mislocates a bare `=` (consistently to
  the wrong spot); the WORD "equals" grounds correctly. Brain is coached to name symbol
  buttons in words ("the equals (=) button", "the plus (+) button").
- **DeepSeek V4 is a reasoning model:** hidden reasoning tokens count against `max_tokens`
  and truncate the JSON (`content: null`) if the cap is too low. Current config disables
  reasoning (`reasoning:{enabled:false}`) for the mechanical decider + `max_tokens: 4096`.
  V4 has 3 modes (Non-think / Think High / Think Max); NO auto-bypass — mode is per-request.
- **OpenRouter reasoning gotcha:** don't send both `reasoning_effort` and `reasoning.effort`
  (→ HTTP 400). Use the single nested `reasoning` form.
- **Target app matters:** swapped `xcalc` → `gnome-calculator` (needs `dbus-x11` + a
  `dbus-launch` session). Bigger buttons + big orange `=` + clear display → far more
  reliable grounding AND cleaner `describe`. The Windows/Docker cold-connection flake
  (`RemoteDisconnected`/`WinError 10053`) after a container restart is handled by HTTP retries.

## Phase status (roadmap)

0 key ✅ · 1 Screen ✅ · 2 Eyes ✅ · 3 Brain ✅ · 4 Closed loop ✅ (computes `7+8`, `100×3`
unattended) · 5 Verify-and-recover ⬜ (the product) · 6 Hosting ⬜ (only if forced).
