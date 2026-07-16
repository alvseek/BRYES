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

### `roadmap.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [roadmap, phases, architecture, entry-point]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: "when a phase is added/completed or the target architecture (4 pieces, verify step) changes"
- **notes**: "The milestone-driven build plan, handed to Claude Code one phase at a time (goal / build / test / trap per step). Names the target: Brain+Eyes+Screen+Hands over HTTP, with verify-and-recover as the differentiator. The closest thing to a root overview — there is no root README.md yet."

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

---

## How to Use This File

**Agents at awakening**: Loaded into session context automatically by `/map-orientation` (bare call). Reference entries by path when consulting orientation docs. Single-role project → all entries load.

**Agents at wrap-up**: If your session updated an orientation doc, `/map-orientation --session-touched [paths]` refreshes its `last_verified` + status. If a session DISCOVERED an entry's status is wrong, correct it via `/update-project-context`.

**Humans reviewing**: Spot-check `verified_by` and `update_trigger`; correct any auto-guessed scope/roles.
