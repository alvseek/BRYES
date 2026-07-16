---
project: BRYES
title: Backlog — Tech Debts & Next Steps
updated: 2026-07-16
---

# BRYES — Backlog

Living list of open work: **tech debts** (known gaps/risks) and **next steps** (what to do
next). Keep it current — check items off, add new ones as they surface. The phase plan lives
in [../roadmap.md](../roadmap.md); this is the finer-grained "what's left right now."

## Next steps (do these next)

- [ ] **Give BRYES a WhatsApp messaging task** (Alvi's vision — the next big goal): chat with /
      help anyone who messages its number. The **`PhoneDevice` body now exists** (a real Android over
      adb/USB), so WhatsApp *on the real phone* is now an option alongside WhatsApp Web — but the
      change-feedback gap (Phase 5, below) limits multi-step phone-task completion today. The first
      genuinely *useful* real-world task; a step toward the legendary-ecosystem vision.
- [ ] **Define an infinite-scroll capture stop-condition** — Tokopedia has no pagination
      (infinite scroll), so "all of page 1" is undefined. A capture task needs an explicit
      bound: a product count, a target item, or N screenshots (the bounded `screenshot`-×N
      approach worked cleanly on 2026-07-14).
- [ ] **Confirm the remaining app-level hands behavior** — `scroll` is now confirmed app-level
      (Tokopedia results scrolled through distinct screenfuls, 2026-07-14). Still eyeball-only:
      `double_click` selects, `right_click` context menu, `drag` on a draggable surface.
- [ ] **Add a combo/macro action** — a composite the Brain can issue in one shot, e.g.
      `ctrl+a → type "who am I" → Enter`. Built from the atomic primitives, sequenced above
      them (not baked into any single primitive). The atomic set to compose from is now the
      full natural set (below).
- [ ] **Validate `qwen3.6-flash` on the calculator suite** (`1550×3÷4`, `128+47`, `512−137`,
      `7÷8`, `12+34+56` on clutter) before fully trusting it as the default Brain — it was
      only crowned on ONE task (browser search).
- [x] **Phase 5 — verify-and-recover** ✅ **DONE (2026-07-16, [ADR-003](adr/2026-07-16-change-feedback-verify-and-recover.md)).** Shipped as **Layer 2 (`expect` verified in the VLM) as the primary change-feedback** + Layer 3 (Brain-requested 2-image diff) + a recovery backstop (same-action-and-failing → escalate). **The original screen-wide pixel "Layer 1" was dropped** after measurement: a single typed digit (~0.02–0.09 mean-diff) sits below the idle noise floor (~0.25), and UI-TARS can't box a region to crop → "did my action work?" is a regional/semantic question the VLM answers, not a pixel metric. `framediff.py` is kept & parked (see Recently resolved + the describe-speed lever above).

## Tech debts (known gaps / risks)

- **Some hands app-behavior still unconfirmed** — `scroll` is now confirmed app-level on
  Tokopedia; `double_click` / `right_click` / `drag` behavior on a real surface is still
  unverified. (See next-steps confirm item.)
- **Infinite-scroll has no natural stop** — pages like Tokopedia lazy-load forever, so a
  "cover the whole results" task can't terminate on pagination; it needs an explicit bound.
- **No explicit verify-and-recover** — the loop infers progress implicitly from the next
  observation; a missed click isn't deliberately caught. (Same as Phase 5 above.)
- **Brain choice validated on one task only** (browser search). Not yet the calculator suite.
- **MiniMax M3 needs hand-holding** — it *did* the search but never recognized completion on
  the generic goal; only finished with a pampered, step-by-step instruction. Sensitive to
  instruction specificity; not a safe default.
- **`decide` (the Brain) is now the dominant loop latency** (3–12s/step, high-variance under
  `reasoning.effort=high`). **`describe` is SOLVED** — the two-mode foveal describe
  ([ADR-004](adr/2026-07-16-foveal-describe-trim.md)) cut it from 5–16s to ~2s (OVERVIEW downscaled
  gist / TRIM 72B-box → crop → q3-8b), moving the bottleneck off the Eyes and onto the Brain. The
  next latency lever, if it matters, is a faster/lighter `decide` config or model; `framediff.py`
  (skip-describe-when-unchanged) is still parked.
- **A box cache would save ~1.5s/step on stable focus regions.** TRIM does 2 calls (72B box +
  q3-8b describe); the box (~1.5s) dominates. A cache keyed by the focus-string would skip re-boxing
  a region that hasn't moved across steps. Follow-up (not yet built).
- **Phone-body boxing (tall aspect) untested.** The *resolution* concern for `box()` is CLOSED
  (validated at 2560×1600 / 4.1M px, absolute coords). The phone *body* (1080×2400 portrait, over adb)
  is a separate follow-up — the boxer should be spot-checked on a live phone frame before trusting TRIM there.
- **[experiment] Thinking `diff`?** `request_diff` (the top, stuck-only escalation rung) runs on the
  72B's non-thinking default. Its latency doesn't matter (it's the last resort), and 2-image
  change-detection with noise-filtering is more analytical than single-frame describe (where thinking
  measured useless) — so a *reasoning* VLM might read subtle changes better. Untested; needs a
  thinking-capable VLM + a measurement before adopting.
- **`decide` (Brain) call could stall the whole loop** — it caught only `HTTPError`, so a dropped/
  timed-out/slow-trickle connection hung or crashed the run (observed 2026-07-16: a step stalled in
  `decide`, *after* `describe` had completed). **Partially fixed**: `decide` now catches `URLError`/
  `TimeoutError`/`ConnectionError` and retries with backoff via its outer loop (mirrors `ContainerDevice`).
  Remaining: a genuinely slow-but-alive reasoning response isn't bounded (a total wall-clock cap would
  need a thread/alarm) — accepted for now.
- **Cost at scale unmeasured** — per-run is cents in prototyping; the every-step `describe`
  is the line item to watch if usage grows (Phase 6 hosting question).
- **Async `/exec` deferred** — `/exec` is synchronous (blocks the loop until done/timeout). The
  async/background+poll upgrade is a clean *additive* branch, deferred until the loop goes
  concurrent/multi-channel or long jobs get frequent (ADR-001). Until then: long-but-finite
  commands use an extended `timeout` (≤300s); very-long ones background with `&` + poll via `wait`.
- **Effector tiers only 2 of 3 built** — Tier 2 (shell) + Tier 3 (vision) exist; **Tier 1
  (API/MCP)** is named by ADR-001 but unbuilt. The next channels (a Tier-3 *persona* surface for
  WhatsApp; a Tier-1 API channel like email) will exercise whether the inherited pattern holds.

## Recently resolved (for context)

- **Describe-speed — two-mode foveal describe + trim, [ADR-004](adr/2026-07-16-foveal-describe-trim.md)** → `describe` cut from **5–16s to ~2s** (now *under* the Brain). Root: latency is **output-length-bound** (72B boxes in ~1.5s but describes in 5–16s, same frame). **OVERVIEW** (no focus): downscaled ×0.5 gist on **qwen3-vl-8b**. **TRIM** (focus): 72B `box()` → crop (+15%) → q3-8b describes the crop; `expect` now REQUIRES `focus` and rides the crop as `VERIFICATION`. 72B → authoritative Eyes (boxing + `recheck` careful re-read); ladder `q3-8b → recheck → request_diff`. Thinking off (14× cost, no gain). Qwen2.5-VL emits **absolute** box coords at any res (validated at 1280×800 **and** 2560×1600/4.1M px — no conversion). Box `None` (unparseable/failed) → full-frame fallback. Deterministic `eyes/test_describe.py`; live browser task `done` in 4 steps, describe 1.8–3.3s. (2026-07-16)
- **Phase 5 — verify-and-recover (change-feedback), [ADR-003](adr/2026-07-16-change-feedback-verify-and-recover.md)** → **Seam B closed** by giving the Brain a semantic post-action check. **Layer 2 (primary):** the Brain emits a `expect` with each action; `describe(…, expect=…)` **REPORTS that thing's actual state** → `VERIFICATION: <what's literally shown>` in the observation (grounded, no verdict — the Brain compares; regional via `focus`, ~free — rides describe). *(The Eyes report, the Brain judges — VLM binary verdicts proved noisy on 1024×4096: whitespace nitpicks, self-contradictions; descriptions were always accurate.)* **Layer 3:** `request_diff` → a Brain-gated 2-image `eyes.diff(prev, cur)` appended as "CHANGES SINCE YOUR LAST ACTION". **Recovery** lives in the Brain (off the report); the loop keeps only a dumb *advisory* guard on a repeated *identical* action; it never picks the action. `focus`/`expect`/`request_diff` now form one prospective describe-modifier family. **Dropped:** the screen-wide pixel no-op ("Layer 1") — whole-frame mean-diff can't separate a small real change from noise and UI-TARS can't box a crop region; `framediff.py` + `test_framediff.py` kept & parked for the describe-speed thread. Live-proven: "8+5" verified clean to `done`; an impossible task escalated fairly + broke the loop. Also hardened `decide` with a network retry. (2026-07-16)
- **Device abstraction (ADR-002) — Screen+Hands+shell behind a swappable `Device`** → the loop
  now depends on a `Device` Protocol (screenshot/act/optional shell + a `Capabilities` manifest),
  not a transport; `ContainerDevice` (HTTP, byte-identical) is the default body and **`PhoneDevice`
  (a real Android phone over adb/USB)** is body #2 — validated live (the unchanged loop drove the
  phone via `screencap`→describe→decide→`locate`→`input`). The Brain's action vocab is assembled
  from the active body's caps (a phone never sees `right_click`). (2026-07-15)
- **Per-phase loop timing** → `run()` prints + logs `screen / describe / decide / locate / act`
  seconds per step (+ totals). The first measurement corrected a wrong assumption: **`describe`
  (the 72B VLM) is the per-step bottleneck (~19.5s on the container), not the Brain's `decide`
  (~3.2s)** — the optimization target is `describe`, not Think High. (2026-07-15)
- **Shell effector channel (Tier 2) — `POST /exec` + `shell` action** → the Brain now runs
  non-interactive commands directly instead of driving the GUI for OS/file/CLI/network tasks:
  `/exec` runs `shell=True` in the sandboxed container (30s timeout, Brain-extendable to 300s,
  ~4 KB truncation, optional `stdin`, `errors="replace"`), and the result threads into HISTORY;
  the Brain prompt teaches tier-routing (shell vs vision) + non-interactive discipline. Verified
  live (`uname -r`, `find | wc -l`) + deterministic `test_shell.py`. Reframes BRYES as a
  **tool-using agent, vision = one tool** — see [ADR-001](adr/2026-07-15-effector-hierarchy.md). (2026-07-15)
- **`wait` + `screenshot` actions (validated live on Tokopedia)** → the Brain can now `wait`
  (Brain-chosen seconds, clamped 0.5–30s) for a loading page, and `screenshot` to save a
  deliverable frame (`capture-NN.png`, distinct from per-step diagnostic frames). Validated
  end-to-end: searched Tokopedia for 'DDR5 5600 SODIMM', **waited** out the results spinner,
  then **scroll + screenshot ×3** captured three distinct real screenfuls → clean `done` in
  10 steps. Browser generalization works on a real commercial site (no bot-wall). (2026-07-14)
- **Chrome auto-boots** → the Screen entrypoint launches Google Chrome at `CHROME_START_URL`
  (default google.com; per-task override); gnome-calculator + xterm stay installed for
  on-demand launch, not auto-started — clean browsing screen. (2026-07-14)
- **Hands regression test + `/pointer`** → added a read-only `/pointer` (mouse x,y) endpoint
  and `screen/test_hands.py`: 5 deterministic, model-free checks (all primitives execute; bad
  payloads 400; point actions land the pointer; drag ends at destination; right_click opens
  the menu). The new primitives' movement is now live-verified, not just static-checked. (2026-07-13)
- **Hands primitive audit + full natural set** → audited all primitives (`type`/`key` clean-
  atomic; `click` naturally-composite-and-safe; `move`→`hover`, now wired to the Brain); no
  second `type`-class bug found. Added the missing natural actions `double_click` /
  `right_click` / `hover` / `scroll` / `drag`, each one atomic xdotool call. (2026-07-13)
- **History-vs-live clear-loop** → fixed by moving `describe` to a VLM (Qwen2.5-VL-72B) that
  separates the live entry from history. (2026-07-13)
- **`type` append bug** → `type` made atomic (no click). (2026-07-13)
- **Confabulated-result false "done"** → tightened `describe` (no-infer). (2026-07-13)
- **Brain flakiness (Chinese output, state slips)** → mostly `describe` garbage-in; cleared
  by the VLM describe + English-only rule. Default Brain → `qwen3.6-flash`. (2026-07-13)
