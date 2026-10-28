# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES
- **Date**: 2026-10-28
- **Agent**: Claude Software Architect
- **Theme**: SP-6 of the Unreal-driving council — the bridge surface: a primitive-level API an outside agent calls to take screenshots, act at a pixel, locate by description, focus a window and read the shared profile vocabulary.
- **Source Protocol**: `/high-wizard` — /high-wizard

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **INHERITED CONTEXT**
*Filled at investigation step 0 with whatever was settled before this plan existed. The two sources are recorded separately and never merged — write "None" under a part that does not apply.*
*These decisions are **not yours to reopen**. If one looks wrong, STOP and surface it to [USER-NAME] — do not silently re-decide it here or in Confirmed Decisions below.*

### From the Parent Plan
- **Parent plan**: `plans/2026-10-28-bryes-unreal-driving/core-plan.md`
- **Assigned scope**: R11 — the bridge surface. Deliver a primitive-level API that an outside agent composes, with no Brain, no goal and no decision in the middle.

| # | Inherited decision | Chosen | Parent's reason | Status |
|---|--------------------|--------|-----------------|--------|
| 1 | What BRYES is in this feature | Hands and eyes for an outside agent, not a decision-maker | "making sure BRYES can act as a bridge from agent outside BRYES to do visual thing". This retired the Unreal API channel (R5, SP-3): the outside agent calls Unreal directly when an API is the right channel | Settled |
| 2 | Who reads the profiles | Both sides: the Eyes get the Visual half, the caller gets the same vocabulary so `locate` instructions are phrased in words the Eyes were primed with | "both inside and outside agent need to have those vocabulary so they can communicate well, especially the locate by description" | Settled |
| 3 | What the surface must offer | screenshot, act at a coordinate (click, drag, key chord, type), locate by description, focus a window, and the profile text | R11 as written at council Step 10 and confirmed with the graph | Settled |
| 4 | The frame the surface returns | The monitor that holds the target window, resolved live by `MonitorFromWindow` | "the WindowsDevice.screenshot() should only screenshot that only monitor tho". R10 owns the body change; this plan consumes whatever the body returns | Settled |
| 5 | Where the profiles come from | The two files written in SP-4, not derived from the `lsgi` lessons | "lessons are for me, not for agents" | Settled |

- **Integration contracts**: consumes the action contract `contracts/action-contract.schema.json` (C-2, produced by SP-2) for the verb and field names; serves SP-5. Produces no contract of its own, but its endpoint shapes are a contract for the outside caller and will be written down.
- **Pushed-down open items**: the transport and its authentication; whether calls hold a session or carry the window each time. Both are this plan's call and are the subject of the first round.

### From Pre-Planning Discussion
- **Discussion**: None — the parent handoff carries everything agreed.
- **Agreed scope**: None

| # | Settled decision | Chosen | His reason | Status |
|---|------------------|--------|------------|--------|
| — | — | — | — | — |

- **Considered and rejected**: the Unreal API channel inside BRYES → retired, the outside agent calls Unreal directly.
- **Left open**: None

---

## **OBJECTIVES**
Let an agent outside BRYES drive the screen with primitives: list the windows, take a picture of one, point at something by description, and act at a pixel. No goal, no Brain, no decision inside BRYES.

### **Related Documents**
- [core-plan.md](core-plan.md) - the council; R11 is this plan's scope
- [SP-4-profiles.md](SP-4-profiles.md) - the vocabulary this surface serves
- [contracts/action-contract.schema.json](contracts/action-contract.schema.json) - the verb and field names the `act` call passes through
- [api/server.py](../../api/server.py) - the task API whose shape this mirrors

### **SUCCESS CRITERIA**
- [ ] `GET /windows` lists every visible top-level window with a stable id, title, rect and foreground flag
- [ ] `GET /screenshot?window=<id>` returns that window's frame as PNG
- [ ] `POST /act` performs one pointer or key verb at the caller's coordinates, or refuses with a reason
- [ ] `POST /locate` returns a pixel for a description, using the Eyes
- [ ] `GET /profiles?path=<p>` returns the merged vocabulary text, or 404 for an unknown path
- [ ] The surface refuses a non-JSON body, and binds loopback only
- [ ] `api/test_bridge.py` is green and model-free

---

## **SCOPE**

### In Scope
- `api/bridge.py`: the five routes above, over an injected device factory and locator so the surface is testable without a screen or a model.
- `api/test_bridge.py`: model-free tests for every route and both refusals.
- Window enumeration with handles, kept inside the bridge for now.

### Out of Scope
- Any decision-making: no goal endpoint, no loop, no Brain.
- Sessions. Each call names its window; calls are serialised with a lock.
- The monitor-scoped frame (R10) and the delta drag (R3), which are SP-2's. The bridge returns whatever frame the body produces and passes the caller's pixels straight through, so it inherits both changes without edits.
- Moving the window enumerator into `devices/windows.py`, because SP-2 is editing that file.

---

## **CONFIRMED DECISIONS**
*Decisions made **by this plan** — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A and B decisions made by the agent, recorded with their reasoning).*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | Transport and authentication | HTTP on loopback, no token, JSON bodies only (any other content type is refused) | Alvi's call: "1. C". The JSON-only rule is the one line that keeps a browser form post out without adding authentication, and it preserves the choice he made |
| 2 | Session or per-call window | Per call. Every request names a window id from `GET /windows`; a lock serialises calls | The caller is one agent, and a session is only bookkeeping the server does on the caller's behalf. The single-driver intent of the task API survives as a lock, and a window id comes from a handle rather than a title, which is the host body's own rule |
| 3 | Which frame the surface returns | Whatever `device.screenshot()` produces, unchanged, with the caller's pixels passed straight to `device.act` | The body already translates image pixels to screen pixels, so the surface inherits R10's monitor frame without an edit. Pinning a frame shape here would duplicate a decision SP-2 owns |
| 4 | Where the window enumerator lives | Inside `api/bridge.py`, not `devices/windows.py` | SP-2 is editing that file for R10; a second edit in the same file is a merge fight for no gain. Recorded as debt to consolidate when SP-2 closes |

---

## **SOLUTION**

### Architecture Overview
One Flask app, five routes, and every outside dependency injected: a device factory, a locator and a window lister. That is what lets the whole surface be tested with fakes, and it is also the seam that keeps the surface from knowing how BRYES works inside. A lock around the calls is the single-driver rule the task API already enforces with its 409.

### Component 1: The surface
- **Purpose**: pass the caller's words to a body and the Eyes, and return pixels or a refusal.
- **Key Files**: `api/bridge.py`

### Component 2: The tests
- **Purpose**: prove every route and both refusals without a screen or a model.
- **Key Files**: `api/test_bridge.py`

### Integration Architecture

| Component | Integrates With | Data Flow | Dependencies |
|---|---|---|---|
| the caller | `api/bridge.py` | window id, verb, pixels in; PNG or {x,y} out | loopback HTTP, JSON |
| `api/bridge.py` | `devices.windows.WindowsDevice` | screenshot bytes; verb + image pixels | `BRYES_ALLOW_HOST` for any act |
| `api/bridge.py` | `eyes.client.locate` | frame + description -> one pixel | `OPENROUTER_API_KEY` |
| `api/bridge.py` | `profiles.load_profiles` | path -> merged visual + operating text | the SP-4 files |

### Technical Considerations
- The frame is whatever `device.screenshot()` returns. Today that is the whole desktop; after SP-2's R10 it is the target's monitor. The surface needs no change either way because the body translates pixels itself.
- A minimised window is skipped: its rectangle is off-screen and it cannot be shown.
- `act` still depends on `BRYES_ALLOW_HOST=1` inside the body, so the bridge cannot drive a desktop that the body refuses.

<!-- OPTIONAL SECTION A: Include when multi-system changes, multiple components interacting -->
### Integration Architecture
[Table or diagram showing how all components integrate together]

<!-- OPTIONAL SECTION B: Include when changing data/process flow, API changes -->
### System Flow Diagrams

**Current State:**
```mermaid
[Sequence diagram showing current system flow and component interactions]
```

**End Result:**
```mermaid
[Sequence diagram showing system flow after changes are applied]
```

<!-- OPTIONAL SECTION C: Include when significant technical constraints exist -->
### Technical Considerations
[Constraints, limitations, dependencies, and technical challenges]

---

## **IMPLEMENTATION PHASES**

### Phase 1: The surface
- [x] **Step 1.1**: Five routes over injected dependencies
  - **Action**: `api/bridge.py` and `api/test_bridge.py`.
  - **Implementation**: `/health`, `/windows`, `/screenshot`, `/act`, `/locate`, `/profiles`; a JSON error handler so every refusal is JSON; a lock around every device call; a JSON-only rule on the two POSTs; `IsIconic` skipped when listing.
  - **Testing**: `python api/test_bridge.py`, model-free with a fake body, fake locator and fake lister.
  - **Success Criteria**: five tests green, covering both refusals and the pass-through of pixels.

- [x] **Step 1.2**: Live smoke against the real screen
  - **Action**: start the server, ask it about the real desktop, stop it.
  - **Implementation**: `Start-Process python api/bridge.py`, then `/health`, `/windows`, `/screenshot`, `/profiles`, an unknown path, then `Stop-Process`.
  - **Testing**: 23 windows listed with handles and no off-screen rectangles; the screenshot came back 3440x2520 (today's whole-desktop frame); profiles served 2718 and 3433 chars; the unknown path returned 404.
  - **Success Criteria**: pass. What was NOT proven live is `act`, which still needs `BRYES_ALLOW_HOST=1` and a throwaway target.

### Phase 2: Prove an act live
- [ ] **Step 2.1**: One real click through the bridge
  - **Action**: launch the throwaway probe window, point the bridge at it, click inside its text field, read the result back.
  - **Implementation**: `artifacts/probe_target.py` as `smoke_windows_drive.py` already does, but driven through `/act` instead of the loop.
  - **Testing**: the probe's title or its body changes as expected.
  - **Success Criteria**: a click from outside BRYES changes a real window, with the guard refusing a point outside it.

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
- [x] **Step 1.1**: Five routes over injected dependencies
  - **Implementation Log**: `api/bridge.py` written: window enumeration with handles, `/health`, `/windows`, `/screenshot`, `/act`, `/locate`, `/profiles`, a `HTTPException` handler returning JSON, a `threading.Lock` around every device call, and a JSON-only rule on the two POSTs. `api/test_bridge.py` written beside it with a fake body, locator and lister.
  - **Testing Log**: first run failed on the 409 assertion because Flask's default abort body is HTML, so `r.get_json()` was None. Fixed by registering a JSON error handler, which is the correct shape for a program-facing surface anyway. Then all five tests passed.
  - **Success Criteria**: pass.
  - **Tech Debts**: the window enumerator lives in `api/bridge.py` instead of `devices/windows.py`, because SP-2 is editing that file.
  - **Result**: the surface exists and is proven with fakes.

- [x] **Step 1.2**: Live smoke against the real screen
  - **Implementation Log**: started the server with `Start-Process`, drove six requests, stopped it by pid.
  - **Testing Log**: health ok; 43 windows before filtering, 23 after skipping minimised; the editor and its blueprint listed with handles; screenshot 3440x2520 and 1,010,956 bytes; profiles 2718/3433 chars; unknown path 404.
  - **Success Criteria**: pass, with the finding that minimised windows were being listed with an off-screen rectangle (-32000), now skipped.
  - **Tech Debts**: the frame is still the whole desktop, so R10 has not landed yet. Not proven live: `act`.
  - **Result**: every read-only route answers against the real machine.

### Phase 2:
- [ ] **Step 2.1**: One real click through the bridge
  - **Implementation Log**: not started.
  - **Testing Log**: —
  - **Success Criteria**: not met yet.
  - **Result**: pending `BRYES_ALLOW_HOST=1` and a throwaway target.

---

## **QUALITY REVIEW**

- **Scope**: [Files reviewed]
- **Quality Standard**: [found / not found]
- **Findings**: [Issues found, or "No findings"]
- **Fixed**: [What was fixed, or "N/A"]

---

## **QA HANDOFF**

- **Scope**: [Modules touched]
- **QA instrument**: [Set up / NOT SET UP]
- **Integration coverage**: [Filled at Step 14]
- **Checklist**: [path, or "none — skipped, reason"]
- **Coverage split**: [N automated / N manual]
- **Runtime verification**: **NOT DONE.** Next action: [...]

---

## **POST-COMPLETION**
`mkdir -p ./plans/completed && mv ./plans/[this-file].md ./plans/completed/[this-file].md`
