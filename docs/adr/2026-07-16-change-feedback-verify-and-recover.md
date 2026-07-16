# ADR-003: Change-Feedback — Verify-and-Recover (Phase 5)

**Date**: 2026-07-16

**Status**: Accepted

---

## Problem

BRYES's loop authored history from what it *tried*, never checking the screen actually changed — **Seam B** ([agent-loop-flow.md §4](../agent-loop-flow.md)). A misclick, a dead control, or an AC that clears nothing was recorded identically to a success, so the Brain (each `describe` independent) could loop on a futile action forever — the "1024 clear-loop" post-mortem. Phase 5 is the roadmap's differentiator: *after each action, did the intended thing actually happen? If not, recover.*

The load-bearing question is **"did my action work?"** — and the first design got its *shape* wrong.

---

## Decision

**We decided to**: make change-feedback the **VLM's job**, and split it correctly — **the Eyes perceive, the Brain judges**. The Brain predicts a **`expect`** with each action; the loop rides it into the next `describe`, which **REPORTS the actual state of that thing** (`VERIFICATION: <what is literally shown>`) — a grounded description, *not* a pass/fail verdict. The Brain compares the report to what it expected and adapts. When stuck, the Brain can request an **expensive 2-image diff** (`request_diff`). Recovery is the Brain's job (off the accurate report); the loop keeps only a dumb, advisory repeated-same-action guard.

> **Refinement (2026-07-16, live-driven):** the first cut had the *VLM* emit a `VERIFIED` / `NOT VERIFIED` **verdict**. Live testing (1024×4096) showed the verdict was **noisy** — the VLM nitpicked whitespace (`'1024 × 4'` vs `'1024×4'`), and even self-contradicted (`NOT VERIFIED - the display shows '1024×409'` when that *was* the expectation). Yet its *description* was always accurate, and the Brain sailed through on it. Lesson: the VLM is reliable at **perceiving**, unreliable at **judging** — so we stopped asking it to judge. Report `VERIFICATION: <state>`, let the Brain (the reasoner) do the match. The re-run was clean, zero verdict noise. This also removed the loop's `NOT VERIFIED` recovery signal → recovery moved to the Brain + an advisory guard (below).

This unifies three **prospective describe-modifiers** — `focus` (spatial spotlight: WHERE), `expect` (assertion: WHAT is true), `request_diff` (precise before/after) — each set on a step-N action and consumed by step-N+1's `describe`.

**Why we chose this:**
- **"Did my action work?" is regional and semantic**, not screen-wide. The VLM reporting the `focus` region's state captures a single-digit change and ignores clock/pointer noise — exactly where a whole-frame pixel metric fails both ways.
- **Eyes perceive, Brain judges** — the VLM is accurate at describing pixels but noisy at binary judgments, so it reports the state and the Brain (the reasoner) does the match. Removes a whole class of false-negative friction.
- **Zero extra cost on the common path** — the `expect` report rides the `describe` call that happens anyway.
- **Recovery stays out of the way** — the Brain recovers off the accurate report; the loop's only backstop is a dumb *advisory* guard on a repeated *identical* action, so exploration (different actions) is never punished.

---

## Why NOT a screen-wide pixel no-op detector (the dropped "Layer 1")

The original Phase-5 design had a first, free layer: a whole-frame pixel diff (`frame_diff`, 64×64 grayscale mean-abs-diff) that tagged an action `NO VISIBLE CHANGE` when nothing moved. It was built and tested — then **measurement killed it**:

- **Small real changes drown in whole-frame noise.** A single typed digit scores **~0.02–0.09** mean-diff — *below* the **0.01–0.25** idle noise floor (clock, dither). Higher resolution doesn't help; it's inherent to mean-over-whole-frame. So pixel-diff can't separate a small real change from noise, and would false-tag real changes as no-ops (actively harmful — the Brain would redo a successful keystroke).
- **It can't be cheaply regionalised.** The fix (crop to the acted-on region) needs a bounding box, but **UI-TARS-1.5-7B only points** — tested across its native `start_box`, an explicit "four integers", Qwen `bbox_2d` JSON, and a tight single-button target, it returned a point (2 coords) every time. No box → no cheap region crop. The only boxer is the 72B VLM, at which point `expect` (semantic verify) strictly dominates pixel-diffing a rectangle.

So the concept "no change" is only meaningful **in a certain area, semantically** — which is precisely what `expect`+`focus` already do. `framediff.py` (built, tested) is **kept and parked** for its right consumer: the describe-speed thread, where "did a *lot* of the screen change → re-describe?" IS a screen-wide question.

---

## What was built (Requirements)

**Core:**
- **Layer 2 (primary)** — `describe(image, focus, expect)` appends a REPORT block: the Eyes emit `VERIFICATION: <the actual state of the thing the Brain named in expect>` (grounded, no judgment). The Brain schema gains `expect` + a "COMPARE THE VERIFICATION REPORT … if it differs, MAYBE it didn't work — rethink or adapt" rule; the loop threads `expect` forward (not sticky) and the report lands in the observation.
- **`focus`** sharpened to a spatial **section/region** only, distinct from `expect`.
- **Layer 3** — `eyes.diff(prev, cur, focus)` (one 2-image VLM call via a multi-image `_ask`); the Brain schema gains `request_diff` (framed EXPENSIVE); the loop runs it when set and appends `CHANGES SINCE YOUR LAST ACTION: …`.
- **Recovery** — lives in the **Brain** (it rethinks off the accurate report). The loop keeps only a **dumb, advisory** guard: if the *same* action (`last_sig`) repeats `_REPEAT_LIMIT=2`× it nudges (graduated — one more repeat also suggests `request_diff`). Different actions never trip it (exploration safe); it never picks the action.

**Success Criteria (met, live):**
- The report round-trips end-to-end: 1024×4096 → `VERIFICATION: 1|` → `1024` → `1024×` → `1024×4096` → `4194304`, the Brain judging each and flowing to a clean `done` in 6 steps — **zero** verdict noise.
- Recovery stays out of the way: the advisory guard only fires on a *repeated identical* action; different actions (exploration) never trip it.

---

## Alternatives Rejected

- **Screen-wide pixel no-op detector (original Layer 1)**: whole-frame mean-diff can't separate a small real change from noise and can't be regionally cropped (UI-TARS only points) — see above.
- **Region-scoped pixel diff via a grounded box**: needs a bounding box UI-TARS won't emit; and once the 72B VLM is boxing, `expect` (semantic verify) dominates a pixel rectangle. Rabbit hole.
- **A `find` describe field**: decomposes into `expect` (presence) / `locate` (position) / `focus` (value) — a 4th name overlapping three existing ops.
- **A standalone `diff` action**: wastes a full turn (issue → re-describe to read); the `request_diff` flag rides the next describe for free.
- **VLM emits a pass/fail verdict (`VERIFIED`/`NOT VERIFIED`)**: the VLM is reliable at *perceiving*, not *judging* — verdicts were noisy (whitespace nitpicks, self-contradictions). Report the state, let the Brain judge. (The first cut did this; live-corrected — see the Decision refinement note.)
- **`on_track` boolean from the Brain to feed the loop's recovery**: once the Brain only says a mismatch *maybe* means failure (softer, fairer), there's no honest boolean to emit — it would drag the crisp judgment back in. Dropped; recovery is the Brain's + an advisory guard.
- **Recovery on consecutive NOT-VERIFIED / a hard `fail`-floor**: moot once the verdict is gone and the Brain judges from the report; a dumb advisory repeated-action guard is enough runaway insurance.

---

## Relationship to ADR-001 / ADR-002

Orthogonal. [ADR-001](2026-07-15-effector-hierarchy.md) = which effector **tier**; [ADR-002](2026-07-15-device-interface.md) = which **body**. ADR-003 = how the loop **verifies and recovers** — it rides on whatever tier/body is active (Layer 2 uses the Eyes; a `shell` action already carries its own verified outcome, the "exception to Seam B").

---

**Full context**: [High Wizard plan](../../plans/2026-07-15-BRYES-phase5-verify-and-recover.md)
