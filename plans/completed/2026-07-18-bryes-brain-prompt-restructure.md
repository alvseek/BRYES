# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES (vision-based computer-use agent)
- **Date**: 2026-07-18
- **Agent**: claude-software-architect
- **Theme**: Brain-prompt restructure — priority-ordered condition blocks + durable CONFIRMED FINDINGS ledger + channel-aware perception, to fix the re-read/self-doubt non-convergence seen in the 07-18 Tokopedia run (step_limit, never converged). Bundles glossary-by-source labelling + OVERVIEW_SCALE 0.5.
- **Source Protocol**: `/high-wizard` — [Procedure](//@agent-memory/control-files/procedures/high-wizard.md)

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **OBJECTIVES**
Fix the Brain's **non-convergence-by-self-doubt** failure. In the 2026-07-18 Tokopedia run the Brain read the MX3 prices correctly at step 7, but because HISTORY is **actions-only** those facts were gone by step 15 — it re-read, distrusted its own (partly-misread) data, and re-searched until step_limit, never reaching `done`. Give the Brain a **durable, trusted record of what it has learned** (CONFIRMED FINDINGS) and a **priority-ordered prompt** (CURRENT CONDITION / FINDINGS as primary) so it stops re-reading and re-doubting confirmed facts. Bundle two small perception/clarity wins (glossary-by-source, OVERVIEW 0.5).

### **Related Documents**
- [07-18 run transcript](../artifacts/runs/20260718-094922-tokopedia-mx-compare/transcript.md) - the failure this plan fixes
- [ADR-005 structured output](../docs/adr/2026-07-16-structured-output-standard.md) - forced tool-calling (kept)
- [ADR-004 foveal describe](../docs/adr/2026-07-16-foveal-describe-trim.md) - OVERVIEW_SCALE lives here
- [ADR-006 embodiment](../docs/adr/2026-07-17-embodiment-selection.md) - profiles/glossary source
- [quality-standard.md](../docs/quality-standard.md) - Dim 4 amended by this change

### **SUCCESS CRITERIA**
- [ ] `decide()` prompt restructured into 6 priority-ordered blocks: GOAL / **CURRENT CONDITION** / **CONFIRMED FINDINGS** / HISTORY / PROFILES MANUAL / TODO (first two marked primary)
- [ ] CONFIRMED FINDINGS = **append-only loop-owned ledger**; new `findings` field on BrainAction; corrections-allowed; carried across steps
- [ ] HISTORY lines carry a compact **`note`** (dedicated field); `did — note`
- [ ] CURRENT CONDITION is **channel-aware** (result = visual reading OR `/exec` output; visual marked UNCHANGED after a non-screen action)
- [ ] Glossary **labelled by source** (`ANDROID/WHATSAPP/TOKOPEDIA UI ELEMENTS`)
- [ ] `OVERVIEW_SCALE = 0.5`
- [ ] Base-prompt prose reconciled (FINDINGS + HISTORY trusted; screen judged from CURRENT CONDITION; `done`/`fail` reminder in TODO)
- [ ] Model-free tests updated/added (profiles `_join` labelling; decide prompt-assembly; loop findings accumulation); ruff clean
- [ ] ADR-007 written; quality-standard Dim-4 amended; docs synced
- [ ] Phase 2 (skip the Eyes on non-visual actions) designed; implemented as a **separable** second step

---

## **SCOPE**

### In Scope
- Restructure the `decide()` user-prompt into priority-ordered labelled blocks ([brain/client.py](../brain/client.py))
- Add `findings` + `note` fields to `BrainAction`; loop accumulates the **append-only** findings ledger + `note`-in-history ([agent/loop.py](../agent/loop.py))
- **Channel-aware** CURRENT CONDITION (loop passes last-action / its-result / `/exec`-output / current-visual + a screen-changed flag)
- **Phase 2 (separable):** skip the `describe()` call when the last action didn't touch the screen (wait / shell / screenshot / failed action)
- Glossary-by-source labelling in `_join` ([profiles.py](../profiles.py))
- `OVERVIEW_SCALE` 0.375 → 0.5 ([eyes/client.py](../eyes/client.py))
- Base-prompt prose update; `done`/`fail` reminder in TODO
- Tests, ruff, ADR-007, quality-standard Dim-4 amendment, doc-sync

### Out of Scope
- **The q3-8b numeric/price-misread issue** (`Rp2.105.000` → "1.050.000"/"1.205.000") — a real, *separate* perception problem (fix would route numeric reads to the 72B or add a recheck-on-numbers). Noted for a follow-up; not fixed here.
- Any change to the embodiment/answer flow (ADR-006), the structured-output transport (ADR-005 forced tool-calling — **kept**), or model selection
- The decide-latency problem (carried tech-debt)

---

## **CONFIRMED DECISIONS**
*These decisions were collected during investigation — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A/B decisions made by the agent with reasoning, per [What to Surface](../procedures/wait-options.md#what-to-surface)). The reasons serve as the analysis record.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | Findings accumulation | **Append-only, loop-owned** ledger (corrections-allowed) | *(asked)* Robust against the forgetting that caused the failure — the Brain cannot drop a banked fact; explicit correction lines handle bad reads. 1M-ctx target makes growth a non-issue. |
| 2 | Compact history rationale | **Dedicated `note` field** | *(asked)* Brain controls conciseness; no arbitrary `thought` truncation. |
| 3 | Prompt-shape ownership | `decide()` composes the blocks; loop passes structured inputs | Keeps prompt assembly in one place (current design); the loop supplies the data. |
| 4 | Block order + priority | GOAL / CURRENT CONDITION\* / CONFIRMED FINDINGS\* / HISTORY / PROFILES MANUAL / TODO (\*=primary) | Alvi's ask: current condition + what's been learned are the primary inputs. |
| 5 | Channel-awareness now, Eyes-skip later | Phase 1 labels the channel; **Phase 3** skips `describe()` on non-visual actions | Alvi's phasing — prompt restructure lands first; the perf optimization is separable but designed now (they're coupled). |
| 6 | Prose reconciliation | Keep "judge the current SCREEN from CURRENT CONDITION"; make CONFIRMED FINDINGS + HISTORY **explicitly trusted** | Resolves the tension that caused re-doubt: stale screen-memory (distrust) vs gathered facts (trust). |
| 7 | Glossary by source | Per-profile `UI ELEMENTS` heads | Disambiguates collisions (WhatsApp "Search bar" vs Tokopedia "Search box" vs browser address bar). |
| 8 | `OVERVIEW_SCALE` | 0.5 | Evidence: results-page overview at 0.375 is nearly unreadable; homepage was fine. |
| 9 | Quality-standard Dim-4 amendment | History no longer strictly actions-only | The findings ledger + `note` are **distilled** facts (not verbose describe text); 1M-ctx relaxes the tightness rationale. |
| 10 | ADR | **ADR-007** (Brain-prompt architecture) | An architecturally significant prompt-contract change. |
| 11 | `thought` field | Kept as-is | Full per-step reasoning → transcript; unchanged. |
| 12 | Numeric/price-misread (q3-8b) | **Out of scope** | A separate perception problem; noted for a follow-up (route numeric reads to 72B / recheck-on-numbers). |

---

## **SOLUTION**

### Architecture Overview

The `decide()` call is the Brain's per-step reasoning. Today it receives a flat `GOAL / OBSERVATION / HISTORY` prompt where HISTORY is **actions-only**, so any fact the Brain *reads* (a price) exists only in that step's transient observation and vanishes next step. This plan changes the **prompt contract** into priority-ordered, labelled blocks and adds a **durable, loop-owned CONFIRMED FINDINGS ledger** the Brain appends to — the facts it banks stay visible every future step, so it never re-reads or re-doubts them.

**New per-step prompt shape (composed in `decide()`):**
```
GOAL:
  <goal>

CURRENT CONDITION (your primary input — the present moment):
- Your last action: <last did, or "(none — first step)">
- What resulted from it: <channel-aware: shell -> /exec output | visual -> "see Current screen below" | wait -> "waited Ns" | failed -> "FAILED (cause); screen unchanged">
- Current screen: <fresh observation, OR "(unchanged since your last action)" after shell/screenshot/failed>

CONFIRMED FINDINGS (facts you have ESTABLISHED — TRUST these, do not re-verify):
  <append-only ledger, step-tagged, or "(none yet)">

HISTORY OF YOUR ACTIONS (most recent last):
- <did — note>   # note = the compact "why" for that action

PROFILES MANUAL — how the current device and app WORK (follow this exactly):
  <operating profile context>

<escalation, if any>

TODO:
  Decide the single next action — including "done" if the GOAL is satisfied, or "fail" if it
  cannot be reached. Return a JSON object matching the decide_action schema.
```

**Data flow:** the loop owns the **findings ledger** (append-only) and the **channel classification** (did the last action change the screen?); it passes structured pieces to `decide()`, which composes the blocks. The Brain writes new facts via a `findings` field (looped back into the ledger) and a per-action `note` (looped into history). Screen-state is judged from CURRENT CONDITION; gathered facts are trusted from CONFIRMED FINDINGS + HISTORY — the split that resolves the re-doubt failure.

### Component 1: Brain schema + prompt (`brain/client.py`)
- **Purpose**: add `findings` + `note` fields to `BrainAction`; restructure the `decide()` user-prompt into the 6 priority blocks (channel-aware CURRENT CONDITION); reconcile `_BASE_PROMPT` prose (trust findings/history, judge screen from current condition, bank-what-you-learn, `done`/`fail` reminder).
- **Key Files**: `brain/client.py` (modify), `brain/test_phase3.py` (reconcile to new signature).

### Component 2: Loop orchestration (`agent/loop.py`)
- **Purpose**: maintain the append-only findings ledger (step-tagged, corrections-allowed); classify each action as screen-changing or not; build the channel-aware condition; thread `did — note` into history; **Phase 3:** skip `describe()` when the last action didn't touch the screen.
- **Key Files**: `agent/loop.py` (modify).

### Component 3: Profiles glossary + Eyes scale (`profiles.py`, `eyes/client.py`)
- **Purpose**: label the merged `UI ELEMENTS` glossary per source profile (`ANDROID/WHATSAPP/TOKOPEDIA UI ELEMENTS`); bump `OVERVIEW_SCALE` 0.375 → 0.5.
- **Key Files**: `profiles.py` (modify `_join`), `eyes/client.py` (constant), `test_profiles.py` (extend).

### Integration Architecture

| Component | Change | What it threads |
|-----------|--------|-----------------|
| `BrainAction` (schema) | +`findings`, +`note` fields | Forced tool-call (ADR-005, unchanged); validated via Pydantic. `findings` → ledger; `note` → history |
| `decide()` (prompt) | Restructured blocks; new params `last_action / last_result / current_visual / visual_unchanged / findings` | Receives structured condition + ledger from the loop; composes the 6-block prompt |
| `run()` loop | Append-only `findings` ledger; action-classifier `_changes_screen`; channel-aware condition; `did — note` history | Orchestrates: reads Brain's `findings`/`note`, accumulates ledger, builds condition, feeds next `decide()` |
| `profiles._join` | Per-profile `UI ELEMENTS` heads | Feeds the (now source-labelled) glossary to BOTH Eyes (visual) and Brain (operating) |
| `eyes.describe` | `OVERVIEW_SCALE` 0.5 | Overview gist legibility (no interface change) |

**Deploy note:** all changes are in one repo, one process — no cross-service contract. `BrainAction` is producer+consumer within `decide()`; the only "consumer" of the prompt shape is the rented model (tolerant of prose changes).

### Technical Considerations

- **The "trust memory" prose is load-bearing — split it, don't delete it.** The base prompt's "judge from the OBSERVATION, not memory of past screens" was the fix for the OLD clear-loop bug (trusting stale *screen* state). The new rule must distinguish **stale screen-state** (judge from CURRENT CONDITION — do NOT trust memory of past screens) from **gathered facts** (TRUST CONFIRMED FINDINGS + HISTORY — do not re-verify). Getting this wrong in either direction re-opens a known failure (over-trust screen memory → clear-loop; under-trust facts → today's re-doubt loop).
- **Quality-standard Dimension 4 amendment.** "History is actions-only" is being relaxed: HISTORY now carries a compact `note`, and a new CONFIRMED FINDINGS block carries distilled facts. Justified because (a) these are *distilled* facts, not verbose describe text (the thing Dim-4 actually guards against), and (b) the 1M-context target removes the tightness pressure. `quality-standard.md` is updated in-plan.
- **Append-only growth + banked errors.** The ledger is unbounded (fine at 1M ctx). A **wrong** banked finding (e.g. a q3-8b price misread) persists — mitigated by corrections-allowed (the Brain appends "correction: …"), but the real fix is the out-of-scope numeric-read reliability follow-up. Accepted for this plan.
- **`decide()` signature back-compat.** Adding structured params + keeping `observation` as a fallback avoids breaking direct callers (`brain/test_phase3.py`); those are reconciled explicitly (Step 1.5).
- **Action classification is a correctness point.** `wait` is **screen-CHANGING** (its whole purpose is to let content load) → always re-read. Only `shell` / `screenshot` / a **failed** action are "screen unchanged". Mis-classifying `wait` as unchanged would make the Brain miss loaded content.

### Solution Options & Evaluation

*Scoped to the core decision — how the Brain gets a **durable, trusted memory** of what it has learned.*

#### Solution Options

| # | Solution | Description |
|---|----------|-------------|
| 1 | **Append-only loop-owned findings ledger** | Loop holds the ledger; Brain's `findings` field only ADDS (step-tagged, corrections-allowed). |
| 2 | Brain rewrites findings each step | Brain re-emits its full canonical knowledge block every step. |
| 3 | Full `thought` in history | Stop trimming — carry every step's full reasoning into HISTORY. |
| 4 | External scratchpad via shell/`/tmp` | Brain writes facts to a file and re-reads them (what it DIY'd today). |
| 5 | Prompt reorder only (no data carried) | Just relabel/prioritize blocks; keep history actions-only. |

#### Evaluation

| Solution | Pros | Cons |
|----------|------|------|
| 1 Append-only ledger | Brain **cannot** drop a banked fact; simple to add facts; corrections handle staleness; robust | Grows unbounded (fine at 1M ctx); banked errors persist until corrected |
| 2 Brain rewrites | Brain can prune/correct freely | **Re-introduces the forgetting bug** — if it forgets a fact it won't re-emit it |
| 3 Full thought-in-history | Zero new schema | The 07-13 regression — verbose text blurs context; noisy |
| 4 Shell scratchpad | Persists outside context | Brittle (sh-vs-bash broke it today), off-context, indirect; not the Brain's native channel |
| 5 Reorder only | Cheapest | Does **not** carry the data — the facts still vanish; doesn't fix the failure |

#### Selected Approach
- **Chosen**: **#1 — Append-only loop-owned findings ledger** (+ dedicated `note` for compact history rationale).
- **Rationale**: it directly defeats the failure mode (a forgotten confirmed fact) by removing the Brain's ability to lose it — the loop, not the model, holds the ledger. Corrections-allowed covers the staleness cost. #2 and #5 leave the forgetting risk; #3 is a known regression; #4 is the brittle DIY we're replacing.

### ADR Output

- **ADR File**: [docs/adr/2026-07-18-brain-prompt-restructure.md](../docs/adr/2026-07-18-brain-prompt-restructure.md) (ADR-007)
- **Decision Summary**: The Brain's per-step prompt becomes priority-ordered labelled blocks (CURRENT CONDITION + CONFIRMED FINDINGS primary), with a durable **append-only, loop-owned CONFIRMED FINDINGS ledger** and channel-aware perception — so the Brain trusts what it has established instead of re-reading and re-doubting it.

---

## **IMPLEMENTATION PHASES**

### Phase 1: Prompt restructure + durable CONFIRMED FINDINGS (the core fix)

- [ ] **Step 1.1**: Add `findings` + `note` fields to `BrainAction`
  - **Action**: extend the schema with two optional fields.
  - **Implementation**: `findings: str | None` (bank NEW confirmed facts / a correction this step) and `note: str | None` (compact one-line "why" for this action). Write field descriptions per the ADR-005 convention ("what the field IS"). Update the `BrainAction` docstring.
  - **Testing**: model-free — instantiate `BrainAction(...)` with and without the fields; confirm `model_dump(exclude_none=True)` omits them when unset; confirm the injected-enum path still validates.
  - **Success Criteria**: both fields optional, absent from the dump when unset, no change to existing action handling.

- [ ] **Step 1.2**: Restructure the `decide()` user-prompt into the 6 priority blocks
  - **Action**: factor prompt assembly into a pure helper and add channel-aware inputs.
  - **Implementation**: add `_build_decide_prompt(...)` (pure, testable) composing `GOAL / CURRENT CONDITION / CONFIRMED FINDINGS / HISTORY / PROFILES MANUAL / <escalation> / TODO`. New `decide()` params: `last_action=None, last_result=None, current_visual=None, visual_unchanged=False, findings=None`; keep `observation=None` as a back-compat fallback (if the structured params are absent, render CURRENT CONDITION from `observation`). TODO line includes the `done`/`fail` reminder. `context` → PROFILES MANUAL label.
  - **Testing**: model-free — call `_build_decide_prompt` with (a) a visual last-action, (b) a shell last-action (result = exec output, screen unchanged), (c) first step, (d) a non-empty findings ledger; assert the block labels, order, channel-aware result line, and findings render correctly.
  - **Success Criteria**: all 6 labelled blocks present in order; channel-aware result correct for visual/shell/unchanged/first-step; findings ledger rendered under CONFIRMED FINDINGS.

- [ ] **Step 1.3**: Reconcile `_BASE_PROMPT` prose
  - **Action**: update the base prompt to match the new blocks + semantics.
  - **Implementation**: (a) intro references CURRENT CONDITION / CONFIRMED FINDINGS / HISTORY; (b) **split the trust rule** — "judge the current SCREEN from CURRENT CONDITION (not memory of past screens)" AND "TRUST your CONFIRMED FINDINGS + HISTORY — facts you established; do NOT re-verify a confirmed finding"; (c) add **BANK-WHAT-YOU-LEARN**: put a read/computed fact you'll reuse into `findings`; correct a wrong one with a correction line; (d) add the `note` instruction; (e) update the VERIFICATION-report rule to point at CURRENT CONDITION; (f) `done`/`fail` reminder. Keep it terse (avoid re-bloating).
  - **Testing**: `ruff check`; assert key phrases present (a model-free string check); manual read for the trust-split nuance.
  - **Success Criteria**: prose consistent with the new blocks; no dangling "OBSERVATION"-only guidance that would re-trigger the clear-loop; findings/history framed as trusted.

- [ ] **Step 1.4**: Loop — append-only findings ledger + channel-aware condition + `note`-in-history
  - **Action**: maintain the ledger and build the structured condition in `run()`.
  - **Implementation**: add `findings = []`; a `_changes_screen(act, failed)` classifier (screen-unchanged = `shell` / `screenshot` / failed; everything else incl. `wait` = changing); after each step capture `last_did`, the channel-aware `last_result` (shell → exec output; visual → "see current screen"; wait → "waited"; failed → failure note), and `visual_unchanged`; pass `last_action / last_result / current_visual / visual_unchanged / findings` to `decide()`; after decide, append `f"[step {step}] {findings}"` to the ledger when the Brain returned `findings`; append `did` + (` — {note}`) to history.
  - **Implementation note**: keep the shell `did` in history too (unchanged), but ALSO surface the exec output as the CURRENT CONDITION result (the fix — it was history-only before).
  - **Testing**: model-free loop test with stubbed `describe`/`decide`/device (mirror `test_run_selection` injection style) — assert (1) a returned `findings` appears in the NEXT step's prompt, (2) a `note` appears in history, (3) after a stubbed shell action the condition shows the exec output + "unchanged".
  - **Success Criteria**: findings persist across steps; history carries notes; shell result reaches CURRENT CONDITION, not just history.

- [ ] **Step 1.5**: Reconcile `decide()` callers
  - **Action**: update direct callers to the new signature.
  - **Implementation**: check `brain/test_phase3.py` + any other direct `decide(...)` callers; use the `observation` back-compat path or new params as appropriate.
  - **Testing**: run the affected model-free tests (`brain/test_phase3.py` non-live parts).
  - **Success Criteria**: existing tests pass; no caller breaks.

### Phase 2: Glossary-by-source + OVERVIEW 0.5 (small, independent)

- [ ] **Step 2.1**: Label the glossary by source in `profiles._join`
  - **Action**: replace the single flat `UI ELEMENTS:` head with per-profile heads.
  - **Implementation**: in `_join`, carry each `Terms & Vocab` block with its profile label (like `visual`/`operating` already do) and emit `f"{LABEL} UI ELEMENTS:"` per profile, in chain order, before the WORKS/LOOKS blocks. Both halves still receive the full glossary.
  - **Testing**: extend `test_profiles.py` — assert `ANDROID UI ELEMENTS` and `WHATSAPP UI ELEMENTS` (and `TOKOPEDIA UI ELEMENTS` for the browser chain) appear in both `visual` and `operating`; the existing dedup/merge checks still pass.
  - **Success Criteria**: glossary is source-labelled; `test_profiles.py` all-pass.

- [ ] **Step 2.2**: `OVERVIEW_SCALE` 0.375 → 0.5
  - **Action**: bump the constant + update its inline comment.
  - **Implementation**: `eyes/client.py:138` → `0.5`; note "2026-07-18: 0.375 too coarse on dense result pages, back to 0.5".
  - **Testing**: model-free — a 1280×800 frame downscales to 640×400 at 0.5 (mirror the existing overview-size check).
  - **Success Criteria**: constant is 0.5; downscale check passes.

### Phase 3: Skip the Eyes on non-visual actions (coupled optimization — separable)

- [ ] **Step 3.1**: Reuse the prior observation instead of re-`describe()` when the screen didn't change
  - **Action**: gate the per-step `describe()` on `_changes_screen`.
  - **Implementation**: track the previous observation; when the last action was screen-unchanged (`shell` / `screenshot` / failed), skip the `describe()` call and reuse the prior observation (CURRENT CONDITION already labels it "unchanged" from Phase 1). Keep the fresh `describe()` for all screen-changing actions incl. `wait`.
  - **Testing**: model-free — spy/stub `describe`; assert it is NOT called on the step after a stubbed shell action, and IS called after a `wait`.
  - **Success Criteria**: no describe latency on shell/screenshot steps; the Brain still sees the (unchanged) screen + the exec result.

### Phase 4: ADR + quality standard + doc-sync

- [ ] **Step 4.1**: Finalize ADR-007 + amend quality-standard Dim 4
  - **Action**: ensure ADR-007 (created in planning) is accurate to the built code; amend Dim 4.
  - **Implementation**: reconcile ADR-007 with final code; edit `quality-standard.md` Dim 4 to note history now carries a compact `note` + a distilled CONFIRMED FINDINGS ledger (still NOT verbose describe text).
  - **Testing**: read-through; links resolve.
  - **Success Criteria**: ADR-007 matches the implementation; Dim 4 reflects reality.

- [ ] **Step 4.2**: Doc-sync
  - **Action**: update the structural docs to the new prompt contract.
  - **Implementation**: `docs/context-index.md` (Brain entry / prompt shape), `docs/agent-loop-flow.md` (the per-step data flow now carries findings + channel-aware condition), `docs/architecture-overview.md` if it describes the decide prompt. (Prose-doc sync per the carried debt.)
  - **Testing**: read-through; links resolve.
  - **Success Criteria**: docs describe the CONFIRMED FINDINGS + block structure.

---

## **EXECUTION LOG**
**Execution Protocol for AI**:
I have to use this document as my **ONLY** source of truth to execute and track the plan steps iteratively. I should **NOT** use additional tools like ToDos because it lacks the context of what should I do. Everytime I want to implement a step I have to check the reference to the original step plan above. Everytime a step has been finished I need to go back to this document to log what was done.
*In other words*:
- I have to make this document as the source of truth for the implementation phase on what I have worked on and what I will be working
- The original plan must be fully in my context, therefore, I have to make sure I loaded the **Plan File** before executing any task and read carefully the reference to the original step
- I have to do the implementation by doing it in order per step THEN, I ALWAYS have to fill the step log rightly after

**Definition of Done (applies to ALL steps)**:
- ✅ **Code Quality**: Code compiles/runs without errors
- ✅ **Testing**: Tests written and passing
- ✅ **Logged**: Implementation and testing logged below
- 🚫 **Blocked**: Get input from [USER-NAME] before assuming

### Phase 1: Prompt restructure + durable CONFIRMED FINDINGS
- [x] **Step 1.1**: Add `findings` + `note` fields to `BrainAction`
  - **Implementation Log**: Added `note: str | None` (compact per-action "why" → history) and `findings: str | None` (bank a read/computed fact / a correction → ledger) to `BrainAction` in `brain/client.py`, placed after `thought`, before `action`, with ADR-005-style "what the field IS" descriptions.
  - **Testing Log**: model-free — `BrainAction(thought,action,target)` dumps without note/findings (`exclude_none`); `BrainAction(...,note=...,findings=...)` carries both. PASS.
  - **Success Criteria**: PASS — both optional, omitted when unset, no change to existing action handling.
  - **Result**: Done.

- [x] **Step 1.2**: Restructure `decide()` into the 6 priority blocks (channel-aware CURRENT CONDITION)
  - **Implementation Log**: Added pure `_build_decide_prompt(...)` composing GOAL / CURRENT CONDITION / CONFIRMED FINDINGS / HISTORY / PROFILES MANUAL / `<escalation>` / TODO. `decide()` signature now takes `last_action / last_result / current_visual / visual_unchanged / findings`; `observation` kept as a defaulted back-compat fallback (fills 'Current screen'). `decide()` body replaced its inline assembly with a call to the helper. CURRENT CONDITION is channel-aware; TODO reminds done/fail.
  - **Testing Log**: model-free — (a) first-step: all 6 blocks present + correct order; (b) visual last action → result points to Current screen; (c) shell → exec output as result + "UNCHANGED" label; (d) findings-list renders + PROFILES MANUAL/escalation optional + `observation` back-compat. ALL PASS.
  - **Success Criteria**: PASS.
  - **Result**: Done.
- [x] **Step 1.3**: Reconcile `_BASE_PROMPT` prose (trust-split, bank-what-you-learn, note, done/fail)
  - **Implementation Log**: Rewrote the intro (references CURRENT CONDITION / CONFIRMED FINDINGS / HISTORY; trust-split: judge SCREEN from CURRENT CONDITION, TRUST findings/history). Updated FOLLOW-THE-OBSERVED-STATE to the trust-split + "if a CONFIRMED FINDING answers part of the GOAL, USE it — don't re-read". Added two rules: BANK WHAT YOU LEARN (findings) + EXPLAIN EACH ACTION (note). Repointed all block-name refs OBSERVATION→"Current screen" (VERIFICATION, VISUAL_FOCUS FAILED, request_diff, done). done-line now also checks CONFIRMED FINDINGS.
  - **Testing Log**: `python -m ruff check brain/client.py` → All checks passed; `py_compile` OK; all six trust/findings/note phrases present in `SYSTEM_PROMPT`; zero residual capitalized `OBSERVATION`. PASS.
  - **Success Criteria**: PASS — prose consistent with new blocks; no dangling OBSERVATION-only guidance.
  - **Result**: Done.
- [x] **Step 1.4**: Loop — append-only findings ledger + channel-aware condition + `note`-in-history
  - **Implementation Log**: `agent/loop.py`: added `_SCREEN_UNCHANGED_ACTS` + `_changes_screen(act, failed)` (shell/screenshot/failed = unchanged; everything else incl. `wait` = changing). In `run()`: `findings=[]` ledger + `last_action_desc/last_result/visual_unchanged` carry vars; `decide()` now called with the structured channel-aware params (dropped positional `observation` → passed as `current_visual`); after decide, bank `action["findings"]` as `[step N] …` (logged); `note` captured; `step_failed` set in the except; history append is now `did (- note)`; end-of-step computes the channel-aware carry.
  - **Testing Log**: NEW `agent/test_condition_ledger.py` (model-free, stubs describe/decide + fake device) — 9/9 PASS: run reaches done; append-only ledger threads step-1→2→3; step-1 saw empty ledger; note in history; visual step → `visual_unchanged=False` + result points to screen; shell step → `visual_unchanged=True` + `last_action` shows the command. `py_compile` OK; `ruff` clean.
  - **Success Criteria**: PASS — findings persist across steps; history carries notes; shell result surfaces in CURRENT CONDITION.
  - **Result**: Done.
- [x] **Step 1.5**: Reconcile `decide()` callers (`brain/test_phase3.py`)
  - **Implementation Log**: Only direct caller besides the loop is `brain/test_phase3.py` (a live-model eyeball test) calling `decide(GOAL, observation, history)` positionally — preserved by the `observation=None` back-compat default. Added a comment marking it intentional; no signature change needed there.
  - **Testing Log**: model-free — `inspect.signature(decide).bind('GOAL','obs',['h'])` binds; `_build_decide_prompt` renders the observation under CURRENT CONDITION 'Current screen'. PASS. (The live decide-hits-model run itself was not executed — no-cost reconciliation.)
  - **Success Criteria**: PASS — existing caller works unchanged; no caller breaks.
  - **Result**: Done. **Phase 1 complete.**

### Phase 2: Glossary-by-source + OVERVIEW 0.5
- [x] **Step 2.1**: Label the glossary by source in `profiles._join`
  - **Implementation Log**: `profiles.py` `_join`: `terms` now carries `(label, body)` tuples; the head emits one `f"{label} UI ELEMENTS:"` block per source profile (in chain order), in BOTH halves, replacing the single flat `UI ELEMENTS:` blob.
  - **Testing Log**: `test_profiles.py` extended (checks 2b) — visual + operating each carry `ANDROID UI ELEMENTS:` and `WHATSAPP UI ELEMENTS:`; no unlabelled blob head. All 20 checks PASS; ruff clean.
  - **Success Criteria**: PASS.
  - **Result**: Done.
- [x] **Step 2.2**: `OVERVIEW_SCALE` 0.375 → 0.5
  - **Implementation Log**: `eyes/client.py:138` → `0.5` (comment updated: 0.375 too coarse on dense result pages; ADR-007).
  - **Testing Log**: model-free — `_downscale` of a 1280×800 frame at 0.5 → 640×400. PASS; ruff clean.
  - **Success Criteria**: PASS.
  - **Result**: Done. **Phase 2 complete.**

### Phase 3: Skip the Eyes on non-visual actions
- [x] **Step 3.1**: Reuse prior observation instead of re-`describe()` when screen unchanged
  - **Implementation Log**: `agent/loop.py`: added `prev_observation` carry; gated the per-step `describe()` — `skip_describe = visual_unchanged and prev_observation is not None and not (visual_focus or want_recheck or want_diff)`. On skip: reuse `prev_observation`, `t_describe=0`, log "[eyes skipped]". Explicit perception requests (focus/recheck/diff) always still describe. `wait` is screen-changing so it never skips.
  - **Testing Log**: `test_condition_ledger.py` extended with a describe-counter + 2 extra runs — 12/12 PASS: shell→done = 1 describe (step-2 skipped); wait→done = 2 describes (not skipped); the main run = 2 describes for 3 steps (skip after shell). `py_compile` + `ruff` clean.
  - **Success Criteria**: PASS — no describe latency on shell/screenshot steps; Brain still sees the (unchanged) screen + exec result.
  - **Result**: Done. **Phase 3 complete.**

### Phase 4: ADR + quality standard + doc-sync
- [x] **Step 4.1**: Finalize ADR-007 + amend quality-standard Dim 4
  - **Implementation Log**: ADR-007 was authored during planning and the implementation followed it — verified accurate to the built code (fields, decide restructure, loop ledger, `_changes_screen`, glossary-by-source, 0.5, unified `/exec` line in Alternatives Rejected). `quality-standard.md` Dim 4: replaced "history is actions-only" with the ADR-007 rule (actions + compact note; durable facts in CONFIRMED FINDINGS; channel-aware condition; verbose describe still OUT) + a new bullet for the Eyes-skip. (OVERVIEW `×0.5` line already correct post-revert.)
  - **Testing Log**: read-through; ADR + quality-standard links resolve.
  - **Success Criteria**: PASS.
  - **Result**: Done.
- [x] **Step 4.2**: Doc-sync (context-index, agent-loop-flow, architecture-overview)
  - **Implementation Log**: Focused ADR-007 sync — `context-index.md`: new "Brain prompt (ADR-007)" quick-fact (the 6-block structure + findings ledger + Eyes-skip + glossary-by-source + 0.5). `agent-loop-flow.md`: a dated **(2026-07-18, ADR-007)** update note (matching the doc's existing dated-note style) — the block restructure + findings closing the "no progress model" half of Seam B + the Eyes-skip; explicitly flags that per-step signatures/model-slug lines are **carried** doc-sync debt (pre-existing, not this change). `architecture-overview.md`: one-line module-map update for the `decide()` prompt blocks + ledger.
  - **Testing Log**: read-through; all ADR-007 links resolve. Scope note: a FULL prose re-sync of `agent-loop-flow.md`'s pre-existing staleness (describe slug, `focus`→`visual_focus`, obs/history signatures) remains carried debt — out of this plan's scope.
  - **Success Criteria**: PASS — docs describe the CONFIRMED FINDINGS + block structure.
  - **Result**: Done. **Phase 4 complete. All phases done.**

---

## **QUALITY REVIEW**
*Filled by procedure Step 16 (delegated to `/analyze-code-quality` in embedded mode) after all execution phases are complete. **Static** review — answers "is the code clean?".*

- **Scope**: `brain/client.py`, `agent/loop.py`, `profiles.py`, `eyes/client.py`, `agent/test_condition_ledger.py` (new), `test_profiles.py`, `brain/test_phase3.py`. **Reconciliation**: git diff also shows `docs/*` (Phase-4 doc-sync, in-plan, not code-reviewed) + `profiles/index.md` & `profiles/linux/browser/*` (from the earlier tokopedia-profile task, low-risk markdown) — accounted for, excluded from code review.
- **Quality Standard**: `docs/quality-standard.md` found — Dims 1, 4, 5–9 applied (2/3 N/A: no UI). Dim 8 (ruff) clean; Dim 9 (structured output) compliant — `findings`/`note` are just new fields on the forced-tool-call schema, no `json_object`.
- **Findings**: No Critical/Medium. Two **Low** (optional polish, non-blocking):
  - **L1** — [agent/loop.py](../agent/loop.py) channel-aware `last_result`: for a `shell` action the exec output is surfaced on the *"Your last action"* line and the *"What resulted"* line points "above" (the approved unified-line design). Functionally the output IS in CURRENT CONDITION; optional polish would carry the outcome on the result line itself.
  - **L2** — [agent/loop.py](../agent/loop.py) `prev_observation` reuse: after a visual→shell→(skip) sequence, the reused observation can re-show a stale `VERIFICATION:` prefix. Harmless (the screen description is still accurate; only the label is stale). Optional.
- **Fixed**: Both Low items fixed (Alvi: "fix both then run"). **L1** — the loop now carries the `shell`/failure OUTCOME on the "What resulted" line (via `outcome`), with a short `gesture` on the "Your last action" line; the exec output is on the result line, not just the action line. **L2** — a reused (skipped) observation now strips a stale leading `VERIFICATION:` block. Both covered by new assertions in `test_condition_ledger.py` (15/15 PASS; ruff clean).

---

## **FINAL INTEGRATION TEST**
*Filled by procedure Step 17 after Quality Review is resolved. **Runtime** verification through the qa/ instrument — answers "does it actually work end-to-end?".*

- **Scope**: whole loop (`agent/loop.py` + `brain/client.py` prompt) via a LIVE run.
- **qa/ Status**: N/A — BRYES has no R/I/A/O `qa/` instrument; the equivalent runtime test is a live agent run.
- **Playbooks Run**: Live re-run of the *exact* 2026-07-18 failing task (`tokopedia-mx-adr007`): "compare avg price of MX Master 3 vs 4 from the first Tokopedia result row." Self-select embodiment.
- **R/I/A/O Results**: **PASS — converged to `done` in 5 steps** (the prior run hit step_limit/20 and never converged). The **CONFIRMED FINDINGS ledger was actively used and trusted** — the Brain banked MX3+MX4 prices + the computed averages and called `done` from the ledger, with **zero re-read/re-doubt loop** (the exact failure this plan targeted). **Eyes-skip fired** once (after the `shell` compute — "[eyes skipped]"). `visual_expectation` emitted 2/2 on acting steps (0 null). Bonus: the Brain used `python3 -c` for the compute (clean; avoided the earlier sh-vs-bash array bug) and reasoned about excluding the "for Mac" variant.
- **Findings**: The **convergence fix is proven**. Honest caveats (NOT regressions, NOT in scope): (1) Chrome started on leftover MX4-results state from the prior run, so step 1 didn't navigate from google.com — the bank→trust→converge behavior is start-independent, but it wasn't a pristine from-scratch run; (2) the **q3-8b numeric-misread persists** (out of scope) — the banked MX4 prices (~1.2M) are still misreads of the real ~2.1M cards, so the *absolute* answer (MX3 dearer by Rp285,845) is wrong; (3) 4-vs-5 card comparison (it excluded "for Mac" from MX4 only). The numeric-misread is now the clear next bottleneck (the documented follow-up).
- **Fixed**: N/A — no runtime regressions; the caveats are the pre-flagged out-of-scope perception issue.

### Post-plan addendum (2026-07-18) — the out-of-scope numeric-misread, RESOLVED
The live run exposed that convergence alone still gave a *wrong* answer (banked misread MX4 prices). A measured follow-up (same-crop 3× bake-off) showed the q3-8b describe model **systematically** misreads discounted price digits (`Rp2.105.000`→`Rp1.050.000`, byte-identical at temp 0), while **qwen3-vl-30b-a3b** reads them correctly, faster (MoE), and cleaner. Fix = a `DESCRIBE_MODEL` swap (8b → 30b-a3b, [ADR-004](../docs/adr/2026-07-16-foveal-describe-trim.md) Amendment 1) + a one-line Tokopedia profile correction (current price = the **bold, non-struck** one; the struck original is HIGHER). Thinking tested + rejected (8b-thinking accurate but 40-115s; 30b-a3b-thinking degraded). **Validated live**: the exact task now reads MX4 at ~2.1M and lands the correct verdict — "MX4 dearer by Rp378.980", where every prior run was backwards. (These files — `eyes/client.py` model swap, `profiles/linux/browser/tokopedia/profile.md` — are outside the original plan scope but committed together.)

---

## **POST-COMPLETION**
After all phases are executed, logged, and both **Quality Review** + **Final Integration Test** are filled, move this plan to `plans/completed/`:
`mkdir -p ./plans/completed && mv ./plans/[this-file].md ./plans/completed/[this-file].md`
