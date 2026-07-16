---
project: BRYES
title: Context Index
updated: 2026-07-16
---

# BRYES Project Context

Structural context for BRYES, localized into this repo alongside the orientation
map (`orientation-map.md`). Universal facts every agent on BRYES should know —
load on relevance.

| File | Description | Tags |
|---|---|---|
| [architecture-overview.md](architecture-overview.md) | What BRYES is (Brain-Eyes vision computer-use agent), the 4-piece HTTP architecture (Screen/Hands/Eyes/Brain), repo layout, OpenRouter model slugs, and load-bearing technical facts (UI-TARS coordinate convention, bare-symbol grounding, DeepSeek text-only + reasoning truncation, gnome-calculator). | computer-use-agent, architecture, ui-tars, deepseek, openrouter, docker |
| [python-conventions.md](python-conventions.md) | Python coding conventions — chiefly: no emoji in console output (Windows cp1252 → UnicodeEncodeError crashes the script); use ASCII markers (PASS:/FAIL:/WARN:). Em-dashes are fine. | python, conventions, encoding, windows, console |
| [agent-loop-flow.md](agent-loop-flow.md) | The data-flow view of the agent loop: how Screen/Hands/Eyes/Brain connect (one orchestrator, two transports), exactly what each piece is fed and emits per step (prompts + payloads), the two lossy seams (Brain-is-blind, history-is-unverified), the 1024 clear-loop post-mortem, and the 2026-07-13 update (actions-only history, atomic `type`, browser generalization, qwen3.6-flash brain). Complements architecture-overview.md (structure). | loop, data-flow, wiring, describe, decide, verify, phase-5, post-mortem |
| [backlog.md](backlog.md) | Living list of open work — tech debts + next steps (audit hands primitives for atomicity, add a combo/macro action, validate qwen3.6-flash on the calc suite, Phase 5 verify-and-recover deferred until ≥80% base capability) + recently-resolved. The finer-grained "what's left" vs roadmap.md's phase plan. | backlog, tech-debt, next-steps, phase-5 |

## Quick facts
- **Repo:** github.com/alvseek/BRYES · local `c:\Work\IM\BRYES` · remote `alvseek`, commit identity `alvseek`.
- **Secret:** `OPENROUTER_API_KEY` in gitignored `.env` (one key = Eyes + Brain). Never commit it.
- **Run the Screen:** `cd screen && docker compose up -d` → API `:8000`, live view `:6080/vnc.html`.
- **Bodies ([ADR-002](adr/2026-07-15-device-interface.md)):** the loop drives a swappable `Device` — `ContainerDevice` (default, HTTP) or `PhoneDevice` (real Android over adb/USB, `tools/platform-tools/adb.exe`). `run(goal, device=None)` → container.
- **Brain:** default `qwen/qwen3.6-flash` (swappable via `run(brain_model=...)`).
- **Eyes ([ADR-004](adr/2026-07-16-foveal-describe-trim.md)):** `describe` = `qwen/qwen3-vl-8b` (two-mode foveal — overview gist / boxed-crop trim, ~2s); `box` + careful re-read = `qwen/qwen2.5-vl-72b`; `locate` = `bytedance/ui-tars-1.5-7b`.
- **Apps in the Screen:** gnome-calculator, xterm, Google Chrome (baked into the Dockerfile).
- **Screen resolution:** `SCREEN_RESOLUTION` env override in `docker-compose.yml` (default `1280x800x24`; e.g. `SCREEN_RESOLUTION=2560x1600x24 docker compose up -d --force-recreate`).
- **Phase:** 0–5 done. The loop verifies + recovers ([ADR-003](adr/2026-07-16-change-feedback-verify-and-recover.md)) and `describe` is two-mode foveal (~2s, [ADR-004](adr/2026-07-16-foveal-describe-trim.md)) — bottleneck now the Brain. Runs varied calcs, Chrome searches, Tokopedia capture. See [backlog.md](backlog.md).
