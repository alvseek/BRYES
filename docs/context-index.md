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
| [backlog.md](backlog.md) | Living list of open work — tech debts + next steps (audit hands primitives for atomicity, add a combo/macro action, make a failed action non-fatal, validate the default Brain on the calc suite) + recently-resolved. The finer-grained "what's left" vs roadmap.md's phase plan. | backlog, tech-debt, next-steps, phase-5 |
| [quality-standard.md](quality-standard.md) | The project quality standard (9 dimensions, discovered from code). Dimension 9's headline: **formats are enforced by our schema + validation, not the AI** — LLM JSON via Pydantic + `response_format: json_schema` + our validation ([ADR-005](adr/2026-07-16-structured-output-standard.md)). Used by `/analyze-code-quality`. | quality, standard, structured-output, conventions, ruff |

## Quick facts
- **Repo:** github.com/alvseek/BRYES · local `c:\Work\IM\BRYES` · remote `alvseek`, commit identity `alvseek`.
- **Secret:** `OPENROUTER_API_KEY` in gitignored `.env` (one key = Eyes + Brain). Never commit it.
- **Run the Screen:** `cd screen && docker compose up -d` → API `:8000`, live view `:6080/vnc.html`.
- **Bodies ([ADR-002](adr/2026-07-15-device-interface.md)):** the loop drives a swappable `Device` — `ContainerDevice` (HTTP) or `PhoneDevice` (real Android over adb/USB, `tools/platform-tools/adb.exe`).
- **Embodiment selection ([ADR-006](adr/2026-07-17-embodiment-selection.md)):** `run(goal)` with no `device`/`profile` **self-selects** — the Brain reads the catalog `profiles/index.md` and returns `{device, profiles}` (`select_embodiment`), or `device=None` → it **answers directly** (`answer`), no loop, returns `{status:"answered", answer}`. The chosen top-level maps to a body (`android`→`PhoneDevice`, `linux`→`ContainerDevice`); ONE body per run (all profiles share the root). Explicit `run(device=…, profile=…)` **overrides** the pick (the test path). Profiles: `load_profiles(list)` merges + de-dups multiple chains.
- **Brain ([ADR-005](adr/2026-07-16-structured-output-standard.md)):** primary `deepseek/deepseek-v4-flash`, backup `google/gemini-2.5-flash-lite` (decide's LAST attempt escapes to it if the primary fails its tries). Output is a **Pydantic model → forced tool-call → OUR Pydantic validation** (`structured.py`) — NO `json_object` free-text; validity never depends on the provider. (json_schema strict:false was tried 2026-07-17 but let reasoning models drop optional fields like `visual_expectation` → reverted to tool-calling; ADR-005 Amendment 2.) Swappable via `run(brain_model=...)`. (qwen3.6-flash was dropped: its thinking mode mis-applies a json_schema grammar / forced tool_choice to the reasoning stream → degenerates — a documented Qwen bug.)
- **Structured output & focus-failure:** any format-bearing LLM output goes through `structured.py` (Pydantic + `response_format: json_schema`, validated on our side). The Eyes report honestly: `box()` answers `NOT_FOUND` instead of fabricating coords → `describe` gives `VISUAL_FOCUS FAILED` + an overview so the Brain re-orients. The Brain aims `visual_focus` at where an action's EFFECT shows (the display), not the control it pressed.
- **Eyes ([ADR-004](adr/2026-07-16-foveal-describe-trim.md)):** `describe` = `qwen/qwen3-vl-8b` (two-mode foveal — overview gist / boxed-crop trim, ~2s); `box` + careful re-read = `qwen/qwen2.5-vl-72b`; `locate` = `bytedance/ui-tars-1.5-7b`.
- **Apps in the Screen:** gnome-calculator, xterm, Google Chrome (baked into the Dockerfile).
- **Screen resolution:** `SCREEN_RESOLUTION` env override in `docker-compose.yml` (default `1280x800x24`; e.g. `SCREEN_RESOLUTION=2560x1600x24 docker compose up -d --force-recreate`).
- **Phase:** 0–5 done. The loop verifies + recovers ([ADR-003](adr/2026-07-16-change-feedback-verify-and-recover.md)) and `describe` is two-mode foveal (~2s, [ADR-004](adr/2026-07-16-foveal-describe-trim.md)) — bottleneck now the Brain. Runs varied calcs, Chrome searches, Tokopedia capture. See [backlog.md](backlog.md).
