# ADR-009: A host body that acts on the real Windows desktop, behind two gates

**Date**: 2026-10-21

**Status**: Accepted

---

## Problem

BRYES could only inhabit a disposable Docker desktop or an Android phone. Everything it might want to
operate on the real machine (Unreal Editor first, Aquazone's forms next) lives outside both, so the
project's central capability had no surface to act on where the actual work happens.

The obvious fix, a Windows body with pointer and keyboard verbs, carries a risk the other bodies do
not: a container is disposable and the host is not. An agent that can move the real pointer can also
click the wrong thing, and the localhost task API has no authentication, so "any local process can
start a run" becomes "any local process can drive the desktop".

---

## Decision

**We decided to**: add a driving `WindowsDevice` whose reach is gated twice, and whose coordinates
are translated from the image space the Eyes produce to the screen space the OS consumes.

A run reaches the host only by naming it (`device="windows"`) **and** running in a process with
`BRYES_ALLOW_HOST=1`. The body is never listed in the profile catalog, so the auto-picker cannot
choose it from a goal. `shell()` has its own switch, `BRYES_ALLOW_HOST_SHELL=1`, because arbitrary
command execution and a misjudged click are different classes of mistake. Capture is not gated:
`WindowsDevice.screenshot()` works with both switches off, which is what the lesson pipeline needs.

**Why we chose this:**
- The container stays the default, so an unqualified `run(goal)` is exactly as safe as it was
  yesterday; reaching the host is a decision someone typed.
- Two gates, because a click can be undone by noticing it and `Remove-Item -Recurse` cannot.
- The coordinate translation is one function reading the live virtual origin, because the origin is
  not zero on every desk: measured as (0,−1080) with a monitor above the primary, and (0,0) after the
  layout changed in the same session.

---

## What to Build (Requirements)

**Core Requirements:**
- `devices/host_input.py`: a thin adapter over `pyautogui`, the only module that touches it, with an
  injectable seam so `act()` is testable without moving the real mouse
- `WindowsDevice` gains `act()`, `clear_field()`, `type_into()`, `screen_xy()` and a gated `shell()`
- `_ROOT_DEVICE["windows"]`, a fail-fast gate in `_make_device`, and a `window` parameter on `run()`
  and `POST /tasks`, passed to the body and nowhere else
- Both gates proven by tests, and one live smoke run that drives Unreal for a single step

**Success Criteria:**
- A real click lands where the screenshot said, verified by the next frame differing
- Host targeting and host shell each refuse with their variable unset, proven by a test
- `resolve_embodiment` can never return `windows`
- The container and phone suites pass unchanged

---

## Consequences, and what this does not solve

The gates are a **stopgap, not the boundary**. They exist because BRYES currently runs as the
same Windows user who owns the documents and applications on this machine, so the only thing
between an agent and a real document is permission. The structural answer is environment
isolation: run the harness under its own user session, where the desktop holds only what the task
created, and the question "did it click my document" stops existing rather than being guarded.

Two harness rules belong with the body regardless, because they hold even inside a sandbox:
target a window the body itself started (a handle, never a title substring, which matched the
largest window and drove someone else's editor), never kill a process the body did not create,
and refuse any pointer action outside the target's rect (the foreground guard proves the right
window is in front; it does not stop a coordinate that lands beside it). All three were learned
the hard way on 2026-10-21.

---

## Alternatives Rejected

- **Writing the input layer ourselves (ctypes `SendInput`)**: reinvents a maintained library, and the
  maintenance would be ours.
- **Hardware HID (a Pico or Arduino as a real keyboard/mouse)**: measured unnecessary, since
  `pyautogui` and `pynput` both reached every monitor; it costs a device to solve a problem this desk
  does not have.
- **UI Automation / element-level control**: the right answer where an app publishes an accessibility
  tree, and unmeasured for Unreal's Slate UI; deferred behind a probe rather than guessed at.
- **Adopting Windows-MCP as the body**: it is a whole agent-side server, so adopting it replaces
  BRYES's loop rather than filling one of its bodies.

---

**Full context**: [High Wizard plan](../plans/2026-10-20-bryes-host-body.md)
