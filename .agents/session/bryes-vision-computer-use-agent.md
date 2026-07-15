# BRYES — Vision-Based Computer-Use Agent

Brain-Eyes: a phase-by-phase computer-use agent (screenshot → decide → click) built
from `roadmap.md`. Project context: [architecture-overview](../../docs/architecture-overview.md).

---

### [2026-07-14 10.15] (agent: software-architect) — HANDS NATURAL SET + REGRESSION TEST + `wait`/`screenshot` ACTIONS → BROWSER TASK WORKS ON TOKOPEDIA 🤖👁️🛒✅

**Session theme**: Turned the browser-generalization *proof* into a real, working browser *task*. Completed the Hands primitive set, built a deterministic regression test, added the two loop-level actions the agent was missing (`wait`, `screenshot`), and drove the whole thing to search Tokopedia and capture page-1 results — end to end, on a real commercial site.

**What happened**:
- **Hands primitive audit → full natural set** (the 2026-07-13 next-step): audited every primitive against the `type` lesson (no hidden action that clobbers caller-set state). Verdict: `type`/`key` clean-atomic; `click` naturally-composite-and-safe (move-then-click clobbers nothing — resisted over-decomposing it); `move` was a dead primitive → renamed **`hover`** and wired to the Brain. No second `type`-class bug. The real gap was *coverage* → added the missing natural actions **`double_click` / `right_click` / `hover` / `scroll` (direction/amount) / `drag` (target→destination)**, each ONE atomic xdotool call, across server + Brain vocab + loop in lockstep.
- **Deterministic regression test + `/pointer`**: added a read-only **`GET /pointer`** (xdotool getmouselocation) so point actions can be asserted without a VLM. New **`screen/test_hands.py`**: 5 model-free checks (all execute; bad payloads 400; hover/click/double_click/scroll land the pointer; drag ends at destination; right_click opens the menu) — all green live. Movement of every primitive now live-verified.
- **Chrome auto-boot + vision-first clarity**: the entrypoint now launches Chrome at `CHROME_START_URL` (default google.com); gnome-calculator + xterm stay installed for on-demand launch, not auto-started. Answered Alvi's Q — the agent is **vision-first** (no shell channel; Chrome-at-boot is the *container's* job, not the agent's), so xterm isn't needed for browsing.
- **Tokopedia take 1 — premature `done`**: searched 'DDR5 5600 SODIMM' correctly (exact query, correct results URL, **no bot-wall** — my #1 risk flag was wrong), but called `done` ~1–2s early on a **loading spinner**; describe honestly said "appears to be a search results page" (true from URL/title) but zero products rendered. Root: no wait/verify; `settle=0.6s` far too short for an async SPA.
- **`wait` action** — the Brain *confessed the gap* (step 4: *"I must take an action and cannot explicitly wait"* → scrolled as a workaround). Added a loop-level **`wait`** with **Brain-chosen `seconds`** (clamped 0.5–30s ≈ API timeout, chainable), no UI touch, re-observe next step.
- **`screenshot` action** — added a loop-level **`screenshot`**: the Brain saves the current frame as a `capture-NN.png` **deliverable** (distinct from per-step diagnostic frames). Enables the "multiple screenshots to cover an infinite-scroll page" pattern.
- **Tokopedia take 2 — clean win**: search → **`wait`** on spinner → products visible → **screenshot** → scroll → screenshot → scroll → screenshot → **`done`** in **10 steps**. Pixel-verified `capture-01/02/03.png`: three DISTINCT scrolled screenfuls of real DDR5 5600 SODIMM listings with prices. No thrash, no premature-done.
- **Infinite-scroll learning**: Tokopedia has no pagination (infinite scroll) → "all of page 1" is undefined; the earlier scroll-forever step-limit run was chasing a non-existent stop. A capture task needs an explicit bound.

**Co-build texture**: Alvi caught my over-engineering fast — I answered "make a test draft" with a whole testing *standard* (tiers/conventions, heading toward `/setup-qa-instrument`); he cut it ("we don't need that, only a mechanism to test the new hands") and I deleted it, keeping just `test_hands.py`. He drove the key calls: `move`→`hover`, the full natural set, Brain-chosen `wait` seconds, the `screenshot` action, 30s clamp, Chrome-at-boot. Empirical throughout — every capability added was the harness giving the Brain what it needed; the thesis held again (`wait`+`screenshot` were the fixes, not a smarter model).

**Outcomes**:
- Commits `66819a8` (natural set + audit) → `b217c16` (regression test + `/pointer`) pushed; the `wait`/`screenshot`/Chrome-boot batch committed at wrap-up. Browser task works end-to-end on Tokopedia.
- **Tech debts**:
  - **Infinite-scroll has no natural stop** — capture tasks need an explicit bound (count / target / N screenshots).
  - **Some hands app-behavior unconfirmed** — `scroll` confirmed live on Tokopedia; `double_click`/`right_click`/`drag` on a real surface still eyeball-pending.
  - **Phase 5 (verify-and-recover) still deferred** (until ≥80% base) — `wait` is a partial mitigation, not the verify step.
  - **Brain still validated on few tasks** — calc suite still un-run; qwen3.6-flash now also proven on the Tokopedia capture task.
- **Next steps**:
  - **Give BRYES a WhatsApp messaging task** (Alvi's vision — drive WhatsApp Web to chat with / help anyone who messages its number; the first genuinely *useful* real-world task, toward the legendary-ecosystem goal).
  - **Define an infinite-scroll capture stop-condition** (count / target / N screenshots).
  - **Confirm remaining app-level hands behavior** (double_click / right_click / drag).
  - **Validate qwen3.6-flash on the calculator suite.**
  - **Phase 5** once base capability clears ~80%.

---

### [2026-07-13 01.50] (agent: software-architect) — THE PERCEPTION ROOT FIXED (VLM DESCRIBE) + ATOMIC PRIMITIVES + 5-MODEL BAKE-OFF → qwen3.6-flash 🤖👁️🧠💸

**Session theme**: Reliability + generalization pass on the loop, then a model bake-off. Chased every recurring failure to its true root (empirically, on real screenshots), generalized the agent from the calculator to a real browser, and picked the Brain on evidence. Phase 5 (verify-and-recover) deliberately deprioritized — Alvi's framing: solve it *after* 80%+ of tasks run well, since most failures were the harness sabotaging a capable Brain, not the Brain.

**What happened**:
- **Loop seeds** (from the 2026-07-11 tech debts): (1) Think High (`reasoning.effort=high`, max_tokens→8192) + JSON-retry robustness; (2) task-directed `describe(focus)` — Brain steers the Eyes; (3) a FOLLOW-THE-OBSERVED-STATE guide + disambiguate-by-position naming ("the equals button ON THE KEYPAD" — else `locate` grabs the "=" in the displayed equation) + global English-only (flash reasoned in Chinese).
- **Tightened `describe` (no-infer)** killed a **confabulated-result false "done"**: UI-TARS reported a *result* (`12979.79`) on an un-evaluated `943104÷73` — Alvi caught in the transcript that the fault was the *Eyes*, not the Brain.
- **THE DECISIVE FIX — VLM describe**: the recurring **history-vs-live clear-loop** (the original 1024 root) was **`describe`, not Brain judgment** — UI-TARS (a Qwen2.5-VL *grounding* fine-tune) flattens a history/log into the current state. Swapped `describe` → **`qwen/qwen2.5-vl-72b-instruct`** (keep UI-TARS for `locate`). It explicitly labels *live entry* vs *history* → the clear-loop that four rounds of prompt-tuning couldn't fix vanished. `12+34+56=102` on a **cluttered** calculator (a `7÷8` result in history) ran clean.
- **`runlog.py`** — per-run transcript logger (every prompt + raw reply + screenshot under `artifacts/runs/`); it's what localized every fault above.
- **History → actions-only** (Alvi's catch): pairing observation+action was made obsolete by the accurate-but-verbose VLM describe — the stacked past observations *blurred* the context. Now history carries only the `did` actions; the Brain judges from the current observation.
- **`type` root cause** (Alvi rejected my band-aid): the logged HANDS payloads proved `type` fired a **click first**, which deselected the Brain's Ctrl+A → append. Fix = **`type` just types** (atomic primitive); the Brain focuses via explicit `click`. Principle Alvi named: **primitives stay dumb/atomic; composition belongs one level up.**
- **Browser generalization**: baked **Google Chrome** into the Dockerfile (apt `chromium` on 24.04 is a *snap shim* that won't run in a container → use the official `.deb`; launch `--no-sandbox`). Agent searched **"who am I"** in Chrome.
- **5-model Brain bake-off** (generic goal `"Search the web using google chrome for the query: who am I"`): all 5 searched successfully; **qwen3.6-flash & hy3 (4 steps) and v4-flash (cheapest, $0.0013/run) beat v4-pro (6 steps, $0.0137) and minimax-m3 (never stopped → step_limit, $0.0296)** on BOTH cost and capability. **v4-flash rehabilitated** — its earlier "flakiness" was describe garbage-in. **Default Brain → `qwen/qwen3.6-flash`** (4 steps, 1M ctx, ~$0.0023/run). `brain_model` now threadable per run.

**Co-build texture**: Alvi's catches drove nearly every root-cause: "the fault is the Eyes describe" (VLM swap), "history is blurring the execution" (actions-only), "that [ctrl+A] is unnatural — find the real root" (type-just-types), the atomic-primitives principle, "why fluxbox / why not chrome" (real Chrome via .deb), and the generic-goal insight (don't pamper the task). Empirical throughout — every root proven from the logged transcript, not guessed. Honest self-corrections: mis-attributed the confabulation to the Brain, over-estimated v4-pro's cost (real data 3× my estimate), proposed a band-aid type-fix — each corrected on evidence.

**Outcomes**:
- Verified clean end-to-end: calcs `1550×3÷4=1162.5`, `128+47=175`, `512−137=375`, `7÷8=0.875`, `12+34+56=102` (on clutter); browser `who am I` search on all 5 models. Commits `07b7ea9 → b6f8bd0 → 4b9097b` pushed.
- **Tech debts**:
  - **Phase 5 (verify-and-recover) still the product** — deferred until base capability ≥80% (Alvi's sequencing). No explicit "did it land?" check yet.
  - **Localized docs stale**: `architecture-overview.md` + `agent-loop-flow.md` don't yet reflect Chrome, `type`-just-types, the qwen3.6-flash default, or the bake-off.
  - **Brain choice validated on ONE task** (browser). Not yet re-run on the calculator suite.
  - **MiniMax M3 needs hand-holding** — did the search but never recognized completion on the generic goal; only worked with the pampered instruction.
- **Next steps**:
  - **Audit every hands primitive for basic/natural (atomic) behavior** — `type` was one; make sure `click`/`key`/`move` don't bundle extra behavior.
  - **Add a combo/macro action** — e.g. `ctrl+a → type "who am I" → Enter` as one composite command the Brain can issue.
  - **Validate `qwen3.6-flash` on the calculator suite** before fully trusting the default.
  - **Refresh the localized docs** (Chrome env, type-just-types, qwen3.6-flash, bake-off table).
  - Build **Phase 5** once base capability clears ~80%.

---

### [2026-07-11 23.41] (agent: software-architect) — PHASES 1–4 BUILT: THE LOOP CLOSES (7+8, 100×3 unattended) + THE 1024 FAILURE DIAGNOSIS + gnome-calculator WIN 🤖👁️🧠

**Session theme**: First BRYES session. Built the vision-based computer-use agent MVP end
to end — Phases 1–4 of the roadmap — proving each piece live before chaining them, then
stress-testing the closed loop and fixing what broke.

**What happened**:
- **Phase 1 — The Screen**: Dockerized Ubuntu desktop (Xvfb + fluxbox + xdotool + scrot)
  with a Flask control API (`/health`, `/screenshot`, `/action{click,move,type,key}`) +
  noVNC live view. Started from Xvfb (avoided the "hand-roll a display server" trap).
  Fixed the fbsetbg wallpaper-warning popup by installing `feh`.
- **Phase 2 — The Eyes**: `bytedance/ui-tars-1.5-7b` grounding. **Load-bearing research**:
  UI-TARS-1.5 is Qwen2.5-VL based → coords in `smart_resize` space; convert
  `actual = model*orig/resized`. Proven live: located the "7" button → clicked it → calc
  showed 7. ~$0.00014/look.
- **Phase 3 — The Brain**: `deepseek/deepseek-v4-flash`, text-only, `decide(goal, obs,
  history)` → JSON action. Names targets by description (Eyes ground them later).
- **Phase 4 — Close the Loop**: `agent/loop.py` chains describe → decide → locate → act.
  Computed **7+8 = 15 unattended in 5 steps**. Then the harder **1024×921/73 FAILED** —
  thrashed 30 steps, never converged. Rich diagnosis (the point of Phase 4): (1) bare-symbol
  grounding — "the = button" mislocates, "equals" fixes it (coached the Brain); (2) NO verify
  → a missed click is invisible → infinite clear/retry; (3) `describe` too vague to track
  exact multi-digit display; (4) Brain has no progress model. Also fixed: DeepSeek reasoning
  tokens truncating the JSON (disabled reasoning + `max_tokens` 300→1024→4096), and the
  Windows cold-connection flake (HTTP retries).
- **Late-session decisions & tests** (with Alvi): confirmed `max_tokens` is a ceiling not a
  target; researched V4 thinking modes (no auto-bypass; Non-think for mechanical steps,
  Think High for planning); confirmed DeepSeek V4 is text-only → the describe→text→LLM
  handoff is a **lossy seam** (surfaced 2-model "VLM decides + grounder locates" vs current
  3-model split as an open architecture fork). **Swapped `xcalc` → `gnome-calculator`**
  (needs `dbus-x11`): far more readable, killed the `describe` "input fields" hallucination,
  and **`100×3 = 300` ran clean in 7 steps** — multi-digit entry that catastrophically
  failed on xcalc now works, because bigger buttons ground reliably.

**Co-build texture**: Alvi drove the phase cadence ("let's try", "yes it should be A") and
generated the sharp catches — the .env "you never see it" mechanism, the "does V4-flash
accept images?" probe that exposed the lossy seam, the "screenshot is ugly" push to a better
app, and the closing "task-directed describe should be a Brain→Eyes feed" insight. Empirical
throughout: every claim proven on a real screenshot, failures diagnosed not hand-waved.

**Outcomes**:
- Shipped: Phases 0–4 (working MVP), 6 commits pushed to github.com/alvseek/BRYES, project
  context created, gnome-calculator upgrade.

- **Tech debts**:
  - **No verify-and-recover** (Phase 5 — "the product"): a missed click is invisible; the
    loop can't self-heal. This is the single biggest gap the 1024 run exposed.
  - **`describe` is vague/unstructured**: doesn't reliably report the exact display value or
    a complete button inventory; still free prose. Needs structured output (`{app, display,
    buttons[], windows[]}`) and/or a stronger describe model.
  - **Multi-digit entry via per-digit clicks is fragile** (each click = a grounding risk).
    `type "1024"` (keyboard, no grounding) would collapse the risk — not yet done.
  - **Open architecture fork undecided**: 3-model (UI-TARS describe + UI-TARS locate +
    DeepSeek decide) vs 2-model (one strong VLM perceives+decides, UI-TARS grounds). The
    describe→text→LLM handoff is lossy.
  - **Reasoning-mode decision (A/B) not finalized**: Non-think base + Think High recovery
    (leaning A) vs always Think High. Evidence favors A (thinking ran long even on trivial
    steps).

- **Next steps**:
  - Build **Phase 5 (verify-and-recover)**: after each action, check "did the intended thing
    happen?"; recover (re-locate / retry / re-plan) instead of marching on. Discuss depth
    with Alvi first (verify = new VLM/Brain call vs cheaper check; retry-action vs re-plan).
  - Improve **`describe`**: structured output + **task-directed** — the Brain feeds the Eyes
    WHAT to focus on ("describe the calculator in detail, we're calculating"). Brain→Eyes
    direction. Tied to the VLM-vs-UI-TARS-for-describe question (bake-off on the same
    screenshot: Qwen3.5-flash / Gemini Flash / gpt-5-nano vs UI-TARS).
  - Decide the **2-model vs 3-model** architecture.
  - Consider **typing digits** instead of clicking them.

**Promotions**: → [architecture-overview](../../docs/architecture-overview.md) (created — BRYES project context: 4-piece architecture, model slugs, load-bearing technical facts).
