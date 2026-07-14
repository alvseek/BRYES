---
project: BRYES
title: Backlog — Tech Debts & Next Steps
updated: 2026-07-14
---

# BRYES — Backlog

Living list of open work: **tech debts** (known gaps/risks) and **next steps** (what to do
next). Keep it current — check items off, add new ones as they surface. The phase plan lives
in [../roadmap.md](../roadmap.md); this is the finer-grained "what's left right now."

## Next steps (do these next)

- [ ] **Give BRYES a WhatsApp messaging task** (Alvi's vision — the next big goal): drive
      WhatsApp Web so the agent can chat with / help anyone who messages its number. The first
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
- [ ] **Phase 5 — verify-and-recover** (the product): after each action, check "did the
      intended thing happen?" and recover instead of marching on. **Deferred until base
      capability clears ~80%** of tasks (Alvi's sequencing — most failures so far were the
      harness sabotaging a capable Brain, not the Brain).

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
- **`describe` (Qwen-VL) is verbose** — good for faithfulness, but it's the highest-volume
  call (every step) and the biggest token cost. Matters at scale (Phase 6), not now.
- **Cost at scale unmeasured** — per-run is cents in prototyping; the every-step `describe`
  is the line item to watch if usage grows (Phase 6 hosting question).

## Recently resolved (for context)

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
