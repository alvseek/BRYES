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
[Clear, concise statement of what we want to achieve]

### **Related Documents**
- [Document 1](path/to/document1.md) - Brief description

### **SUCCESS CRITERIA**
- [ ] [Primary goal achieved]

---

## **SCOPE**

### In Scope
- [Specific deliverable or feature]

### Out of Scope
- [Explicitly excluded item and why]

---

## **CONFIRMED DECISIONS**
*Decisions made **by this plan** — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A and B decisions made by the agent, recorded with their reasoning).*
*Decisions settled before this plan existed belong in [INHERITED CONTEXT](#inherited-context) above, not here.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | [Decision topic] | [Chosen option] | [Evidence-based reason] |

---

## **SOLUTION**

### Architecture Overview
[High-level system design and component interaction, built from confirmed decisions]

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
I have to use this document as my **ONLY** source of truth to execute and track the plan steps iteratively. I should **NOT** use additional tools like ToDos because it lacks the context of what should I do.

**Definition of Done (applies to ALL steps)**:
- ✅ **Code Quality**: Code compiles/runs without errors
- ✅ **Testing**: Tests written and passing
- ✅ **Logged**: Implementation and testing logged below
- 🚫 **Blocked**: Get input from [USER-NAME] before assuming

### Phase 1:
- [ ] **Step 1.1**: [link to step above]
  - **Implementation Log**: [What was done]
  - **Testing Log**: [What was tested and results]
  - **Success Criteria**: [Pass/Fail against step's success criteria]
  - **Tech Debts**: [Optional]
  - **Result**: [Outcome compared to success criteria]

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
