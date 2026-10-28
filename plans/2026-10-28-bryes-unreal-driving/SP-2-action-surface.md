# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES
- **Date**: 2026-10-28
- **Agent**: Claude Software Architect
- **Theme**: SP-2 of the Unreal-driving council — the action surface (delta drag, a pointer aimed by pixel, proof a drop landed) and host reachability (a named window selects the body, and the host frame is the target's monitor).
- **Source Protocol**: `/high-wizard` — /high-wizard

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **INHERITED CONTEXT**
*Filled at investigation step 0 with whatever was settled before this plan existed. The two sources are recorded separately and never merged — write "None" under a part that does not apply.*
*These decisions are **not yours to reopen**. If one looks wrong, STOP and surface it to [USER-NAME] — do not silently re-decide it here or in Confirmed Decisions below.*

### From the Parent Plan
- **Parent plan**: `plans/2026-10-28-bryes-unreal-driving/core-plan.md`
- **Assigned scope**: R9 and R10 (host reachability and frame scope), then R3, R4 and R6 (delta drag, pointer by absolute pixel, proof a drop landed). Produces contracts C-2 and C-3.

| # | Inherited decision | Chosen | Parent's reason | Status |
|---|--------------------|--------|-----------------|--------|
| 1 | The empty drop point | A delta drag: `destination` may be an offset from the located start | Alvi answered "2. A"; a graph canvas is a coordinate space, so a delta is meaningful there while a second description of empty space is a guess the loop cannot detect. Measured since: locate() scored 0/6 on empty-canvas requests, so the model cannot answer a request for nothing | Settled |
| 2 | Pointer by absolute pixel | The agent must be able to drive the mouse by pixel position, not only by a described target | His words: "I want the agent to be able to drive the mouse by position in pixels" | Settled |
| 3 | The host body becomes reachable a new way | A named window selects the body, a host run with no window is refused, and `profiles/index.md` gains its `windows` section (that last part is SP-4's) | His call on option B: the catalog should carry the app knowledge, so a caller does not have to remember a profile path, while the window is what decides the desktop is in play. The refusal closes a hole measured in the code: `_ensure_foreground` and `_require_inside_target` both return early with no target, so a windows run without a window clicks the whole desktop unchecked | Settled |
| 4 | The host frame | The monitor holding the target window, resolved by `MonitorFromWindow`, read at capture time rather than cached | His words: "the WindowsDevice.screenshot() should only screenshot that only monitor". Measured: two screens, and the layout moved between two probes in one session, so any cached rect is already wrong | Settled |
| 5 | Where the Unreal API channel sits | A capability on the same body, gated like `shell` | Chosen at council decision 3; it is SP-3's, but it constrains the action contract this plan produces | Settled |

- **Integration contracts**: **produces** `contracts/action-contract.schema.json` (C-2) and `contracts/run-invocation.schema.json` (C-3). Consumes the C-1 measurement (already delivered: headers 2/3, pins 1/5, tiles 6/6).
- **Pushed-down open items**: how the Brain is told when to use a coordinate instead of a description; whether a drag's verification is automatic or Brain-driven; whether the pointer verbs are new vocabulary or a field on existing verbs.

### From Pre-Planning Discussion
- **Discussion**: None separate from the parent discussion; it is recorded above in the council plan.
- **Agreed scope**: None

| # | Settled decision | Chosen | His reason | Status |
|---|-------------------|--------|------------|--------|
| — | — | — | — | — |

- **Considered and rejected**: None
- **Left open**: None

---

## **OBJECTIVES**
Let the body be aimed at a pixel, let a drag end at an offset instead of a description, catch a drag that landed somewhere else, and make the host body reachable by naming a window while refusing to run without one.

### **Related Documents**
- [core-plan.md](core-plan.md) - the council; this plan owns R9, R10, R3, R4, R6
- [contracts/action-contract.schema.json](contracts/action-contract.schema.json) and [contracts/run-invocation.schema.json](contracts/run-invocation.schema.json) - produced here
- [SP-1-grounding-measurement.md](SP-1-grounding-measurement.md) - the numbers that decided pins go through the API

### **SUCCESS CRITERIA**
- [ ] A named window selects the host body, and a host run with no window is refused before any action
- [ ] The host frame is the target's monitor, and `caps` reports that frame rather than the desktop
- [ ] A drag can end at `destination_offset`, with no second locate
- [ ] `move_to` and `click_at` are offered as verbs and act at a coordinate without a description
- [ ] A drag automatically produces a before/after diff on the next step
- [ ] Every rule above has a model-free test, and the existing suites stay green

---

## **SCOPE**

### In Scope
- `devices/windows.py`: the monitor frame, the frame origin, and `caps` sized to the frame.
- `agent/loop.py`: window-selects-body, the refusal, the delta drag branch, the post-drag diff.
- `devices/base.py` and `brain/client.py`: the two pointer verbs and their prompt rule.
- `api/server.py`: `window` accepted as the body selector.
- Tests: `devices/test_host_frame.py` plus updates to the suites whose assumptions this reverses.

### Out of Scope
- The Unreal API channel, which is SP-3.
- The profiles, which are SP-4.
- Any change to `locate()` or its model.
- Making the pointer verbs available on the phone or container bodies beyond what they already accept (they take x and y already, so they inherit them for free).

---

## **CONFIRMED DECISIONS**
*Decisions made **by this plan** — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A and B decisions made by the agent, recorded with their reasoning).*
*Decisions settled before this plan existed belong in [INHERITED CONTEXT](#inherited-context) above, not here.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | How a coordinate reaches the pointer | Two new verbs, `move_to` and `click_at`, taking `x` and `y`, advertised through `Capabilities` | Alvi chose A. A verb is the unit this Brain reasons in, and `_actions_for` already offers only what a body advertises, so the verbs are filtered per body for free. Aiming by description keeps working unchanged |
| 2 | What proves a drag landed | The loop requests the before/after diff itself when the action was a drag | Alvi chose A. A misplaced wire is the most expensive silent failure here, and a drag is the one action whose failure still changes the screen. One extra vision call per drag is affordable because a build contains few drags |
| 3 | Where the no-window refusal lives | `_make_device`, the one place a run builds a host body | That is the single point every run-built host body passes through, so one check covers the picker, a forced profile and a named device. `capture.py` builds `WindowsDevice` directly and keeps working, which is the boundary R9 asks for |
| 4 | What `caps` reports | The frame's size, resolved live from the target's monitor | `brain/client.py` tells the Brain "a WxH pixel screen". With R10 the frame is the monitor, so the advertised size had to follow it or the Brain would be told the wrong image size |
| 5 | The frame origin | The frame rect's own corner, read per action | The image is the frame, so the translation is `frame.left + x`. A vanished target raises instead of silently falling back to the desktop, because a silent frame change keeps every coordinate valid in the wrong space |

---

## **SOLUTION**

### Architecture Overview
Two layers move. The body decides what it looks at and where a coordinate lands: one frame rect, one origin, one `caps` that describes it. The loop decides what the Brain may ask for: a window may select the body, a drag may end at an offset, a coordinate may be aimed directly, and a drag asks for its own proof. Nothing above the loop changes, and the API gains one accepted field.

### Component 1: The frame and the origin
- **Purpose**: hand the Eyes one monitor instead of the whole desk, and map its pixels back exactly.
- **Key Files**: `devices/windows.py` (`monitor_rect`, `_frame_rect`, `_desktop_rect`, `screen_xy`, `caps`), `devices/test_host_frame.py`

### Component 2: The action surface
- **Purpose**: let the Brain aim a coordinate, drop at an offset, and hear about a drag that went wrong.
- **Key Files**: `agent/loop.py`, `brain/client.py`, `devices/base.py`, `devices/windows.py`, `devices/test_host_frame.py`, `devices/test_windows_drive.py`

---

## **IMPLEMENTATION PHASES**

### Phase 1: Host reachability and the frame
- [ ] **Step 1.1**: The frame is the target's monitor
  - **Action**: Add `monitor_rect(hwnd)` and make `screenshot()`, `screen_xy()` and `caps` agree on one rect.
  - **Implementation**: `MonitorFromWindow` + `GetMonitorInfoW`; `_frame_rect()` raises when a named target vanished; `_desktop_rect()` stays live for the no-target case; `caps` is a property built with `dataclasses.replace`.
  - **Testing**: `python devices/test_host_frame.py` with injected geometry; `python devices/test_windows.py`.
  - **Success Criteria**: frame, caps and origin all follow the monitor; a vanished target raises.

- [ ] **Step 1.2**: A window selects the body, and no window is refused
  - **Action**: `run(window=...)` resolves to the host body; `_make_device("windows")` without a target refuses.
  - **Implementation**: window implies `device="windows"` when neither device nor profile was named; the forced-profile path forwards `window`; the refusal sits in `_make_device`.
  - **Testing**: `python agent/test_run_selection.py`, `python devices/test_host_frame.py`.
  - **Success Criteria**: the window alone selects the host; no window fails with a readable message naming the window.

### Phase 2: The action surface
- [x] **Step 2.1**: Delta drag
  - **Action**: Accept `destination_offset` on a drag and act at `start + delta`.
  - **Implementation**: loop branch beside the two-locate drag; bodies take `x2`, `y2` as computed, so no body change.
  - **Testing**: extend `devices/test_windows_drive.py` with a delta drag and assert the translated endpoints.
  - **Success Criteria**: one locate instead of two, and the release point is exact.

- [x] **Step 2.2**: Pointer aimed by pixel
  - **Action**: Add `move_to` and `click_at` to the vocabulary.
  - **Implementation**: `ALL_VERBS` plus the bodies' advertised sets; the loop's act branch skips `locate`; the Brain schema gains `x`/`y` with a prompt rule saying when a coordinate beats a description.
  - **Testing**: model-free vocabulary test plus a fake-input drive test.
  - **Success Criteria**: a coordinate action reaches the device with no `locate` call.

- [x] **Step 2.3**: A drag proves itself
  - **Action**: After a drag, the loop asks for the diff on the next step.
  - **Implementation**: set `want_diff` when the last action was a drag and the screen changed, without overriding a Brain request.
  - **Testing**: a model-free test that the flag is set for drags and not for clicks.
  - **Success Criteria**: a drag always produces `CHANGES SINCE YOUR LAST ACTION`.

---

## **EXECUTION LOG**
**Execution Protocol for AI**:
I have to use this document as my **ONLY** source of truth to execute and track the plan steps iteratively. I should **NOT** use additional tools like ToDos because it lacks the context of what should I do.

**Definition of Done (applies to ALL steps)**:
- ✅ **Code Quality**: Code compiles/runs without errors
- ✅ **Testing**: Tests written and passing
- ✅ **Logged**: Implementation and testing logged below
- 🚫 **Blocked**: Get input from [USER-NAME] before assuming

### Phase 1:
- [x] **Step 1.1**: The frame is the target's monitor
  - **Implementation Log**: `monitor_rect(hwnd)` added (`MonitorFromWindow` + `GetMonitorInfoW`); `_frame_rect_or_none` / `_frame_rect` / `_desktop_rect` added; `screen_xy` now adds the frame's corner; `screenshot()` grabs the frame rect; `caps` became a property sized to the frame via `dataclasses.replace`. `_origin_xy` kept for the no-target desktop rect.
  - **Testing Log**: `devices/test_host_frame.py` green on all four rules (frame, caps, origin, vanished target). `devices/test_windows.py` green after its old "naming a window must not crop" assertion was replaced by "a named-but-missing window raises".
  - **Success Criteria**: Pass.
  - **Tech Debts**: `WINDOWS_CAPS` still carries the virtual-desktop size as a fallback for the no-target case, which is correct for capture but means `caps` is only the frame size when a target exists.
  - **Result**: One frame rect, one origin, one advertised size.

- [x] **Step 1.2**: A window selects the body, and no window is refused
  - **Implementation Log**: `run()` resolves `window` to `device="windows"` when neither device nor profile was given, and the forced-profile path now forwards `window`; `_make_device` refuses a windows body with no window; `api/server.py` accepts `window` alone and rejects contradictions with a device or a profile.
  - **Testing Log**: `agent/test_run_selection.py` ALL PASS after its old refusal assertion was rewritten (a window now selects the body, and the gate is what refuses); `devices/test_host_frame.py` covers the refusal directly.
  - **Success Criteria**: Pass.
  - **Tech Debts**: The API's `window` + `profile` check reads the profile paths as strings only; it does not resolve them, and `run()` does that afterwards.
  - **Result**: `{goal, window}` is a valid invocation, and `{goal}` cannot reach the desktop.

### Phase 2:
- [x] **Step 2.1**: Delta drag
  - **Implementation Log**: `drag_endpoint(action, start)` added; the drag branch locates the start once, then releases at `start + destination_offset` when an offset is given, and falls back to the second locate only for a named `destination`. `BrainAction` gained `destination_offset` (`DragOffset` with `dx`/`dy`), and the prompt says to use it when the release lands on empty space.
  - **Testing Log**: `agent/test_drag_and_pointer.py` — offset math, zero offset, negative delta, and three malformed offsets each refused with a message.
  - **Success Criteria**: Pass. One locate instead of two, and the release point is exact.
  - **Result**: A canvas drop is a delta, which is the only form the measurement supports.

- [x] **Step 2.2**: Pointer aimed by pixel
  - **Implementation Log**: `_COORD_VERB` maps `move_to` -> the body's `hover` and `click_at` -> its `click`; a loop branch acts at `x`/`y` without calling `locate`; `_actions_for` DERIVES both verbs from the pointer a body advertises, so a phone gets `click_at` only and a body with no hover never sees `move_to`; `BrainAction` gained `x`/`y`; the prompt gained both actions and one rule saying to use a pixel only when it is already known.
  - **Testing Log**: `agent/test_drag_and_pointer.py` — desk/phone/blind vocabularies, the full-vocabulary case lists it once, and the two branches land on `hover`/`click`.
  - **Success Criteria**: Pass at the rule level. No live run has clicked a real desktop by pixel yet.
  - **Result**: The Brain can aim a pixel; the body still only ever receives its own verbs.

- [x] **Step 2.3**: A drag proves itself
  - **Implementation Log**: `wants_diff(action, after_drag)` added; a completed drag sets `diff_after_drag`, which the next step ORs into `want_diff` and then clears, so a drag always produces `CHANGES SINCE YOUR LAST ACTION` and the Brain's own `request_diff` still works.
  - **Testing Log**: `agent/test_drag_and_pointer.py` — the false/true matrix, including "the Brain asks for false but the drag happened".
  - **Success Criteria**: Pass.
  - **Tech Debts**: The flag is proven as a rule, not in a run. A failed drag raises before the flag is set, which is intended, but that path has no test.
  - **Result**: A drag cannot be silently wrong without a report saying what changed.

---

## **QUALITY REVIEW**
*Filled by procedure Step 16 after all execution phases are complete. **Static** review — answers "is the code clean?".*

- **Scope**: [Files reviewed]
- **Quality Standard**: [quality-standard.md found / not found]
- **Findings**: [Issues found, or "No findings"]
- **Fixed**: [What was fixed, or "N/A"]

---

## **QA HANDOFF**
*Filled by procedure Step 17. This plan is **not** runtime-verified.*

- **Scope**: [Modules touched]
- **QA instrument**: [Set up / NOT SET UP]
- **Integration coverage**: [Filled at Step 14]
- **Checklist**: [path, or "none — skipped, reason"]
- **Coverage split**: [N automated / N manual]
- **Runtime verification**: **NOT DONE.** Next action: [...]

---

## **POST-COMPLETION**
After all phases are executed, logged, and both **Quality Review** + **QA Handoff** are filled, move this plan to `plans/completed/`.
