# ADR-002: Device Interface — Swappable Vision-Controllable Bodies

**Date**: 2026-07-15

**Status**: Accepted

---

## Problem

BRYES's perceive→decide→act loop is hard-wired to a single body: `agent/loop.py` calls `screenshot()` / `hands()` / `exec_cmd()`, each an HTTP request to one specific Screen container at `localhost:8000`. But the agent's mind (loop + Brain + Eyes) is inherently body-agnostic — it reasons over a screenshot and emits an action. To let the agent inhabit other bodies (an Android phone, a Windows desktop) we must stop coupling the loop to one transport. The bodies genuinely differ (a phone has no right-click, has Back/Home, portrait coordinates, an Android shell), so a naive "same methods" swap would flatten those differences and break.

---

## Decision

**We decided to**: extract the Screen + Hands + shell into a swappable **`Device`** abstraction — a *vision-controllable body* — that the loop depends on, with a per-device **`Capabilities`** manifest that makes each body's differences first-class.

A `Device` exposes `screenshot() -> bytes`, `act(action) -> None`, an optional `shell(...) -> dict`, and a `caps: Capabilities` (name, coordinate space, supported `verbs`, `has_shell` + `shell_flavor`, named `keys`). The loop, Brain, and Eyes are written once and stay device-agnostic; **transport is each device's private detail** (`ContainerDevice` speaks HTTP, `PhoneDevice` shells out to `adb`, a future `WindowsDevice` calls `mss`+`pyautogui` in-process). The Brain assembles its action vocabulary from the *active* device's `caps.verbs`, so it is only ever offered verbs the current body can perform. The Eyes are untouched — they already read the coordinate space from each screenshot, so any resolution works.

**Why we chose this:**
- Dependency inversion — the loop depends on an abstraction, not a transport; the mind is written once and every future body reuses it.
- The `Capabilities` manifest keeps "same interface, real differences" honest — the phone's missing `right_click` / added Back-Home / swipe-scroll are modeled, not flattened.
- Right timing, not premature: an interface earns its keep at the *second* implementation, and the phone is that real second body — so it is validated now, not guessed.

---

## What to Build (Requirements)

**Core Requirements:**
- A `devices/` package: `base.py` (`Device` Protocol + `Capabilities` dataclass), `container.py` (`ContainerDevice`, wrapping today's HTTP calls **byte-identically**), `phone.py` (`PhoneDevice`, over `adb`/USB).
- The loop depends on `Device`: `run(goal, device=None)` defaults to `ContainerDevice`; dispatch calls `device.screenshot()/act()/shell()`; the container path is unchanged in behavior (`test_hands.py` + `test_shell.py` stay green).
- The Brain's action vocabulary is assembled from the active device's `caps.verbs ∪ {wait, screenshot, done, fail} ∪ (shell if has_shell)`, with a device preamble injected into the prompt; the tuned prose is preserved.
- `PhoneDevice` maps verbs to `adb shell input` (tap/swipe/text/keyevent), `screencap` for perception, `adb shell` for Tier-2, and advertises phone `Capabilities` (1080×2400, no `right_click`/`hover`, Back/Home keys, `scroll`→swipe, `shell_flavor="android"`).
- **Boundary**: `Device` is only for *vision-controllable* bodies. Pure API/MCP channels (no screen) are explicitly NOT `Device`s — they are a separate effector abstraction (ADR-001's future Tier-1).

**Success Criteria:**
- The container task runs end-to-end through the `Device` abstraction with no regression.
- `PhoneDevice` drops in as the second device and the **unchanged** loop performs a real action on the physical phone — the interface is validated by a genuinely different body.
- A third body (`WindowsDevice`) could be added without touching the loop, Brain, or Eyes.

---

## Alternatives Rejected

- **Uniform HTTP contract for every device**: forces a server + port per body (heavy for `adb`, which is naturally a subprocess) — needless daemons the design doesn't need.
- **No abstraction (`if device_type == ...` in the loop)**: keeps the exact coupling we're removing and grows a device switch in `loop.py` — defeats the goal.
- **Full plugin/registry framework**: massive over-engineering for 2–3 known devices (YAGNI — the over-engineering trap).
- **ABC base class instead of a Protocol**: heavier (forces inheritance) for no gain at this size; a structural Protocol is enough.
- **Fold pure API/MCP channels into `Device`**: they have no screen — a `screenshot()` on them is meaningless; over-abstraction. They stay a separate (ADR-001 Tier-1) concern.

---

## Relationship to ADR-001

Orthogonal axes. [ADR-001](2026-07-15-effector-hierarchy.md) = which effector **tier** (API / shell / vision) the Brain uses for a given target. ADR-002 = which **body** the agent inhabits. They compose: a device's `Capabilities` expresses which tiers it offers (`has_shell` → Tier-2 available; `verbs` → Tier-3 vision surface).

---

**Full context**: [High Wizard plan](../../plans/2026-07-15-bryes-device-interface.md)
