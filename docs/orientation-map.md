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
- **last_verified**: "2026-10-23"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the four pieces (Screen/Eyes/Brain/Loop), setup, the task entry point (run()), the ADR list, the lesson pipeline, or the high-level architecture change"
- **notes**: "The root, GitHub-facing project README (7 Questions Framework) — the single project overview. Covers what BRYES is (Brain-Eyes vision computer-use agent), the CURRENT module coupling (the loop is the sole coupler — grounded on docs/modularity.mmd + docs/loop-dispatch.mmd), setup, how to give a task (run(goal) from Python), the per-step flow, the ADR-001..008 index, and known debts. Supersedes roadmap.md as the closest-to-root overview. Generated 2026-07-19 via /generate-readme. Updated 2026-10-20: a third body (WindowsDevice, capture-only, no pointer verbs) and the lesson pipeline (capture.py + lesson.py, procedure in docs/procedures/make-a-lesson.md) added to the architecture section. Updated 2026-10-23: `key_hold` added to the action set and the hands table, plus the two new regression commands (screen/test_action_payloads.py, agent/test_key_hold.py)."

### `roadmap.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: stale-but-valuable
- **tags**: [roadmap, phases, architecture, entry-point]
- **last_verified**: "2026-10-23"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when a phase is added/completed or the target architecture (4 pieces, verify step) changes"
- **notes**: "The milestone-driven build plan, handed to Claude Code one phase at a time (goal / build / test / trap per step). Kept as the record of the build sequence, not as current state: phases 0-5 are all built, Phase 6 was never forced, and its model names are two swaps behind (`DeepSeek V4` is now v4.1-flash; UI-TARS is still the grounder). Verified 2026-10-23 and left as-is deliberately: rewriting a completed plan to current models adds nothing. The project overview lives in the root `README.md`."

### `screen/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [screen, hands, shell, exec, docker, xvfb, xdotool, flask-api]
- **last_verified**: "2026-10-29"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the Screen container stack, the /screenshot|/action|/exec API, or ports change"
- **notes**: "Standalone Docker Linux desktop and HTTP control server on port 8000, with noVNC on 6080. Documents PNG response bytes, every input primitive including key_hold, shell results/timeouts, configuration, test commands, disposable state and security limits. The README refers only to Screen and its children, never sibling modules. Compose ports are not loopback-restricted and the screenshot handler leaves temporary files; documentation does not claim those limits are fixed."

### `eyes/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [eyes, grounding, ui-tars, openrouter, coordinates]
- **last_verified**: "2026-10-23"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the Eyes model, locate()/describe() signatures, or coordinate convention change"
- **notes**: "Phase 2 — the Eyes. Covers `locate()`: UI-TARS-1.5-7B grounding via OpenRouter (matches `GROUND_MODEL` in client.py), plus the smart_resize coordinate convention. Verified 2026-10-23 against the code, with one thing the file did not say added: the **describe** half arrived with the loop (ADR-004) and runs elsewhere — deepseek-v4.1-flash for fast overview/crop reads, qwen2.5-vl-72b for boxing, careful re-reads and diffs — so a reader does not mistake the Eyes for one model."

### `brain/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [brain, decider, deepseek, openrouter, json-action]
- **last_verified**: "2026-10-23"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the Brain model, decide() signature, or the action JSON shape change"
- **notes**: "Phase 3 — the Brain: DeepSeek V4.1 Flash (`deepseek/deepseek-v4.1-flash`) decider, rented and text-only in practice, with gemini-2.5-flash-lite as the last-attempt fallback. decide(goal, observation, history) -> one structured action naming its target by description; the Eyes ground the description to a pixel. Repaired 2026-10-23: the model line, the action schema (the full per-body verb set, not `click|type|key|done|fail`) and the answered Phase-4 question were all stale, and the module docstring in client.py said qwen3.6-flash."

### `agent/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: stale-but-valuable
- **tags**: [loop, orchestration, closed-loop, phase-4]
- **last_verified**: "2026-10-23"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the loop's step sequence changes or verify-and-recover (Phase 5) lands"
- **notes**: "Phase 4 — Close the Loop, as it was built: screenshot -> describe -> decide -> locate -> act, until done/fail/step-limit. Verified 2026-10-23 as a **historical record that no longer describes the loop**: it says no verify-and-recover exists (ADR-003 and ADR-007 shipped it), omits the `wait`/`screenshot`/`shell`/`type_into` actions and the findings ledger, and predates embodiment selection (ADR-006). A status banner now sits at its top pointing readers at agent-loop-flow.md, which is the current shape."

### `api/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: stale-but-valuable
- **tags**: [api, task-invocation, flask, async, http, jobmanager]
- **last_verified**: "2026-10-29"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when task endpoints, supported device/window parameters, or the JobManager lifecycle change"
- **notes**: "Task-Invocation API on port 8100: whole-goal submission and polling around the Brain-driven run loop. Bridge details have moved to api/README-Bridge.md, linked from this README. The original task API endpoint reference still omits Windows/window details; the current operator procedure distinguishes that path from direct Bridge driving."

### `api/README-Bridge.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [bridge, windows, http, screenshots, coordinates, external-agent]
- **last_verified**: "2026-10-29"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the Windows Bridge filename, routes, image headers, or runtime setup changes"
- **notes**: "Dedicated reference for api/bridge-windows.py on loopback port 8110, separated from the Task API README. Lists primitive routes including downscaleshot and upscaleshot and their coordinate mapping. The full safety and observe-act-verify workflow lives in docs/procedures/drive-the-desktop.md."

### `docs/architecture-overview.md`

- **type**: architecture-overview
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [architecture, layers, devices, brain, eyes, hands, actions, effector-tiers]
- **last_verified**: "2026-10-29"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when a layer, the Device abstraction, the Brain action set, or an effector tier changes"
- **notes**: "The single-section architecture deep-dive: the four pieces, the Device abstraction and its three bodies, the effector tiers, the full Brain action set, `type_into` as the device-level text gesture, and the two-mode foveal describe. Updated 2026-10-29 to split the two host HTTP surfaces it had previously conflated: the Brain-driven Task API on :8100 and the Windows Bridge on :8110, whose primitive routes include the downscaled and enlarged screenshots, with the screen/ container API on :8000 named as a third, separate surface."

### `docs/agent-loop-flow.md`

- **type**: flow-diagram
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [flow, loop, sequence, actions, verification, recovery, history]
- **last_verified**: "2026-10-23"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the per-step loop, the action dispatch, or the verification/recovery path changes"
- **notes**: "The loop as a sequence: screenshot → describe → decide → locate → act → verify, with the per-step component table, the BRAIN PROMPT blocks, the HISTORY and CONFIRMED FINDINGS rules, and the change-feedback rungs. Also carried the running list of what is still open. **Missing from this map until 2026-10-23.** Updated the same day: `key_hold` added to the action list and to the Hands payload contract."

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

### `docs/adr/2026-10-21-host-body-and-gates.md`

- **type**: adr
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [adr, host-body, windows, pyautogui, gates, safety, effector]
- **last_verified**: "2026-10-21"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the host body's gates or harness rules change, or when environment isolation lands"
- **notes**: "ADR-009 — a body that acts on the real Windows desktop. Reach requires `device=\"windows\"` AND `BRYES_ALLOW_HOST=1`; `shell` has its own switch; capture is ungated because the lesson pipeline builds the same body. Carries the measured evidence (virtual origin (0,−1080) on one desk then (0,0) after a display change; `pyautogui.FAILSAFE` must be off or a point beyond the primary raises instead of moving), the three harness rules that came from driving Alvi's own Notepad (target a handle you started, kill only what you started, act only inside the target rect), and the honest limit: **the gates are a stopgap, environment isolation is the structural answer**."

### `docs/procedures/make-a-lesson.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [procedure, lessons, tutorial, screenshots, capture, html, teaching]
- **last_verified**: "2026-10-20"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the lesson pipeline changes (capture.py flags, lesson.py step syntax, the gates, or where lessons are placed)"
- **notes**: "The tutorial-lesson procedure, also served as the `/make-lesson` skill (`.opencode/skills/make-lesson/SKILL.md` points here, deliberately carrying no copy of its own). Splits the work into instrument and author: BRYES captures labelled screenshots (`capture.py` -> `WindowsDevice`, capture-only, no pointer verbs) and builds one HTML page per lesson (`lesson.py`, which refuses a step whose shot is missing); the mentor writes the steps. Lessons live under `lessons/<project>-<nn>-<slug>/` with `lesson.md`, `shots/`, `capture-log.jsonl`, `lesson.html` and generated `assets/`. First two worked examples: `lsgi-01-editor-anatomy` and `lsgi-02-blueprint-editor`."

### `docs/procedures/drive-the-desktop.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [procedure, host-body, windows, driving, pyautogui, gates, adr-009]
- **last_verified**: "2026-10-29"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when Windows Bridge routes, coordinate mapping, input gates, or operator workflow change"
- **notes**: "Canonical /drive-desktop operator procedure, rewritten Bridge-first on 2026-10-29. Start api/bridge-windows.py on loopback 8110, select a verified window handle, read profiles, observe PNGs, map downscaled or enlarged crop coordinates, act and verify. Records that screenshots do not foreground targets, each shot is fresh, input success is not app success, JSON is not authentication, and Bridge has no shell route. Whole-goal Python/Task API delegation is an explicitly separate alternative. Global commands/skills are generated copies refreshed by setup-scripts."

### `grounding.py`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [grounding, measurement, eyes, locate, unrel, regression, snapshot-test]
- **last_verified**: "2026-10-28"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when locate()'s model changes, when the probe kinds change, or when a new app's grounding is measured"
- **notes**: "The snapshot grounding tester: one frame plus a labels JSON (kind, instruction, box in pixels), one `locate()` call per target, a hit when the point lands inside the box. Emits the council's measurement report (per-kind rate, median error, the model recorded) and an overlay that draws every box and every returned point. `--check-labels` draws the key and spends no model call, which is the step that caught the author's own mis-marked pins on 2026-10-28. Measured then on the Unreal editor: headers 2/3, pins 1/5, asset tiles 6/6, empty canvas 0/6. Model-free tests live in `test_grounding.py`; the numbers and the re-measure recipe are in [.agents/knowledge/grounding-measurement.md](../.agents/knowledge/grounding-measurement.md)."

### `setup-scripts/`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [installer, procedures, claude-code, opencode, bat, skills]
- **last_verified**: "2026-10-26"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when a procedure is added to or removed from `PROCEDURES` in `install_skills.py`, or when a platform's global command/skill directory changes"
- **notes**: "Installs `/drive-desktop` and `/make-lesson` globally so agents in OTHER projects (the Unreal agent in LSGI) can use them. `setup-all-claude-code.py` writes `~/.claude/commands/<name>.md`; `setup-all-opencode.py` writes `~/.config/opencode/skills/<name>/SKILL.md`; each has a `.bat` that only finds a real Python 3 (skipping the WindowsApps Store stub) and runs the `.py`. The shared `install_skills.py` copies the FULL procedure from `docs/procedures/` (the in-repo `.opencode/skills/` pointers resolve a relative path that does not exist from another project), rewrites relative links to absolute ones into the clone, and prepends a note naming the clone so its scripts can be run from there. The installed file is a generated copy: edit the procedure, then re-run the installer. A per-platform manifest (`.bryes-manifest`, `.bryes-opencode-manifest`) lets a re-run replace its own files without touching anything else. Override the target with `BRYES_TARGET_DIR`. Tested by `python setup-scripts/test_setup.py` (model-free, temp dirs only). Shape copied from `agent-memory-project/setup-scripts`."

### `docs/backlog.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [backlog, tech-debts, next-steps, qa, proofs]
- **last_verified**: "2026-10-23"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when an item is added, closed, or re-scoped"
- **notes**: "The living list of what is known-broken, planned, or unproven, split into next steps and tech debts. It is the honest counterpart to the README's claims: a capability whose app-level behaviour has never been watched lives here. Added to this map on 2026-10-23 (it was not indexed before), the same day its `key_hold` entry was written and then checked off with the live timings."

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
