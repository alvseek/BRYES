---
project: "BRYES"
description: "Orientation map for BRYES — index of the build roadmap and the four module READMEs (Screen/Eyes/Brain/Loop) with staleness tracking."
created: "2026-07-12"
last_full_scan: "2026-07-12"
source_of_truth: project
---

# Orientation Map — BRYES

Index of orientation artifacts in this project. Used by agents at awakening (load into session context) and wrap-up (refresh entries the session touched) via the `/map-orientation` skill.

## Status Legend

- **useful** — current, accurate, future tasks will rely on it. Update when scope changes.
- **stale-but-valuable** — could be useful if updated. Repair on demand when next task hits its scope.
- **obsolete** — neither current nor valuable. Ignore. Optional: archive or delete.
- **unverified** — mtime changed since `last_verified`, or never verified. Next task touching its scope verifies and updates status.

## Scope Legend

- **shared** — relevant to every role on this project. Always loaded.
- **role-private** — relevant only to roles listed in `roles`. Other roles skip.
- **cross-readable** — relevant to roles listed in `roles`, PLUS Architect and QA always.

## Type Legend

- **7q-readme** — 7 Questions Framework README.
- **architecture-map** / **architecture-overview** — project-wide navigation / single-section deep-dive.
- **flow-diagram** / **flow-journey-map** — control/data-flow deep-dive / map altitude.
- **domain-model** / **domain-context-map** — data-model / bounded-context map.
- **adr** — Architecture Decision Record.
- **orientation-map-link** — pointer to a child sub-project map.
- **other** — orientation artifact that doesn't fit above (roadmaps, non-7Q module READMEs, etc.).

> **Single-role project**: BRYES is Architect-only (Alvi's solo project, no fleet split), so every entry is `scope: shared, roles: []` — the role filter is a no-op.

---

## Entries

### `README.md`

- **type**: 7q-readme
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [readme, 7q, overview, entry-point, architecture, github]
- **last_verified**: "2026-07-19"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the four pieces (Screen/Eyes/Brain/Loop), setup, the task entry point (run()), the ADR list, or the high-level architecture change"
- **notes**: "The root, GitHub-facing project README (7 Questions Framework) — the single project overview. Covers what BRYES is (Brain-Eyes vision computer-use agent), the CURRENT module coupling (the loop is the sole coupler — grounded on docs/modularity.mmd + docs/loop-dispatch.mmd), setup, how to give a task (run(goal) from Python), the per-step flow, the ADR-001..008 index, and known debts. Supersedes roadmap.md as the closest-to-root overview. Generated 2026-07-19 via /generate-readme."

### `roadmap.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [roadmap, phases, architecture, entry-point]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: "when a phase is added/completed or the target architecture (4 pieces, verify step) changes"
- **notes**: "The milestone-driven build plan, handed to Claude Code one phase at a time (goal / build / test / trap per step). Names the target: Brain+Eyes+Screen+Hands over HTTP, with verify-and-recover as the differentiator. A build-sequence plan — the project overview now lives in the root `README.md` (added 2026-07-19)."

### `screen/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [screen, hands, shell, exec, docker, xvfb, xdotool, flask-api]
- **last_verified**: "2026-07-15"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the Screen container stack, the /screenshot|/action|/exec API, or ports change"
- **notes**: "Phase 1 — the Screen+Hands: disposable Ubuntu container (Xvfb + fluxbox + xdotool + scrot) exposing screenshot + the full Hands action set (click/double_click/right_click/hover/scroll/drag/type/key) over a Flask API (:8000) with noVNC live view (:6080). Also POST /exec — the Tier-2 shell effector (run a command in the sandboxed container; ADR-001). Apps: gnome-calculator, xterm, Chrome. Tests: test_hands.py + test_shell.py."

### `eyes/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [eyes, grounding, ui-tars, openrouter, coordinates]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: "when the Eyes model, locate()/describe() signatures, or coordinate convention change"
- **notes**: "Phase 2 — the Eyes: UI-TARS-1.5-7B grounding client (rented via OpenRouter, not a container). locate(png, instr) -> pixel (x,y); describe(png) -> text for the Brain. Documents the smart_resize coordinate-conversion convention."

### `brain/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [brain, decider, deepseek, openrouter, json-action]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: "when the Brain model, decide() signature, or the action JSON shape change"
- **notes**: "Phase 3 — the Brain: DeepSeek V4 decider (rented, text-only). decide(goal, observation, history) -> one structured JSON action naming its target by description. Eyes ground the description to a pixel afterward."

### `agent/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [loop, orchestration, closed-loop, phase-4]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: "when the loop's step sequence changes or verify-and-recover (Phase 5) lands"
- **notes**: "Phase 4 — Close the Loop: agent/loop.py chains screenshot -> Eyes.describe -> Brain.decide -> Eyes.locate -> Hands act, until done/fail/step-limit. Now also dispatches the `shell` action (exec_cmd -> /exec, result into HISTORY). No verify-and-recover yet (that's Phase 5, the product)."

### `api/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [api, task-invocation, flask, async, http, jobmanager]
- **last_verified**: "2026-07-19"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the task API endpoints, the JobManager lifecycle, or the run() wrapping change"
- **notes**: "The host-side Task-Invocation API (ADR-008): give BRYES a task over HTTP instead of a script. `python api/server.py` -> :8100; POST /tasks {goal,...} -> {task_id}, GET /tasks/<id> -> {status, steps, result} (result carries the findings ledger). Async (a daemon thread per task), single-flight (409 busy), localhost-only. Wraps agent/loop.py run() (the coarse 'hand off a whole goal' path); MCP adapter later. Distinct from screen/server/ (the container body API). Tests: api/test_jobs.py + api/test_server.py (model-free)."

### `docs/adr/2026-07-15-effector-hierarchy.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, effector-tiers, shell, vision, architecture]
- **last_verified**: "2026-07-15"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the effector-tier model changes or a new channel (Tier 1 API/MCP, a persona surface) is added/built"
- **notes**: "ADR-001 — BRYES's effector hierarchy: the Brain routes each intent to the highest-available channel (Tier 1 API/MCP [future] · Tier 2 shell /exec · Tier 3 vision-fallback). Reframes BRYES as a tool-using agent, vision = one tool; future channels inherit the pattern."

### `docs/adr/2026-07-15-device-interface.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, device, capabilities, phone, adb, protocol, architecture]
- **last_verified**: "2026-07-15"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the Device interface / Capabilities change or a new body (WindowsDevice, another phone) is added"
- **notes**: "ADR-002 — the `Device` abstraction: Screen+Hands+shell extracted into a swappable *vision-controllable body* (`devices/` package: base/container/phone) with a per-device `Capabilities` manifest; loop/Brain/Eyes stay device-agnostic, transport is device-private. Proven by adding a real Android phone (`PhoneDevice`, adb/USB) as body #2. Orthogonal to ADR-001 (tier vs body)."

### `docs/adr/2026-07-16-change-feedback-verify-and-recover.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, phase-5, verify-and-recover, expect, change-feedback, seam-b, recovery]
- **last_verified**: "2026-07-16"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the change-feedback design changes (expect/focus/request_diff modifiers, the recovery trigger) or framediff is un-parked"
- **notes**: "ADR-003 — Phase 5 verify-and-recover closes Seam B. Change-feedback is the VLM's job, split correctly (Eyes perceive, Brain judges): the Brain emits a `expect` per action, and the next `describe` REPORTS that thing's actual state (`VERIFICATION: <state>`, no verdict) for the Brain to compare — Layer 2, primary. Plus `request_diff` (Brain-gated 2-image diff, Layer 3) and a dumb advisory repeated-action recovery guard. Two things measured & dropped: the screen-wide pixel no-op ('Layer 1' — a typed digit scores below the noise floor, UI-TARS can't box a crop region; `framediff.py` parked), and the VLM pass/fail verdict (noisy — report-not-judge instead). Unifies focus/expect/request_diff into one prospective describe-modifier family."

### `docs/adr/2026-07-16-foveal-describe-trim.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, describe-speed, foveal, trim, box, overview, q3-8b, recheck, architecture]
- **last_verified**: "2026-07-16"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the describe modes (overview/trim), the boxer, the crop-describe model, or the recheck rung change"
- **notes**: "ADR-004 — two-mode foveal describe cuts describe latency (5-16s -> ~2s) by attacking OUTPUT LENGTH, not model/image (72B boxes in ~1.5s but describes in 5-16s, same frame). OVERVIEW (no focus): downscaled x0.5 gist on qwen3-vl-8b. TRIM (focus): 72B box() -> crop(+15%) -> q3-8b describes the crop; expect now REQUIRES focus, rides the crop as VERIFICATION. 72B demoted to authoritative Eyes (boxing + `recheck` careful re-read). Ladder q3-8b -> recheck -> request_diff. Qwen2.5-VL emits ABSOLUTE box coords at any res (validated to 4M px, no conversion). box None (unparseable/failed) -> full-frame fallback. Live: describe now UNDER decide."

### `docs/adr/2026-07-16-structured-output-standard.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, structured-output, pydantic, json-schema, validation, format-enforcement, model-fallback, architecture]
- **last_verified**: "2026-07-17"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the structured-output mechanism (structured.py / BrainAction / response_format json_schema), the model primary/backup, or the format-enforcement standard changes"
- **notes**: "ADR-005 (amended TWICE 2026-07-17) — structured LLM output: formats are enforced by OUR schema + Pydantic validation, not the AI. Mechanism RE-REVERTED to FORCED TOOL-CALLING (Amendment 2): Pydantic model -> forced tool-call -> OUR Pydantic validation (structured.py); never json_object free-text; validity never depends on the provider. (json_schema strict:false was tried in Amendment 1 but let reasoning models drop OPTIONAL fields — visual_expectation 89%->0%, Phase-5 verify silently died — so reverted; qwen, the only reason we'd left tool-calling, was already dropped.) Model: deepseek-v4-flash primary + gemini-2.5-flash-lite backup (both re-emit visual_expectation under tool-calling; gemini does NOT degenerate). Also: box() NOT_FOUND -> VISUAL_FOCUS FAILED + overview; focus->visual_focus, expect->visual_expectation."

### `docs/adr/2026-07-17-embodiment-selection.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, embodiment, device-selection, profiles, catalog, answer-only, architecture]
- **last_verified**: "2026-07-17"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when embodiment selection (select_embodiment / Embodiment / resolve_embodiment / _ROOT_DEVICE / the run() selection stage / profiles/index.md) or the answer-only path changes"
- **notes**: "ADR-006 — the agent SELF-SELECTS its embodiment at task start: before the loop (text-only, no screenshot yet) the Brain reads the catalog profiles/index.md and returns Embodiment{device, profiles, reason} — which BODY (android->PhoneDevice, linux->ContainerDevice; ONE body per run) + which app profiles, or device=None -> answer(goal) directly (no loop). load_profiles(list) merges + de-dups multiple profile chains, LABELLED per-profile (HOW ANDROID/WHATSAPP WORKS -> Brain, ...LOOKS -> Eyes). Explicit run(device=/profile=) overrides the pick. Builds on ADR-002 (Device) + ADR-005 (structured output). Validated live: answer-only + WhatsApp self-select on the real phone (self-picked android+android/whatsapp)."

### `docs/adr/2026-07-18-brain-prompt-restructure.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, brain-prompt, confirmed-findings, current-condition, channel-aware, eyes-skip, convergence, architecture]
- **last_verified**: "2026-07-18"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the decide() prompt structure (_build_decide_prompt / CURRENT CONDITION / CONFIRMED FINDINGS / the findings+note fields / the loop findings ledger / _changes_screen / the Eyes-skip) changes"
- **notes**: "ADR-007 — the Brain's per-step decide() prompt is priority-ordered labelled blocks (GOAL / CURRENT CONDITION [channel-aware: shell result = /exec output, screen marked UNCHANGED] / CONFIRMED FINDINGS [append-only, loop-owned ledger the Brain banks facts into via a `findings` field and TRUSTS] / HISTORY [action + compact `note`] / PROFILES MANUAL / TODO), with an Eyes-skip on non-visual actions. Fixes the re-read/re-doubt non-convergence (the Brain forgot facts because HISTORY was actions-only). Base-prompt trust-split: judge SCREEN from CURRENT CONDITION, TRUST findings/history. Keeps ADR-005 forced tool-calling (findings/note are new fields). Amendment note: ADR-004 Amendment 1 (same session) swapped DESCRIBE_MODEL 8b->30b-a3b to fix the numeric-misread — obsoleting the 'route numeric to 72B' follow-up."

### `docs/adr/2026-07-19-task-invocation-api.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, task-invocation, api, flask, async, mcp, jobmanager, architecture]
- **last_verified**: "2026-07-19"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the task-invocation architecture changes (sync/async, HTTP/MCP, the endpoint/result contract, the concurrency model)"
- **notes**: "ADR-008 - BRYES tasks are invoked through an ASYNC HTTP task service (POST /tasks -> task_id, GET /tasks/<id> polls) wrapping the native run() loop; API-first, MCP as a later thin adapter. Step 0 of the loop-as-a-service target (docs/modularity-target.mmd). Decisions: Flask, global single-flight (409 busy), localhost-only + no auth, result = status/steps/history + CONFIRMED FINDINGS ledger, in-memory job store, one daemon thread per task."

### `docs/quality-standard.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [quality-standard, conventions, structured-output, ruff, analyze-code-quality]
- **last_verified**: "2026-07-17"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when a project convention changes (error handling, efficiency, security, tooling/ruff, or a project-specific rule) or a new dimension is added"
- **notes**: "The project quality standard — 9 dimensions filled from code (error handling degrades-not-crashes, model tiering, .env secrets, ASCII console, module-per-role, ruff, conventional-commits). Dimension 9 headline: FORMATS ARE ENFORCED BY TOOLS, NOT THE AI — mechanism = forced tool-calling (ADR-005 Amendment 2). State/UX dims marked N/A (no UI). Consumed by /analyze-code-quality Dimension 8."

---

## How to Use This File

**Agents at awakening**: Loaded into session context automatically by `/map-orientation` (bare call). Reference entries by path when consulting orientation docs. Single-role project → all entries load.

**Agents at wrap-up**: If your session updated an orientation doc, `/map-orientation --session-touched [paths]` refreshes its `last_verified` + status. If a session DISCOVERED an entry's status is wrong, correct it via `/update-project-context`.

**Humans reviewing**: Spot-check `verified_by` and `update_trigger`; correct any auto-guessed scope/roles.
