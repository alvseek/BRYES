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
- **tags**: [screen, hands, docker, xvfb, xdotool, flask-api]
- **last_verified**: "2026-07-14"
- **verified_by**: "claude-software-architect"
- **update_trigger**: "when the Screen container stack, the /screenshot|/action API, or ports change"
- **notes**: "Phase 1 — the Screen+Hands: disposable Ubuntu container (Xvfb + fluxbox + xdotool + scrot) exposing screenshot + the full Hands action set (click/double_click/right_click/hover/scroll/drag/type/key) over a Flask API (:8000) with noVNC live view (:6080). Apps: gnome-calculator, xterm, Chrome (xcalc note fixed 2026-07-13)."

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
- **notes**: "Phase 4 — Close the Loop: agent/loop.py chains screenshot -> Eyes.describe -> Brain.decide -> Eyes.locate -> Hands act, until done/fail/step-limit. No verify-and-recover yet (that's Phase 5, the product)."

---

## How to Use This File

**Agents at awakening**: Loaded into session context automatically by `/map-orientation` (bare call). Reference entries by path when consulting orientation docs. Single-role project → all entries load.

**Agents at wrap-up**: If your session updated an orientation doc, `/map-orientation --session-touched [paths]` refreshes its `last_verified` + status. If a session DISCOVERED an entry's status is wrong, correct it via `/update-project-context`.

**Humans reviewing**: Spot-check `verified_by` and `update_trigger`; correct any auto-guessed scope/roles.
