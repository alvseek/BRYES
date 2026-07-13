---
project: BRYES
title: Backlog — Tech Debts & Next Steps
updated: 2026-07-13
---

# BRYES — Backlog

Living list of open work: **tech debts** (known gaps/risks) and **next steps** (what to do
next). Keep it current — check items off, add new ones as they surface. The phase plan lives
in [../roadmap.md](../roadmap.md); this is the finer-grained "what's left right now."

## Next steps (do these next)

- [ ] **Live-verify the new hands primitives** — `scroll` / `drag` / `double_click` /
      `right_click` / `hover` are static-checked only (compile + cross-layer consistency),
      never exercised on a real screen. Prove them in a container run (Chrome is the natural
      test: `scroll` a page, `right_click` a link, `double_click` to select).
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

- **New hands primitives not live-verified** — `scroll`/`drag`/`double_click`/`right_click`/
  `hover` pass static checks but have never touched a real screen; behaviour under real apps
  (esp. Chrome scroll amount, drag timing) is unconfirmed. (See next-steps live-verify item.)
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
