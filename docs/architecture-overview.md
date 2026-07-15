---
project: BRYES
title: Architecture Overview
updated: 2026-07-15
tags: [computer-use-agent, vision, shell, effector-tiers, openrouter, docker, ui-tars, deepseek, architecture]
---

# BRYES — Architecture Overview

**BRYES = Brain-Eyes.** A **computer-use agent**: it screenshots a desktop and acts —
clicking/typing through vision, or running a command **directly via a shell channel** when
the task suits the command line. The perception→action loop, built
phase-by-phase from a `roadmap.md` Alvi hands over one phase at a time.
GitHub: **github.com/alvseek/BRYES** (remote named `alvseek`, commit identity
`alvseek`). Local: `c:\Work\IM\BRYES`. Windows + Docker Desktop (WSL2).

## The four pieces (all talk over HTTP; none runs inside another)

| Piece | What | Where |
|---|---|---|
| **Screen** | disposable Ubuntu desktop (Xvfb + fluxbox): screenshots + input, plus a sandboxed **shell** (`/exec`) | local Docker container, `screen/` |
| **Hands** | `xdotool` click/double-click/right-click/hover/scroll/drag/type/key inside that container | same container |
| **Eyes** | two models: **Qwen2.5-VL-72B** *describes* the screen (text for the Brain), **UI-TARS-1.5-7B** *locates* elements (grounding → coordinates) | rented, OpenRouter, `eyes/` |
| **Brain** | `qwen3.6-flash` (default, swappable) — state → next action (reasoning) | rented, OpenRouter, `brain/` |

**Two rules from the roadmap:** rent everything until it hurts (local GPU 3060 Ti 8GB
is a last resort, Phase 6); prove ONE real task end-to-end before generalizing.

## Bodies — the Device abstraction ([ADR-002](adr/2026-07-15-device-interface.md))

Screen + Hands + shell are **not** hard-wired to the container — they sit behind a swappable
**`Device`** interface (a *vision-controllable body*: `screenshot()` + `act()` + optional
`shell()`, plus a `Capabilities` manifest). The loop, Eyes, and Brain are **device-agnostic**;
each body keeps its transport private:

| Body | Transport | Notes |
|---|---|---|
| **`ContainerDevice`** (default) | HTTP → `:8000` | the Dockerized desktop, 1280×800, `bash` shell, all 8 pointer verbs |
| **`PhoneDevice`** | `adb` (USB) | a real Android phone — `screencap` / `input` / `adb shell`; 1080×2400 portrait, no right_click/hover, Back/Home keys, `scroll`→swipe |
| *`WindowsDevice`* | *(future)* | `mss` + `pyautogui`, in-process — named, not built |

The Brain assembles its **action vocabulary from the active body's `Capabilities`** — it is only
offered verbs the current body can do (a phone never sees `right_click`). Pure API/MCP channels
(no screen) are deliberately NOT `Device`s — that's a separate effector abstraction
([ADR-001](adr/2026-07-15-effector-hierarchy.md)'s Tier-1). One mind, swappable bodies.

## Repo layout

- `screen/` — Dockerfile + Flask control API (`/health`, `/screenshot`, `/pointer`,
  `/action`, `/exec`), `docker-compose.yml`, `test_phase1.py`, `test_hands.py` (deterministic
  Hands regression test), `test_shell.py` (deterministic shell-channel test). `/action` verbs:
  `click`, `double_click`, `right_click`, `hover`,
  `scroll`, `drag`, `type`, `key`. `/pointer` returns the mouse `(x,y)` for model-free
  action assertions. Live view: noVNC at `http://localhost:6080/vnc.html`; control API on `:8000`.
- `devices/` — the **Device abstraction** ([ADR-002](adr/2026-07-15-device-interface.md)): `base.py` (`Device` Protocol + `Capabilities`), `container.py` (`ContainerDevice`), `phone.py` (`PhoneDevice`, adb), `test_phone.py` (deterministic smoke). The loop's `run(goal, device=None)` defaults to `ContainerDevice`.
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
- **Brain / reasoning:** `qwen/qwen3.6-flash` (default, ~$0.19/$1.13 per M, 1M ctx,
  text-only) — won a 5-model browser-search bake-off (4 steps, clean, cheap). `brain_model`
  is swappable per `run()`; fallbacks `tencent/hy3` (256k ctx) or `deepseek/deepseek-v4-flash`
  (cheapest). Text-only → the Brain can't see; it reasons over the VLM `describe` text.
  `deepseek-v4-pro` and `minimax/minimax-m3` LOST the bake-off (pricier, no better — M3 also
  failed to recognize completion on a generic goal). Avoid legacy `deepseek-chat`/
  `deepseek-reasoner` (retire 2026-07-24).

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
- **Hands primitives are atomic:** `type` just sends text to the FOCUSED field — it does
  NOT click first (a click deselects a Ctrl+A selection → text appends instead of replaces,
  which broke browser URL-bar entry). The Brain focuses via an explicit `click`, then
  optionally `key` ctrl+a, then `type`. Composition (macros) belongs ABOVE the primitives.
  The full natural pointer set is `click` / `double_click` / `right_click` / `hover` /
  `scroll` (`direction` up|down) / `drag` (`target`→`destination`) — each is ONE atomic
  xdotool call with no hidden action. Movement is regression-tested (`test_hands.py` +
  `/pointer`); `scroll` also validated live on Tokopedia (2026-07-14).
- **Effector tiers — vision is the fallback, not the only tool** ([ADR-001](adr/2026-07-15-effector-hierarchy.md)):
  the Brain routes each intent to the most direct channel available.
  **Tier 2 — shell:** the `shell` action runs a NON-interactive command inside the container
  via `POST /exec` (`shell=True`, sandboxed; returns `{ok, exit_code, stdout, stderr}`) — used
  for OS/file/CLI/network tasks. Its result threads into HISTORY (invisible on screen, unlike a
  GUI action whose feedback is the next screenshot). Liveness: a 30s timeout (Brain-extendable
  via a `timeout` field, clamped to 300s) is `/exec`'s only recovery valve — a blocking call
  would freeze the loop, so every call is bounded; output truncated ~4 KB. Interactive terminals
  (REPL/ssh) are NOT for `shell` — the Brain drives `xterm` with vision.
  **Tier 3 — vision (Eyes + Hands):** GUI-only surfaces. **Tier 1 — API/MCP:** future; the
  pattern is named so later channels (http/mcp/email/phone) inherit it. Beyond the Hands, the
  Brain also has loop-level `wait` (pause N Brain-chosen seconds, clamped 0.5–30s) and
  `screenshot` (save a `capture-NN.png` deliverable). Full Brain action set: click /
  double_click / right_click / hover / scroll / drag / type / key / wait / screenshot /
  **shell** / done / fail.
- **Real browser = Google Chrome from the .deb:** apt `chromium`/`chromium-browser` on
  Ubuntu 24.04 is a *snap transitional* that won't run in a container. Chrome is installed
  from the official `.deb` (in the Dockerfile), launched `--no-sandbox` (Chrome won't run its
  sandbox as root; the disposable container is the isolation boundary and holds no secrets —
  the API key lives on the host). **The entrypoint auto-boots Chrome** at `CHROME_START_URL`
  (default google.com, override per task); gnome-calculator + xterm stay installed for
  on-demand launch, not auto-started.
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
(seeds in — VLM describe, atomic `type`, run transcripts; computes varied calcs cleanly
AND searches "who am I" in Chrome, and searched + captured Tokopedia page-1 results via
`wait`+`screenshot`; explicit post-action re-check/recover still to come) ·
6 Hosting ⬜ (only if forced). **Brain default: `qwen3.6-flash`** (bake-off winner).
