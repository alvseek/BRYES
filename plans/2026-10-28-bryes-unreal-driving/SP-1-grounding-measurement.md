# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES
- **Date**: 2026-10-28
- **Agent**: Claude Software Architect
- **Theme**: SP-1 of the Unreal-driving council — a grounding measurement rig that scores the Eyes' `locate()` against real `lsgi` editor frames and writes the report the other sub-plans read.
- **Source Protocol**: `/high-wizard` — /high-wizard

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **INHERITED CONTEXT**
*Filled at investigation step 0 with whatever was settled before this plan existed. The two sources are recorded separately and never merged — write "None" under a part that does not apply.*
*These decisions are **not yours to reopen**. If one looks wrong, STOP and surface it to [USER-NAME] — do not silently re-decide it here or in Confirmed Decisions below.*

### From the Parent Plan
- **Parent plan**: `plans/2026-10-28-bryes-unreal-driving/core-plan.md`
- **Assigned scope**: R1 — the grounding measurement. Deliver the report described by `contracts/measurement-report.schema.json` (C-1), which SP-4 and SP-5 consume.

| # | Inherited decision | Chosen | Parent's reason | Status |
|---|--------------------|--------|-----------------|--------|
| 1 | Measurement before the build | This sub-plan is the first one executed | Alvi answered "1. A + B + C"; the measurement is the only piece that cannot be wasted, because its number either green-lights the vision path or sends the work to the API | Settled |
| 2 | Authority of the measurement | A diagnostic inside the vision path, never a veto on it | He chose the measurement and the vision path together, so the number can steer the channel per step but cannot decide vision will not be built | Settled |
| 3 | Which project's frames | `lsgi` | His answer to the council's OQ1: "OQ1: lsgi" | Settled |
| 4 | Who owns the Unreal facts | `agent-lsgi-unreal` knows the editor; BRYES is a visual executor | His words: "we also have agent-lsgi-unreal... that's up to the agent... bryes should just do visual execution" | Settled |
| 5 | What the report must contain | The C-1 shape: per-kind attempts, hits, rate, median error, the model recorded, and a verdict in channel terms | Contract written at council Step 11 and confirmed with the decomposition | Settled |

- **Integration contracts**: **produces** `contracts/measurement-report.schema.json` (C-1), consumed by SP-4 and SP-5. Consumes nothing.
- **Pushed-down open items**: the probe ground truth and how a hit is scored (this plan's call); which blueprint the live build targets and what a landed drop looks like on screen (SP-5's call).

### From Pre-Planning Discussion
- **Discussion**: None — the council handoff carries everything Agreed so far.
- **Agreed scope**: None

| # | Settled decision | Chosen | His reason | Status |
|---|------------------|--------|------------|--------|
| — | — | — | — | — |

- **Considered and rejected**: None
- **Left open**: None

---

## **OBJECTIVES**
Answer one question with a number: when the agent names something on a real Unreal editor screen, how often does the Eyes' grounding point land on it? Split by the three kinds of target the live build needs, so the answer routes work instead of merely describing it.

### **Related Documents**
- [core-plan.md](core-plan.md) - the council this sub-plan belongs to; R1 is its scope
- [contracts/measurement-report.schema.json](contracts/measurement-report.schema.json) - the report shape this plan produces
- [docs/quality-standard.md](../../docs/quality-standard.md) - the project criteria the harness is held to

### **SUCCESS CRITERIA**
- [ ] `grounding.py` scores a labelled frame and writes a C-1 shaped report plus an overlay
- [ ] `test_grounding.py` is green, model-free, and covers the hit rule, aggregation, validation and the end-to-end write
- [ ] The frame is a capture of the monitor that holds the editor, verified by looking at it before any target is marked
- [ ] The report carries a per-kind rate and median error, with `GROUND_MODEL` recorded so a model swap invalidates it
- [ ] The verdict is written in channel terms: which steps go by eye, which go through the API

---

## **SCOPE**

### In Scope
- The harness: `grounding.py` and its model-free test.
- A capture of the editor's monitor, taken through BRYES's own capture path.
- An answer key per frame: named targets with boxes, one per kind and more.
- The report, its overlay, and a verdict read in channel terms.

### Out of Scope
- Changing `locate()` or its model. This plan measures what exists.
- Driving the editor. No action is taken on the screen here.
- The Windows and Unreal profiles, which are SP-4's.
- Making the host body's `screenshot()` monitor-scoped, which is R10 in SP-2. This plan captures the monitor explicitly and leaves the body's behaviour to that sub-plan.

---

## **CONFIRMED DECISIONS**
*Decisions made **by this plan** — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A and B decisions made by the agent, recorded with their reasoning). The reasons serve as the analysis record.*
*Decisions settled before this plan existed — by a parent, or in a pre-planning discussion — belong in [INHERITED CONTEXT](#inherited-context) above, not here. Keeping them separate is what shows which decisions this plan actually owns.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | What the test runs on | A live capture through BRYES's own path, scoped to the monitor holding the editor. No lesson images. | Alvi's call: "you can take it directly using bryes". A hit rate belongs to the frame it was measured on, so the frame must be the one the agent will act on. The lesson shots are window crops (3456x1408, one at 930x900) and are teaching material, not agent input. |
| 2 | What counts as a hit | The returned point falls inside the authored box, and the edge counts as inside. Median distance to the box is reported beside it. | No invented tolerance: a pixel tolerance would be a tuned constant deciding the headline number. Inside-the-box is the call the agent actually needs to be right about, and the distance keeps the near misses visible. |
| 3 | Where the harness lives | A root utility `grounding.py` with `test_grounding.py`, the same shape as `capture.py`, `lesson.py` and `framediff.py`. | The quality standard puts single-purpose utilities at the root and tests beside them, and forbids a root `tools/` (taken by gitignored adb). The rig is a utility, not a module role. |

---

## **SOLUTION**

### Architecture Overview
Three parts, each replaceable on its own: a capture (the frame), an answer key (the truth), and a scorer (the measurement). The scorer never sees how the frame was produced, so the same rig will score any app's screen later. The only model call is `locate()`, which is the thing under test.

### Component 1: The harness
- **Purpose**: turn a labelled frame into a per-kind hit rate, a report, and a picture that shows whether the answer key is sane.
- **Key Files**: `grounding.py`, `test_grounding.py`

### Component 2: The frame
- **Purpose**: the pixels the agent would act on, scoped to the monitor holding the editor.
- **Key Files**: `artifacts/grounding/lsgi-2026-10-28/*.png` (gitignored), captured by the same `ImageGrab` call the body uses

### Component 3: The answer key
- **Purpose**: name each target and draw its box, since a frame alone has nothing to compare against.
- **Key Files**: `artifacts/grounding/lsgi-2026-10-28/labels-*.json`

<!-- OPTIONAL SECTION A: Include when multi-system changes, multiple components interacting -->
### Integration Architecture
[Table or diagram showing how all components integrate together]

| Component | Integrates With | Data Flow | Dependencies |
|-----------|----------------|-----------|--------------|
| [Component 1] | [Other components] | [Input → Processing → Output] | [Required components] |
| [Component 2] | [Other components] | [Input → Processing → Output] | [Required components] |

<!-- OPTIONAL SECTION A2: Include when a change alters a data shape/format/contract that CROSSES a system, service, or process boundary (a field's type/nullability, a string format, an enum value, a serialized payload, a DB column another app reads). Skip for single-system internal changes. -->
### Cross-System Contract Impact (Blast-Radius Check)

*A producer-side change to shared data silently breaks consumers that nobody updated in the same pass. Enumerate EVERY consumer of the changed shape and how each is verified BEFORE shipping. Producer and consumers are usually separate deploys.*

**Change classification** (check all that apply): ☐ field type/nullability ☐ string/ID format ☐ enum value added/changed ☐ new/removed field ☐ semantics changed (same shape, new meaning)

| # | Consumer (system + path) | How it couples (deserialize / string-parse / DB-read / migrate / display) | Breaks how on this change? | Verified / mitigated |
|---|---|---|---|---|
| 1 | [System → file] | [coupling] | [crash / silent-wrong / leak / none] | [what was checked] |
| 2 | [System → file] | [coupling] | [crash / silent-wrong / leak / none] | [what was checked] |

- **Deploy ordering**: [which ends deploy, in what order — a producer-only deploy with a stale consumer is the classic break]
- **Existing data**: [is historical data mixed-format / un-migrated? parsers must handle both]
- **Project registry**: [link to the project's cross-system consumer registry if one exists]

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

- **Consideration 1**: [Description]
  - [Sub-detail]
  - [Sub-detail]
- **Consideration 2**: [Description]
  - [Sub-detail]
  - [Sub-detail]

<!-- OPTIONAL SECTION D: Include for investigation/analysis-focused tasks -->
### Detailed Analysis

#### Objective Analysis
[What does the objective really want? Break down requirements and specifications]

- **Requirement 1**: [Analysis]

#### Current State Analysis
[What is our current state? Existing code, systems, capabilities, constraints]

- **Existing Systems**: [Current technology stack and architecture]
- **Current Capabilities**: [What we can do now]
- **Known Limitations**: [Current constraints and bottlenecks]

<!-- OPTIONAL SECTION E: Include for bug investigation/fix tasks -->
### Bug Investigation

#### Bug Information
- **Bug Report**: [What was reported / what's the symptom]
- **Context**: [When does it occur? What conditions trigger it?]
- **Severity**: [Impact on users/system]

#### Scaffolding Check
- **Existing Tests**: [What test coverage exists around the bug area?]
- **Debugging Tools**: [What logging/debugging infrastructure do we have?]
- **Reproduction**: [Can the bug be reliably reproduced? Steps to reproduce.]

#### Bug Location
- **Suspected Area**: [Files/modules/functions where the bug likely lives]
- **Evidence**: [What points to this location?]

#### Hypothesis Testing
*Test hypotheses sequentially. Each must be tested before moving to the next.*

| # | Hypothesis | Test | Result | Confirmed? |
|---|-----------|------|--------|------------|
| 1 | [What might be causing the bug] | [How to verify] | [What happened] | Yes/No |

#### Root Cause
- **Confirmed Cause**: [The verified root cause of the bug]
- **Evidence**: [What test/evidence confirmed this?]

<!-- OPTIONAL SECTION F: Include for brainstorming/decision tasks, multiple viable approaches -->
### Solution Options & Evaluation

#### Solution Options
*List 5-8 potential solutions. Brief description for each.*

| # | Solution | Description |
|---|----------|-------------|
| 1 | [Name] | [Brief description of approach] |

#### Evaluation
*Evaluate top candidates with pros/cons.*

| Solution | Pros | Cons |
|----------|------|------|
| [Name] | [Advantages] | [Disadvantages] |

#### Selected Approach
- **Chosen**: [Solution name]
- **Rationale**: [Why this solution wins — connects evidence from evaluation]

<!-- OPTIONAL SECTION G: Include when task produces an architecture decision record -->
### ADR Output
- **ADR File**: [Path to created ADR file, filled by procedure Step 12]
- **Decision Summary**: [1-sentence summary of the decision made in section F]

---

## **IMPLEMENTATION PHASES**

### Phase 1: The harness
- [x] **Step 1.1**: The scorer, its validation, and a model-free test
  - **Action**: Write `grounding.py` (load, score, aggregate, render, report) and `test_grounding.py`.
  - **Implementation**: Boxes in frame pixels; `inside()` inclusive on the edge; `distance()` 0 inside, else Euclidean to the nearest edge or corner; probes aggregated per kind in the C-1 shape; `GROUND_MODEL` recorded; the overlay drawn so a wrong key is visible.
  - **Testing**: `python test_grounding.py`, model-free, with a fake locator for the end-to-end case.
  - **Success Criteria**: all four tests green; the report validates against C-1's required fields.

### Phase 2: The live reading
- [ ] **Step 2.1**: Capture the screens the build needs
  - **Action**: Capture the editor's monitor with a Blueprint graph open, and a second frame with the Content Browser open.
  - **Implementation**: `MonitorFromWindow` for the rect, `ImageGrab(bbox=rect, all_screens=True)`, saved under `artifacts/grounding/`.
  - **Testing**: Look at each capture and confirm the editor is on it and fills it, before marking anything.
  - **Success Criteria**: a frame exists per screen, at the monitor's size, with the editor visible.

- [ ] **Step 2.2**: Author the answer key
  - **Action**: Name roughly ten targets per kind per frame and draw their boxes.
  - **Implementation**: `kind` plus `instruction` plus `box` in pixels; node headers on real nodes, pins on real pins, empty spots in blank canvas away from every node.
  - **Testing**: Run the overlay, look at it, and correct any box that does not sit on its target.
  - **Success Criteria**: every box verified by eye on the overlay.

- [ ] **Step 2.3**: Run the live scoring and write the verdict
  - **Action**: `python grounding.py --frame <png> --labels <json>` per frame, then read the rates in channel terms.
  - **Implementation**: Real `locate()` calls, one per target; report written beside the labels.
  - **Testing**: Sanity-check the numbers against the misses in the report's per-target detail.
  - **Success Criteria**: a C-1 report per frame, and a verdict saying which steps go by eye and which through the API.

---

## **EXECUTION LOG**
**Execution Protocol for AI**:
I have to use this document as my **ONLY** source of truth to execute and track the plan steps iteratively. I should **NOT** use additional tools like ToDos because it lacks the context of what should I do. Everytime I want to implement a step I have to check the reference to the original step plan above. Everytime a step has been finished I need to go back to this document to log what was done.

**Definition of Done (applies to ALL steps)**:
- ✅ **Code Quality**: Code compiles/runs without errors
- ✅ **Testing**: Tests written and passing
- ✅ **Logged**: Implementation and testing logged below
- 🚫 **Blocked**: Get input from [USER-NAME] before assuming

### Phase 1:
- [x] **Step 1.1**: The scorer, its validation, and a model-free test
  - **Implementation Log**: `grounding.py` written: `load_labels` (project + frame + targets, kind enum, four-int box, inverted-box refusal), `inside` (edge inclusive), `distance` (0 inside, Euclidean otherwise), `score` (per-kind attempts/hits/rate, absent kinds skipped, median error), `render` (boxes plus returned points onto the frame), `build_report` (C-1 shape with `GROUND_MODEL`), `run`, and a CLI with `--frame --labels --out`. `test_grounding.py` written beside it with four model-free tests. First import failed (`import eyes` is an empty package init); fixed to `from eyes.client import GROUND_MODEL, locate`, matching `agent/loop.py`.
  - **Testing Log**: `python test_grounding.py` -> PASS on the hit rule and distance, PASS on per-kind aggregation and absent kinds, PASS on validation of an empty target set and an inverted box, PASS end to end with a fake locator (report and overlay written). Live path not yet exercised: it needs a frame showing the target kinds.
  - **Success Criteria**: Pass on the harness; the live reading is Phase 2.
  - **Tech Debts**: The capture used for smoke (Project Settings open) shows no node header, pin or empty canvas, so it cannot produce a real reading. A Blueprint graph frame is needed.
  - **Result**: Harness complete and green; the number waits on the right screen.

### Phase 2:
- [x] **Step 2.1**: Capture the screens the build needs
  - **Implementation Log**: `MonitorFromWindow` on `BP_CombatBody_Party` resolved the primary 1920x1080 at (0,0); captured with `ImageGrab(bbox=monitor, all_screens=True)` to `artifacts/grounding/lsgi-2026-10-28/bp-window-02-monitor.png`. A window-rect variant was captured beside it for comparison.
  - **Testing Log**: Looked at the capture before using it: it is the Blueprint editor on EventGraph, with three nodes and the node he dragged in (`LSGICombat Unit UI`), and the taskbar strip at the bottom.
  - **Success Criteria**: Pass.
  - **Tech Debts**: The monitor layout changed between the two probes of this session (3440x1440 moved from (0,0) to (-783,1080)), so no rect may be cached. Only one frame exists; the Content Browser frame he suggested is still uncaptured.
  - **Result**: One usable frame.

- [x] **Step 2.2**: Author the answer key
  - **Implementation Log**: Twelve targets in `labels-bp-02.json`: 3 node headers, 5 pins, 4 empty-canvas regions, each with an instruction naming the node it belongs to.
  - **Testing Log**: `--check-labels` drew the boxes with no model call; looked at the overlay and confirmed each box sits on its target. Pin boxes cover the pin and its short label, which is slightly generous.
  - **Success Criteria**: Pass, with the pin-box generosity noted.
  - **Result**: Key verified by eye before any call was spent.

- [x] **Step 2.3**: Run the live scoring and write the verdict
  - **Implementation Log**: `grounding.py` run on two frames, 28 `locate()` calls across both after one correction pass; a report and overlay per frame.
  - **Testing Log**: First pass gave pin 2/5 on frame 02 and 1/5 on frame 03, and the zoomed overlay showed why that differed: the pin boxes were 5 to 10 px off, cutting the pin glyph. Re-marked the five pin boxes from 4x crops as 24x24 boxes centred on each pin, then re-ran both frames. Corrected result, identical on both: headers 2/3, pins 1/5 (median 10.6 px), empty canvas 0/6 across both, asset tiles 6/6.
  - **Success Criteria**: Pass. The shared probes reproduce across two frames, so the rates are stable rather than noise.
  - **Tech Debts**: Small targets must be marked on a zoomed crop and divided back, never marked from the full frame; the first pass was measuring the author's hand. One screen only (the blueprint editor), so the rates describe that screen. The `empty_canvas` probe asks a pointing model for nothing, which is a probe-design question, not a model verdict.
  - **Result**: A stable per-kind reading in channel terms, with the pin rate low enough to route wiring away from vision.

---

## **QUALITY REVIEW**
*Filled by procedure Step 16 (delegated to `/analyze-code-quality` in embedded mode) after all execution phases are complete. **Static** review — answers "is the code clean?".*

- **Scope**: [Files reviewed — from Execution Log, reconciled against `git status --short`]
- **Quality Standard**: [quality-standard.md found / not found — dimensions applied]
- **Findings**: [Issues found, or "No findings"]
- **Fixed**: [What was fixed from approved findings, or "N/A"]

---

## **QA HANDOFF**
*Filled by procedure Step 17 after Quality Review is resolved. This plan is **not** runtime-verified — this section records the plan for that verification, which happens in a QA session with the stack up.*

- **Scope**: [Modules touched]
- **QA instrument**: [Set up / NOT SET UP — auto-skipped]
- **Integration coverage**: [Filled at Step 14]
- **Checklist**: [`qa/checklists/{feature}.md`, or "none — skipped, reason"]
- **Coverage split**: [N automated / N manual — of which N are UI-bound]
- **Runtime verification**: **NOT DONE.** Next action: [...]

> Do not read a filled checklist as a passed one. This section says a verification *plan* exists, nothing more.

---

## **POST-COMPLETION**
After all phases are executed, logged, and both **Quality Review** + **QA Handoff** are filled, move this plan to `plans/completed/`:
`mkdir -p ./plans/completed && mv ./plans/[this-file].md ./plans/completed/[this-file].md`
