# ADR-007: Brain Prompt Restructure — Priority-Ordered Condition Blocks + a Durable Confirmed-Findings Ledger

**Date**: 2026-07-18

**Status**: Accepted

---

## Problem

The Brain's per-step `decide()` prompt was a flat `GOAL / OBSERVATION / HISTORY`, where HISTORY is **actions-only** (the 07-13 fix against verbose-describe blur). So any fact the Brain *reads* — a price, a count, a computed result — lives only in that step's transient OBSERVATION and is gone the next step. In the 2026-07-18 Tokopedia run this caused a non-convergence failure: the Brain read the MX3 prices correctly at step 7, but by step 15 those facts had vanished from its context, so it re-read, distrusted its own (partly-misread) data, re-searched the same queries, and hit the step limit without ever calling `done`. The prompt also gave no priority signal (what to read first) and conflated "result of my last action" with "what's on screen now" — after a `shell` step the screen is unchanged, yet the loop still presented a fresh (redundant) visual read and buried the shell output in history.

---

## Decision

**We decided to**: restructure the `decide()` prompt into **priority-ordered, labelled blocks** and add a **durable, append-only, loop-owned CONFIRMED FINDINGS ledger** the Brain banks facts into.

The new per-step prompt is: `GOAL` → **`CURRENT CONDITION`** (primary) → **`CONFIRMED FINDINGS`** (primary) → `HISTORY` → `PROFILES MANUAL` → `TODO`. `CURRENT CONDITION` is **channel-aware** — it names the last action, its result (a `shell` action's result is its `/exec` output; a visual action's result is the current screen; a failed/`screenshot` action leaves the screen **unchanged**), and the current screen. `CONFIRMED FINDINGS` is a step-tagged ledger the *loop* owns: the Brain's new `findings` field only **adds** facts (or an explicit correction), so it can never drop a banked fact — the exact failure mode is removed structurally. HISTORY lines carry a compact `note` (the Brain's per-action "why"). The base-prompt prose is split so the Brain **judges the current screen from CURRENT CONDITION** (not stale screen-memory) while **trusting CONFIRMED FINDINGS + HISTORY** (facts it established; not to be re-verified). Bundled: the merged `UI ELEMENTS` glossary is labelled per source profile, and `OVERVIEW_SCALE` returns to 0.5.

**Why we chose this:**
- The loop, not the model, holds the ledger — the Brain literally cannot lose a confirmed fact, which is what caused the loop-to-step-limit failure.
- Priority ordering + a channel-aware CURRENT CONDITION make "what just happened" vs "what's on screen" unambiguous (and let the Eyes be skipped when the screen didn't change).
- Corrections-allowed keeps the ledger honest without re-introducing forgetting (rewrite-each-step would).

---

## What to Build (Requirements)

**Core Requirements:**
- `brain/client.py`: add `findings: str | None` (bank new facts / a correction) and `note: str | None` (compact per-action reason) to `BrainAction`; restructure the `decide()` user-prompt into the 6 priority blocks via a pure, testable `_build_decide_prompt(...)`; new channel-aware params (`last_action`, `last_result`, `current_visual`, `visual_unchanged`, `findings`) with `observation` kept as a back-compat fallback; `TODO` reminds `done`/`fail`.
- `brain/client.py` prose: split the trust rule (judge screen from CURRENT CONDITION; trust FINDINGS + HISTORY), add BANK-WHAT-YOU-LEARN + `note` instructions, keep it terse.
- `agent/loop.py`: an append-only `findings` ledger (step-tagged, corrections-allowed); a `_changes_screen` classifier (`shell`/`screenshot`/failed = unchanged; everything else incl. `wait` = changing); build + pass the channel-aware condition; append `did — note` to history; **(separable)** skip `describe()` when the last action left the screen unchanged.
- `profiles.py` `_join`: per-profile `UI ELEMENTS` heads (`ANDROID/WHATSAPP/TOKOPEDIA UI ELEMENTS`).
- `eyes/client.py`: `OVERVIEW_SCALE = 0.5`.
- Model-free tests (prompt assembly, findings accumulation, glossary labelling); `quality-standard.md` Dim-4 amended; docs synced.

**Success Criteria:**
- A fact the Brain writes to `findings` at step N is visible under CONFIRMED FINDINGS at every step > N (it cannot be dropped).
- CURRENT CONDITION shows a `shell` action's `/exec` output as the result and marks the screen unchanged; a visual action's result points at the current screen.
- HISTORY lines carry the compact `note`.
- Glossary is source-labelled; `OVERVIEW_SCALE` is 0.5; all model-free tests pass; ruff clean.
- The trust-split prose does not re-open the clear-loop (over-trusting screen memory) nor the re-doubt loop (under-trusting facts).

---

## Alternatives Rejected

- **Brain rewrites the findings block each step**: lets it prune freely, but re-introduces the exact forgetting bug — a fact it forgets, it won't re-emit.
- **Full `thought` in history**: reverts the 07-13 regression — verbose reasoning blurs the context.
- **External scratchpad via shell/`/tmp`**: the brittle DIY the Brain attempted in the failing run (broke on `sh`-vs-`bash`), off-context and indirect.
- **Prompt reorder only (carry no data)**: cheapest, but the facts still vanish — it doesn't fix the failure.
- **A separate persistent `/exec` result line (the literal draft)**: overlaps the channel-aware "result of last action"; folded into one channel-aware line to avoid an empty/N-A slot the Brain must reason around. (Durable shell results live in CONFIRMED FINDINGS.)

---

## Relationship to ADR-004, ADR-005, ADR-006

Keeps [ADR-005](2026-07-16-structured-output-standard.md)'s forced tool-calling (Amendment 2) — `findings`/`note` are just new fields on the tool schema, validated by our Pydantic guard. Amends the [ADR-004](2026-07-16-foveal-describe-trim.md) OVERVIEW scale (0.375 → 0.5) after the 07-18 evidence that 0.375 is unreadable on dense result pages. Reuses [ADR-006](2026-07-17-embodiment-selection.md)'s profile system (the glossary labelling is in the same `_join`).

**Out of scope (separate follow-up):** the q3-8b numeric/price-misread reliability issue (a banked *wrong* finding persists until corrected). **→ RESOLVED same day** by [ADR-004](2026-07-16-foveal-describe-trim.md) Amendment 1 — measurement showed the fix is a simple `DESCRIBE_MODEL` swap (qwen3-vl-8b → 30b-a3b), which reads discounted prices correctly; the "route numeric reads to the 72B" idea was obsoleted.

---

**Full context**: [High Wizard plan](../../plans/2026-07-18-bryes-brain-prompt-restructure.md)
