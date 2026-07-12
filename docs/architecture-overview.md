---
project: BRYES
title: Architecture Overview
updated: 2026-07-13
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
| **Eyes** | two models: **Qwen2.5-VL-72B** *describes* the screen (text for the Brain), **UI-TARS-1.5-7B** *locates* elements (grounding → coordinates) | rented, OpenRouter, `eyes/` |
| **Brain** | DeepSeek V4 — state → next action (reasoning) | rented, OpenRouter, `brain/` |

**Two rules from the roadmap:** rent everything until it hurts (local GPU 3060 Ti 8GB
is a last resort, Phase 6); prove ONE real task end-to-end before generalizing.

## Repo layout

- `screen/` — Dockerfile + Flask control API (`/health`, `/screenshot`, `/action`),
  `docker-compose.yml`, `test_phase1.py`. `/action` verbs: `click`, `move`, `type`, `key`.
  Live view: noVNC at `http://localhost:6080/vnc.html`; control API on `:8000`.
- `eyes/client.py` — `describe(img)` (screen → text, via Qwen2.5-VL-72B) + `locate(img, instr)` (element → pixel x,y, via UI-TARS-1.5-7B).
- `brain/client.py` — `decide(goal, observation, history)` → structured JSON action.
- `agent/loop.py` — `run(goal)` chains screenshot → describe → decide → locate → act.
- `.env` (gitignored) holds `OPENROUTER_API_KEY` (one key covers Eyes + Brain). Template: `.env.example`.

## Models (OpenRouter slugs — verified live)

- **Eyes / describe:** `qwen/qwen2.5-vl-72b-instruct` — a general VLM reads the screen
  faithfully (separates the live entry from history/log; ~$0.25/M in, $0.75/M out, image
  billed as input tokens). Called EVERY step → the highest-volume cost.
- **Eyes / locate (grounding):** `bytedance/ui-tars-1.5-7b` — the ONLY UI-TARS on
  OpenRouter. $0.10/M in, $0.20/M out, images free. UI-TARS is Qwen2.5-VL-7B tuned for
  grounding: great at pointing, but the fine-tune degraded description — which is why
  describe moved to a general VLM (above).
- **Brain / reasoning:** `deepseek/deepseek-v4-flash` (default, $0.077/$0.15 per M, 1M ctx,
  **text-only**) or `-pro` ($0.35/$0.70, stronger — the likely upgrade for harder
  multi-step reasoning). Both text-only → Brain cannot see; it needs a text observation.
  Avoid legacy `deepseek-chat`/`deepseek-reasoner` (retire 2026-07-24).

## Load-bearing technical facts (costly to re-discover)

- **UI-TARS-1.5 coordinate convention:** Qwen2.5-VL based → outputs coords in the
  `smart_resize`d image space (sides rounded to multiples of 28, area clamped by
  MIN/MAX_PIXELS). Convert back: `actual = model_coord * original_dim / resized_dim`.
  For 1280×800 the resized size is 1288×812 (~1:1). Implemented in `eyes/client.py:smart_resize`.
- **Grounding needs word + position:** UI-TARS mislocates a bare `=` (the WORD "equals"
  grounds correctly), AND when a symbol also appears in the display (e.g. the "=" in the
  shown equation) it may grab that instead of the keypad button. Brain is coached to name
  symbol buttons in words AND with position/context ("the equals (=) button on the keypad").
- **Describe vs locate use DIFFERENT models:** UI-TARS is a grounding fine-tune — asked to
  *describe*, it confabulates results and flattens a history/log into the current state
  (caused clear-loops + false "done"). So `describe` runs on a general VLM
  (Qwen2.5-VL-72B) that separates the live entry from history; `locate` stays on UI-TARS.
- **DeepSeek V4 is a reasoning model:** hidden reasoning tokens count against `max_tokens`
  and truncate the JSON (`content: null`) if the cap is too low. Current config enables
  **Think High** (`reasoning:{effort:"high"}`) + `max_tokens: 8192` (headroom for trace +
  JSON) — proven needed for reliable decisions; `decide()` also retries on malformed JSON.
  V4 has 3 modes (Non-think / Think High / Think Max); NO auto-bypass — mode is per-request.
- **OpenRouter reasoning gotcha:** don't send both `reasoning_effort` and `reasoning.effort`
  (→ HTTP 400). Use the single nested `reasoning` form.
- **Target app matters:** swapped `xcalc` → `gnome-calculator` (needs `dbus-x11` + a
  `dbus-launch` session). Bigger buttons + big orange `=` + clear display → far more
  reliable grounding AND cleaner `describe`. The Windows/Docker cold-connection flake
  (`RemoteDisconnected`/`WinError 10053`) after a container restart is handled by HTTP retries.

## Phase status (roadmap)

0 key ✅ · 1 Screen ✅ · 2 Eyes ✅ · 3 Brain ✅ · 4 Closed loop ✅ · 5 Verify-and-recover ◐
(seeds in — observation-grounded loop, VLM describe, run transcripts; computes varied
calcs cleanly: 1550×3÷4, 128+47, 512−137, 7÷8, 12+34+56. Explicit post-action
re-check/recover still to come) · 6 Hosting ⬜ (only if forced).
