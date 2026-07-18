# ADR-004: Two-Mode Foveal Describe + Trim (describe-speed)

**Date**: 2026-07-16

**Status**: Accepted

---

## Problem

`describe` was BRYES's per-step bottleneck — **5–16s** on the 72B VLM (Qwen2.5-VL-72B), the #1 tech debt after Phase 5. The naive fixes (a faster model, or downscaling the frame) each looked plausible but attacked the wrong thing.

A full-session bake-off (`artifacts/bakeoff/`) found the **load-bearing fact**: describe latency is dominated by **output length**, not model or image size. The proof is stark — the *same* 72B, on the *same* frame, **boxes in ~1.5s but describes in 5–16s**. The 72B isn't slow; generating a paragraph is. Prefill (image encode) is ~1s; the rest is token generation.

So the real lever is *say less, about less* — which is how human vision already works: cheap low-acuity gist everywhere, sharp high-acuity detail only where the fovea points.

---

## Decision

**We decided to** give the Eyes **two describe modes** (foveal vision) and demote 72B from the default describer to the **authoritative-Eyes escalation**:

- **OVERVIEW** (`describe` with **no `focus`**): downscale the full frame (×0.5) and ask the fast **qwen3-vl-8b** for a coarse gist — environment / apps / anything eye-catching. Cheap; the *salience* it surfaces is the cue that tells the Brain where to `focus` next. Downscaling is safe **only here** (gist needs no acuity).
- **TRIM** (`describe` with **`focus`**): **72B `box()`es** the named region → the client **crops** it (+15% pad, full resolution) → **qwen3-vl-8b describes the crop**. A small clean crop is both fast *and* faithful (the bake-off's hard-crop test: no confabulation, read `Rp759` vs a struck `Rp799`, clean on cluttered calc displays). `expect` (which now **requires** `focus`) rides the crop as the `VERIFICATION:` report (ADR-003).
- **Escalation ladder**: `q3-8b` crop-describe (default) → **`recheck`** (Brain-gated 72B re-read of the same region, on an `expect`-mismatch) → **`request_diff`** (existing 72B 2-image diff). 72B is the *authoritative Eyes* — it boxes and it re-reads when the fast read is doubted.

Thinking is **off** on every describe call (measured **14× latency for zero accuracy gain**).

**Why we chose this:**
- **Latency ∝ output length** — trim cuts both the region *and* what there is to say; overview is gist. Downscaling (prefill) is the small half, kept only for the overview.
- **Trim makes cheap models reliable** — small VLMs confabulate/flatten on full busy frames but are faithful on a trimmed crop (nothing to hallucinate). This is *why* q3-8b is safe here, and only here.
- **72B is the accurate boxer** — in the bake-off it boxed 4/4 including small targets; the small VLMs mislocated to blank regions. Boxing is cheap on 72B (~1.5s) because a box is ~4 output tokens.
- **Trim needs a box, not a point** — the exact capability ADR-003 shelved (UI-TARS only points). General Qwen-VL emits absolute boxes; validated below.

Result, live: describe dropped to **1.8–3.3s** per step and moved **under** `decide` (the Brain) — the bottleneck is no longer the Eyes.

---

## Coordinate convention (validated)

Qwen2.5-VL emits **absolute pixel coordinates** (unlike UI-TARS' `smart_resize` space). Validated at **both** 1280×800 and **2560×1600 (4.1M px, above the model's ~2.1M-px clamp)**: raw coords land dead-on at both — the model returns absolute even when it internally downscales. So `box()` takes coords **as-is**, no conversion or pre-scale. (A deterministic pre-scale-to-≤2M backup was designed but proved unnecessary.)

---

## What was built (Requirements)

- **`eyes/client.py`**: new `box(image, target) -> (x1,y1,x2,y2) | None` on `BOX_MODEL` (72B); `describe(image, focus, expect, *, careful=False)` mode switch; `_downscale` / `_crop` / `_expect_block` helpers; `OVERVIEW_PROMPT` + `CROP_PROMPT`; `DESCRIBE_MODEL`→q3-8b, `CAREFUL_MODEL`=72B; `NO_THINK` + a `reasoning` kwarg on `_ask`. Robustness: unparseable **or failed** box → `None` → full-frame describe (the only fallback — geometry can't catch a confidently-wrong box; 72B accuracy + the ladder cover that); `_ask` raises a clear error on a missing-`choices` body.
- **`brain/client.py`**: `recheck` schema field; `expect` **requires** `focus`; a RE-READ-A-DOUBTFUL-REPORT rule situating `recheck` on the ladder.
- **`agent/loop.py`**: threads `recheck` → next `describe(..., careful=True)` (mirrors `request_diff`); an unchanged describe call site otherwise.
- **`screen/docker-compose.yml`**: `SCREEN_RESOLUTION` made overridable (high-res / 1:1 knob).
- **`eyes/test_describe.py`**: deterministic, model-free regression test (helpers + mode routing).

**Success Criteria (met, live):**
- Clean browser task `done` in 4 steps: OVERVIEW gist (1.8s) → TRIM + `VERIFICATION:` (2.8/3.3s) → results. describe **1.8–3.3s** every step (vs 5–16s), **under** `decide`.
- Faithful throughout; no confabulation; box validated at 1280×800 **and** 2560×1600.

---

## Alternatives Rejected

- **A faster describe model on the full frame** — small VLMs mislocate/confabulate on full busy frames (boxing 0/4 on small targets); reintroduces the faithfulness bugs Phase-5 removed.
- **Downscale the full frame** — model-independent but touches only prefill (~1s, the small half) and *hurts* exact reading; kept for the overview only.
- **Skip describe when the frame is unchanged** (`framediff.py`) — orthogonal; doesn't speed the describes that *do* run. Still parked.
- **Structured / short-output describe, same frame** — helps, but the model still processes the whole busy frame and can't isolate the region.
- **`box()` applies a `smart_resize` conversion** — designed as robustness, but 72B returns absolute at all resolutions, so a conversion would *corrupt* correct coords. Raw is correct.
- **Geometric box-fail detection** (area thresholds, whole-frame checks) — geometry can't detect a *confidently-wrong* box; only unparseable/failed → full-frame fallback. 72B accuracy + the `recheck`/`request_diff` ladder cover mislocation.
- **Two names collapsed / automatic recheck** — the loop can't semantically compare `expect` vs reality (that's Brain judgment) and confident misreads don't announce themselves, so `recheck` is Brain-gated on a concrete `expect`-mismatch signal.
- **Include phone-body (tall-aspect) boxing in this change** — the *resolution* concern is the real risk and is closed by the 4M container test; the phone *body* is a separate follow-up (needs a live device).

---

## Relationship to ADR-001 / ADR-002 / ADR-003

Extends **ADR-003**: the escalation ladder (`recheck` → `request_diff`) grows the change-feedback family, and `expect`⇒`focus` makes verification always regional — it now rides a *trimmed crop*, not a full-frame prompt. Orthogonal to **ADR-001** (effector tier) and **ADR-002** (body): trim/overview run on whatever body's Eyes are active. The trim's boxer answers the "did ADR-003 shelve boxing forever?" question — no, general Qwen-VL boxes; UI-TARS just couldn't.

---

**Full context**: [High Wizard plan](../../plans/2026-07-16-bryes-foveal-describe-trim.md) · **Evidence**: `artifacts/bakeoff/`

---

## Amendment 1 (2026-07-18): `DESCRIBE_MODEL` qwen3-vl-8b → qwen3-vl-30b-a3b-instruct

The default crop/overview describer is changed from `qwen/qwen3-vl-8b-instruct` to **`qwen/qwen3-vl-30b-a3b-instruct`** (a Qwen3-VL MoE, ~3B active params). `BOX_MODEL` / `CAREFUL_MODEL` (the 72B authoritative Eyes) are unchanged; thinking stays OFF.

**Why (measured, same-crop 3× at temperature 0):** the 8b **systematically misread discounted Tokopedia price cards** — read `Rp2.105.000` as `Rp1.050.000`, **byte-identical across passes** (a repeatable perceptual error on the struck-original + badge layout, NOT sampling noise) — which silently produced a *wrong* answer even after the [ADR-007](2026-07-18-brain-prompt-restructure.md) convergence fix. Model bake-off on the same crop:

| Model | Discount read | Latency (typ.) | $in/$out per M |
|---|---|---|---|
| qwen3-vl-8b (old) | ❌ wrong (2.1M→1.0M) | ~6s | 0.117 / 0.455 |
| **qwen3-vl-30b-a3b (new)** | ✅ correct 3/3, lists only current | **~3.7s** (occasional 20–30s spike) | 0.130 / 0.520 |
| qwen3-vl-32b | ✅ correct, slower | ~11s | 0.104 / 0.416 |
| qwen2.5-vl-72b | ✅ correct | ~9s | 0.800 / 1.000 |

30b-a3b is a **near-strict upgrade**: more accurate on dense/discounted layouts, **faster** than the 8b (MoE), and cleaner (reports only the current price). Thinking was tested and rejected: `8b-thinking` reads correctly but takes 40–115s; `30b-a3b-thinking` *degraded* accuracy — confirming "thinking off" for perception. This obsoletes the [ADR-007](2026-07-18-brain-prompt-restructure.md) "route numeric reads to the 72B" follow-up (a model swap is simpler and covers it). **Validated live**: the exact Tokopedia task now reads MX4 at ~2.1M and lands the correct verdict ("MX4 dearer by Rp378.980"), where every prior run was backwards. *(Latency spikes on 30b-a3b are provider-variance — worth monitoring.)*
