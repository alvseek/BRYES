# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES
- **Date**: 2026-10-28
- **Agent**: Claude Software Architect
- **Theme**: SP-5 of the Unreal-driving council — prove the bridge on a real Unreal Editor task, driven entirely from outside BRYES, and bring the procedures, the orientation map and the session record up to date.
- **Source Protocol**: `/high-wizard` — /high-wizard

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **INHERITED CONTEXT**
*Filled at investigation step 0 with whatever was settled before this plan existed. The two sources are recorded separately and never merged.*

### From the Parent Plan
- **Parent plan**: `plans/2026-10-28-bryes-unreal-driving/core-plan.md`
- **Assigned scope**: R7 (a real build proving the bridge) and R8 (the procedures, the map and the session record).

| # | Inherited decision | Chosen | Parent's reason | Status |
|---|--------------------|--------|-----------------|--------|
| 1 | What BRYES is in this feature | Hands and eyes for an outside agent; the outside agent decides | Council decision 9: BRYES exposes primitives and vocabulary, and holds no Brain in that path | Settled |
| 2 | The profiles | Shared vocabulary, read by the Eyes and by the caller | "both inside and outside agent need to have those vocabulary so they can communicate well, especially the locate by description" | Settled |
| 3 | The Unreal API channel | Dropped. Wiring has no exact channel through BRYES | Council decision 8: "SP-3 is dropped"; and the measurement put vision at 1/5 on pins | Settled |
| 4 | The bridge | Six routes, frame-space rectangles, no auth with a JSON-only rule, live-proven with a click and a keystroke | SP-6, committed and closed | Settled |
| 5 | The frame | The monitor holding the target window | R10, live: the probe's frame came back 1920x1080 | Settled |

- **Integration contracts**: consumes C-2's action fields through `/act`; produces no contract.
- **Pushed-down open items**: what this sub-plan can honestly prove, given that R7's three wires have no exact channel. That is the subject of the first round.

### From Pre-Planning Discussion
- **Discussion**: None — the parent handoff carries everything agreed.
- **Agreed scope**: None

| # | Settled decision | Chosen | His reason | Status |
|---|------------------|--------|------------|--------|
| — | — | — | — | — |

- **Considered and rejected**: None
- **Left open**: None

---

## **OBJECTIVES**
Prove the bridge on the real editor with a caller that is not BRYES: a scripted agent that opens the asset picker by shortcut, reads the screen, attempts three connections by hand and eye, verifies each with a diff, and records what held.

### **Related Documents**
- [core-plan.md](core-plan.md) - the council; R7 and R8 are this plan's scope
- [SP-6-bridge-surface.md](SP-6-bridge-surface.md) - the surface being proven
- [contracts/action-contract.schema.json](contracts/action-contract.schema.json) - the verbs `/act` forwards

### **SUCCESS CRITERIA**
- [ ] A caller outside BRYES lists the editor by handle and reads a screenshot of it
- [ ] `Ctrl+P` opens the asset picker and the screenshot shows it
- [ ] Three connections are attempted by hand and eye, each with a screenshot before and a diff after
- [ ] The compile runs and its result is read
- [ ] Whatever held is claimed and whatever did not is recorded per attempt, with the diff as the evidence
- [ ] The wiring gap and what would close it are written where the LSGI work lives
- [ ] `drive-the-desktop.md`, the orientation map and the session record are brought up to date

---

## **SCOPE**

### In Scope
- A scripted caller that talks only to the bridge (loopback HTTP), kept beside the bridge as a record of the technique.
- `Ctrl+P`, screenshots, `locate`, `act` drags, `request_diff`-style comparison through two screenshots.
- The compile, read back through a screenshot.
- The record: procedures, map, session log, and the wiring note.

### Out of Scope
- Saving the blueprint. Nothing in the user's asset changes, so an unsaved experiment cannot damage his work.
- C++ in `LSGIEditor`. That is the handoff, not this plan's build.
- BRYES's Brain. The whole point is that the caller decides.

---

## **CONFIRMED DECISIONS**
*Decisions made by this plan.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | What this sub-plan proves | A real editor task through the bridge AND the three wires attempted by hand and eye, each verified with a diff | Alvi's call: "we need wiring by hand and eye throught the bridge too. it means A+B then?" — so the wires stay the target and the claim follows the evidence |
| 2 | Whether the wiring gap is a handoff | Yes, but a smaller one: it records what the method achieved per attempt, plus the C++ entry point that would make it exact | The gap is real (no scripting path creates a node or connects a pin) but it is no longer the conclusion; the attempt is the deliverable and the gap is what it leaves behind |
| 3 | Whether anything is saved | No. The compile is run and read; the asset is not saved | An experiment on a real project asset should be reversible by doing nothing, and a saved-but-wrong blueprint is the failure nobody notices |

---

## **SOLUTION**

### Architecture Overview
[High-level system design and component interaction]

### Component 1: [Name]
- **Purpose**: [What problem it solves]
- **Key Files**: [Files to create/modify]

---

## **IMPLEMENTATION PHASES**

### Phase 1: [Name]
- [ ] **Step 1.1**: [Overview]
  - **Action**: [What to do]
  - **Implementation**: [How to do it]
  - **Testing**: [How to verify]
  - **Success Criteria**: [When it's done]

---

## **EXECUTION LOG**
**Execution Protocol for AI**:
I have to use this document as my **ONLY** source of truth to execute and track the plan steps iteratively.

**Definition of Done (applies to ALL steps)**:
- ✅ **Code Quality**: Code compiles/runs without errors
- ✅ **Testing**: Tests written and passing
- ✅ **Logged**: Implementation and testing logged below
- 🚫 **Blocked**: Get input from [USER-NAME] before assuming

### Phase 1:
- [ ] **Step 1.1**: Prove the bridge on the real editor
  - **Implementation Log**: bridge started on loopback; the editor listed (`frame` 1920x1080, `image_rect` -8..1928); a screenshot read; a right-click sent to empty canvas; a `type` and a menu-row click attempted; a slow stepped drag sent directly through pyautogui; a Compile click attempted.
  - **Testing Log**: right-click returned 200 and the menu opened. The `type` returned 200 but the menu was gone, and a click on a menu row did the same. The slow drag returned success at the OS level and the node did not move. The Compile click was refused with `could not bring the target window to the foreground after 3 attempts`.
  - **Success Criteria**: NOT met. No node was created, no wire was attempted, nothing was saved and the graph is unchanged.
  - **Tech Debts**: three separate unknowns, none resolved: (a) whether Slate ignores synthetic left-button input or the press is swallowed by window activation; (b) whether the bridge can ever hold focus, since Windows blocks `SetForegroundWindow` from a background process; (c) whether a menu can be driven at all, given every synthetic input closes it.
  - **Result**: blocked, with the cause measured rather than guessed.

  **What the run measured, in order**
  1. `GET /windows` and `GET /screenshot` are correct and useful: the editor, its monitor and its frame rectangle all come back right.
  2. A synthetic right-click OPENS the editor's context menu.
  3. Any subsequent synthetic input closes it: a typed character and a click on a menu row each dismissed it. So a node cannot be created through the menu.
  4. A press-move-release over a node's title bar, sent slowly and in steps, did not move the node.
  5. The focus guard refused a click after the editor lost focus, and Windows will not let the bridge's own process restore it.

  **The one code change this produced**: `foreground_is_target` in `devices/windows.py` now walks the owner chain rather than comparing handles. Measured: after a right-click the foreground window is an untitled `UnrealWindow` owned by the blueprint window, whose own owner is the main editor. The old equality test refused every action taken while a menu was open, and raising the window then dismissed the menu. Tested in `devices/test_windows_drive.py`.

- [x] **Step 1.2**: The run after the guard fix, and after the pointer restore
  - **Implementation Log**: with the owner-chain fix and `_ensure_pointer_in_frame` in place, a caller parked the pointer on the other monitor and drove the editor: a click to take the foreground, a right-click, typing `Pri`, typing `nt String`, Return, then three pin drags, a Compile click and one Ctrl+Z.
  - **Testing Log**:
    - Reaching the editor from the other monitor: pointer read `inside_frame: false`, the click returned 200, and afterwards the pointer was inside and the editor held the foreground.
    - The context menu DOES work: typing filtered the list (`Pri` showed Play Sound and friends) and Return created a `Print String` node on the canvas.
    - **Two of three wires landed**: `Event BeginPlay` → Print String exec, and `Event ActorBeginOverlap` → Print String exec, both visible as white wires.
    - **The third attempt missed and did something else**: the press landed on `Event Tick`'s node body rather than its pin, so the graph MOVED the node instead of wiring it. Caught by the next screenshot, undone with Ctrl+Z (`Undo: Move Node`).
    - Compile after the two wires: the Compile tooltip read `Good to go`. After the undo it read `Dirty, needs to be recompiled`.
    - Nothing was saved; the status bar reads `1 Unsaved`.
  - **Success Criteria**: A met for reach, screen reads and the compile. B met at 2 of 3 wires, with the third recorded as a miss.
  - **Tech Debts**: the third wire is unproven; a pin press within a few pixels of the body moves the node with no error, which is the silent failure R6 exists to catch, now measured rather than assumed.
  - **Result**: the method works. My earlier "blocked" reading was wrong, and the cause was the focus guard, not the menu.

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
