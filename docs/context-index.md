---
project: BRYES
title: Context Index
updated: 2026-07-13
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
- **Apps in the Screen:** gnome-calculator, xterm, Google Chrome (baked into the Dockerfile).
- **Phase:** 0–4 done; loop runs varied calcs + a Chrome "who am I" search. Phase 5 (verify-and-recover, "the product") deferred until base capability ≥80% — see [backlog.md](backlog.md).
