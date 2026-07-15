---
project: BRYES
title: Backlog — Tech Debts & Next Steps
updated: 2026-07-15
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
- [ ] **Phase 5 — verify-and-recover** (the product): after each action, check "did the intended
      thing happen?" and recover instead of marching on. **Deferred until base capability clears
      ~80%** of tasks. **The gap** (pinpointed 2026-07-15 on the phone "open Settings" run): the loop
      feeds current-`describe` + actions-only history but **no state-delta**, so the Brain *infers*
      what its actions did ("scrolled twice, suggesting I'm at the bottom") instead of being told —
      it can't detect a no-op and wanders. Two failure shapes to catch: **no effect** and **wrong
      effect**. **Design worked out 2026-07-15 (ready to `/high-wizard`):**
    - **Layer 1 — pixel no-op detector** (deterministic, ~free, Brain-independent): compare this
      step's top-of-step screenshot to the previous one; if effectively identical, tell the Brain
      *"your last action changed nothing."* Catches the exact failure the Brain is blind to (each
      `describe` is independent → it narrates an unchanged screen as fresh). Mechanism = `frame_diff`:
      downscale both frames to ~64×64 grayscale, mean-abs-diff, threshold — downscaling washes out
      cursor/clock noise; **threshold tuned empirically** (log no-op vs real-change diffs, don't
      guess). Only fire after *state-changing* actions (not `wait`/`screenshot`).
    - **Layer 2 — `expect` verified in the VLM** (cheap, grounded, SAME describe call): the Brain
      emits a checkable `expect` with its action; the loop carries it into the next `describe`
      (exactly like `focus` already rides along); the **VLM verifies it against pixels** ("VERIFY:
      'Settings app is open' → FALSE; still on the home launcher"). Grounded, not inferred (dodges
      Seam A + Brain rationalization), no extra call. **Bias `expect` toward ABSOLUTE/nameable
      target-states** ("an icon labeled 'Settings' is visible") not relative ("new apps appeared") —
      then the *current* frame suffices, no diff needed. **Trap:** VLMs confirm eagerly — the verify
      prompt must be **neutral/disconfirming** ("if it is NOT true, say so and report what IS shown"),
      same no-infer discipline as `DESCRIBE_PROMPT`.
    - **Escalation ladder (cost→need):** ① pixel no-op diff (free, "did anything move?") → ② `expect`
      in the describe (cheap, grounded, "is my target true now?") → ③ **two-image VLM diff** — the
      Brain **requests** it *only when stuck / verification is inconclusive*; the loop feeds prev+current
      to the VLM → "what SPECIFICALLY changed", and returns that **to the Brain**. Frame it in the
      **system prompt as EXPENSIVE + SLOW — use sparingly, only when truly stuck** (a 2-image call is
      heavier than the describe we're already trying to shrink). Gated behind "something's wrong", never
      every step.
    - **Constraints:** compact signals only; do NOT re-feed full past describes (re-blurs — the reason
      history went actions-only on 2026-07-13); the common path (①+②) adds **zero** extra VLM calls.
    - **Open (decide at build):** whether Layer 1 is still needed once Layer 2's `expect`-check is in
      (test it — the past no-op failures were all *pre-*`expect`); recovery = pure Think-High reasoning
      on the signal vs a hard backstop (same no-op ×N → force-different). The `frame_diff` primitive
      built for Layer 1 also becomes the trigger for **incremental/change-driven describe** in the
      separate *describe-speed* thread (small diff → describe just the changed tile) — one primitive,
      two threads.

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
- **`describe` (Qwen-VL) is the per-step bottleneck** — good for faithfulness, but it's the
  highest-volume call (every step), the biggest token cost, AND (measured 2026-07-15) the dominant
  *latency*: ~19.5s/step on the container vs ~3.2s for `decide`; the phone's larger 1080×2400 frame
  is likely worse. The lever for loop speed. Options: **downscale the frame before `describe`** (the
  Eyes' `locate` already rescales coords, so it's safe), a faster VLM, or skip-`describe`-when-frame-
  unchanged.
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
