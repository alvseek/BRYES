# BRYES — Vision-Based Computer-Use Agent

Brain-Eyes: a phase-by-phase computer-use agent (screenshot → decide → click) built
from `roadmap.md`. Project context: [architecture-overview](../../docs/architecture-overview.md).

---

### [2026-07-16 20.36] (agent: software-architect) — STRUCTURED-OUTPUT STANDARD (ADR-005) + VERIFY-FOCUS FIX + FOCUS-FAILURE HARNESS + RESILIENCE FALLBACK — A MARATHON WHETSTONE ARC 🧱👁️🔧

**Session theme**: A long, tight co-design marathon that started from "let's try the latest implementation" on a raw calc task and turned into four coupled fixes, each surfaced by an Alvi catch: (1) LLM JSON should be **enforced by tools, not the AI** → the structured-output STANDARD (Pydantic + forced tool-calling + our validation, ADR-005); (2) the Brain was aiming the Eyes at the **control it pressed, not where the effect shows** → `focus`→`visual_focus` / `expect`→`visual_expectation`; (3) the Eyes **fabricated a crop** when the target wasn't visible → the focus-failure harness; (4) the Brain is **single-provider + degenerates** → qwen primary with a deepseek-v4-flash resilience fallback. Empirical throughout; measurement killed two of my own guesses.

**What happened**:
- **Raw-goal test + instrumentation-before-fixing (Alvi)**: ran the exact goal "Please calculate 1024*8096/112 using calculator" — no hand-holding. It crashed at step 10 (`Brain failed... finish_reason=error`). I proposed a backoff-retry fix; **Alvi: "how do you intend to fix without knowing the root cause?"** — conceded. Added two instrumentation lines (**save the trim crop** per step; **capture the raw failed decide body**) BEFORE fixing. The capture then caught the ground truth: a **1148-token reasoning-loop degeneration** ("click division, then 112, then equals" ×hundreds), `content:null`, Alibaba blaming "generating a JSON response for response_format." Root cause = model reasoning-spiral under loose `json_object`, NOT a network blip. My backoff guess was refuted.
- **Verify-focus (Alvi's novice-human analogy)**: crops proved q3-8b does NOT hallucinate — when it can't see the display it *says so*; the failure was that the Brain set `visual_focus` to the **keypad it was clicking** while `expect` was about the **display**. Rename `focus`→`visual_focus`, `expect`→`visual_expectation` + a sharpened "aim at where the EFFECT shows, not the control" prompt. Live: verification stopped going blind. + an operator-relapse fix ("keys don't light up; the operator shows in the display").
- **Structured standard (ADR-005)**: Alvi — *"without tight json we're beating around the bush; anything that needs format shouldn't be relied on the AI — enforce with scripts/tools."* Verified tool-calling support (deepseek-v4-flash 18/18 providers, qwen 1/1). Chose **Path A**: Pydantic `BrainAction` model → forced tool-call → **our Pydantic validation is the guard** (not provider enforcement — his load-bearing point: "don't rely on something that may not be available"). New `structured.py` (the reusable STANDARD), `decide()` refactored onto it, dropped `json_object`+prose-schema+regex-scrape. Live on v4-flash: zero JSON crashes, malformed-JSON class eliminated.
- **Focus-failure harness (Alvi's minimize diagnosis)**: the calc got minimized by a click; `box()` then **fabricated coords on a popup** instead of admitting absence. Fix: `box()` answers `NOT_FOUND` (no guessing) → `describe()` emits `VISUAL_FOCUS FAILED` + an overview → the Brain re-orients (overview awareness added). Then **Alvi caught a false-NOT_FOUND** (display visible, box bailed) → recalibrated `BOX_PROMPT` (NOT_FOUND only for genuine absence). Targeted box test: **0/9 false-negatives**, and it *refuted my concise-phrasing guess* (verbose phrases box the display MORE precisely) → reverted.
- **Model decision (Alvi flip-flopped, landed clean)**: pulled fresh OpenRouter pricing + provider counts. **qwen3.6-flash is Alibaba-only (1 provider); deepseek-v4-flash has 18** and is ~5.7× cheaper output. Final call: **qwen primary, deepseek-v4-flash backup** — `decide()`'s last attempt escapes to the backup (different weights + 18 providers → survives both a sick provider and a weight-level spiral; the structured standard makes qwen's degeneration survivable, so single-provider-primary is now safe).
- **Standardize + land it**: `/generate-standard` → `quality-standard.md` (9 dims; "formats via tools not AI" is Dimension 9, enforced by `/analyze-code-quality` + runtime Pydantic per Alvi's call — no separate guard). Added **ruff** (config + dev dep; `structured.py` made exemplary-clean). Fixed a Windows-console cp1252 crash (a stray VLM `▼` glyph). Committed + pushed `d9c6b2c`.

**Co-build texture**: the whetstone at its sharpest across a marathon — nearly every fix came from an Alvi catch (raw-goal, "don't fix without root cause," the crop-hallucination question, the single-provider consideration, format-via-tools, the minimize diagnosis, two false-NOT_FOUND catches). I conceded cleanly every time and let **measurement kill two of my own guesses** (backoff-retry, concise-phrasing) — ef253360 firing repeatedly. Honest corrections throughout (mis-stated "brain/eyes are pure-stdlib" → eyes already has Pillow; retracted).

**Outcomes**:
- **Deliverables** (commit `d9c6b2c`, pushed): `structured.py` (new); `brain/client.py` (BrainAction + tool-calling decide + qwen/deepseek fallback + prompt fixes); `eyes/client.py` (visual_focus/expectation, focus-failure harness, BOX_PROMPT recalibration, crop-save); `agent/loop.py` (renames, utf-8-safe console); `runlog.py` (`current_step`); `docs/adr/2026-07-16-structured-output-standard.md` (ADR-005); `docs/quality-standard.md`; `ruff.toml` + `requirements.txt` + `requirements-dev.txt`; `eyes/test_describe.py` updated (all offline tests green).
- **Tech Debts**: [new] **model-fallback UNEXERCISED live** (qwen→deepseek escape wired + unit-verified, never actually fired); [new] focus-failure recovery + BOX_PROMPT recalibration only **targeted-tested**, not re-validated in a fresh full run; [new] **doc-sync incomplete** — `architecture-overview.md` / `agent-loop-flow.md` still say `focus`/`expect` (context-index, backlog, orientation-map synced this wrap-up; the two prose docs deferred); [new] **broader ruff pass** — 6 pre-existing issues remain (`eyes/client.py` semicolons, `_ask` raise-from); [carry] `decide` latency (Think-High, 3–12s, worse on mobile net); box-cache; thinking-diff experiment; phone-body boxing; Layer 3 (`request_diff`) never exercised live; PhoneDevice type-escaping; hands app-behavior; infinite-scroll stop; MiniMax M3; async /exec; Tier-1 unbuilt.
- **Next Steps**: **(1) TEST the shipped work live** — trigger the model-fallback, re-validate focus-failure recovery + box recalibration in a full run; **(2) design the macro/combo input action** (harness-level, so the Brain can batch a sequence / type a whole expression — the recurring THIRD vote this session: batching cut a 16-step run to 4, and the Brain's degeneration loop was it straining to plan a multi-step sequence under one-action-at-a-time); then the **phone/WhatsApp north star**; finish the doc-sync; broader ruff pass.

**Insights**: *Formats belong to tools, not the model* — a permissive `json_object` + lenient scrape is no guard at all; the fix is a schema the provider fills and WE validate, so validity never depends on the provider being able/willing. *Instrument before you fix* — Alvi's "don't fix without root cause" turned a wrong backoff-guess into a captured 1148-token reasoning-loop; the raw provider body was the whole answer. *A perception model should REPORT, not fabricate* — `box()` guessing coords for an absent target is the same failure class as the ADR-003 verdict noise; `NOT_FOUND` + overview + Brain-re-orient is the honest split. *Provider count = resilience* — the crash reached us only because our primary was single-provider; OpenRouter's own fallback would have hidden it on an 18-provider model. *Measurement kills guesses, including your own* (twice: backoff-retry, concise-phrasing) — the same discipline that killed over-builds in ADR-003/004 turned on my fixes here and I let it.

**Promotions**: → docs/adr/2026-07-16-structured-output-standard.md (ADR-005, new) · docs/quality-standard.md (new — 9 dims; format-via-tools = Dim 9) · docs/context-index.md (Brain backup + structured-output quick-facts, quality-standard entry) · docs/backlog.md (structured standard + verify-focus + focus-failure done; new debts) · docs/orientation-map.md (ADR-005 + quality-standard entries).

---

### [2026-07-16 13.53] (agent: software-architect) — FOVEAL DESCRIBE + TRIM (ADR-004): DESCRIBE-SPEED SOLVED (5–16s → ~2s) BY ATTACKING OUTPUT LENGTH, NOT THE MODEL 🔬👁️⚡

**Session theme**: A full bake-off → `/high-wizard` → `/implement-plan` → `/wrap-up` that solved the #1 tech debt (`describe` latency). One load-bearing find drove everything: **describe latency is output-length-bound, not model/image** — the 72B *boxes* a frame in ~1.5s but *describes* it in 5–16s (same model, same image). So describe became **two-mode foveal** (say less about less), and 72B was demoted from default describer to the authoritative-Eyes escalation.

**What happened**:
- **Bake-off first (measure, don't guess)**: pulled OpenRouter's 176 vision models; ran 3 tests. **Test 1 (box probe)** — only `qwen2.5-vl-72b` boxed reliably (4/4 incl. small buttons); the fast small models mislocated to blank regions. And the quiet proof: 72B boxes in ~1.5s but describes in 5–16s → **latency ∝ output length**. **Test 3 (crop-describe)** — `qwen3-vl-8b` faithful on trimmed crops (no confab; read `Rp759` vs a struck `Rp799`; hard calc crops clean) at ~0.3–1.4s; thinking measured **14× slower for zero gain** (instruct-vs-thinking A/B on q3-8b). Alvi added a **marketplace crop** mid-test — good call, different domain.
- **Alvi's grand-POV reframe** turned my flat "faster model + downscale" into **foveal vision**: cheap gist everywhere + sharp detail only where focused; `focus` should **TRIM** (crop), not just instruct; overview downscales; **`expect` requires `focus`** (verification always regional). I named the load-bearing constraint (trim needs a BOX — the thing ADR-003 shelved; general Qwen-VL boxes, UI-TARS only points) and corrected "bigger screen better" (false past the pixel clamp — trim IS the fovea).
- **HW → 15 confirmed decisions → 4-phase build, all green**: `box()` (72B, absolute coords — validated at **1280×800 AND 2560×1600/4.1M px**, above the clamp, no conversion → killed the pre-scale backup); two-mode `describe()` (overview downscaled gist / trim box→crop→q3-8b; `careful`→72B recheck rung; box-fail→full-frame); brain `recheck` + `expect⇒focus`; loop threads `careful`; deterministic `eyes/test_describe.py`; ADR-004 + 5 docs.
- **Live win**: browser task `done` in 4 steps, describe **1.8–3.3s**, now *under* `decide` — the bottleneck left the Eyes. Two robustness gaps surfaced live (box 429 crash; `_ask` KeyError on an error body) → both fixed.
- **Quality review caught my own regression**: the model reshuffle had silently downgraded `diff()` (the `request_diff` top rung) to q3-8b → fixed to 72B. Alvi's "should diff think?" became a logged experiment (its model, qwen2.5-vl, can't think — only Qwen3-VL has thinking variants; a model swap, untested).

**Co-build texture**: the whetstone at its best across a very long arc — Alvi's precise questions repeatedly sharpened the design (trim-needs-a-box, "+15% means what", the marketplace crop, "should diff think?", the qwen2.5-vs-qwen3 generation catch). Empirical throughout: every decision measured, not argued — the bake-off drove the architecture, and the quality review's value showed by catching a real reshuffle regression a passing test suite missed.

**Outcomes**:
- **Deliverables**: `eyes/client.py` (box, two-mode describe, helpers, prompts, models, NO_THINK, robustness), `brain/client.py` (recheck + expect⇒focus), `agent/loop.py` (careful threading), `screen/docker-compose.yml` (SCREEN_RESOLUTION knob), `eyes/test_describe.py` (new), `docs/adr/2026-07-16-foveal-describe-trim.md` (ADR-004, new) + 5 docs synced; completed plan. Quality Review 1 med + 2 low, resolved; FIT skipped (no qa/, runtime = live smoke).
- **Tech Debts**: [new] **`decide` (Brain) is now the dominant loop latency** (3–12s, Think-High) — describe SOLVED; next lever = lighter reasoning config; [new] **box-cache** would save ~1.5s/step on stable focus regions (trim = 2 calls, box dominates); [new] **thinking-diff experiment** (reasoning VLM at the stuck rung, untested); [new] **phone-body boxing** untested (resolution CLOSED @4M, body pending a live device); [carry] `decide` slow-trickle stall unbounded; [carry] **Layer 3 (`request_diff`) never exercised live** (diff() model fixed to 72B this session, still not run); [carry] PhoneDevice type-escaping + double adb-devices; hands app-behavior unconfirmed; infinite-scroll stop; MiniMax M3; async /exec; Tier-1 unbuilt.
- **Next Steps**: **phone/WhatsApp real-world task** (north star — body exists, Phase 5 done, describe now fast); exercise **Layer 3** live (now 72B); **box-cache** (the trim speed lever); **faster `decide`** (the new bottleneck); thinking-diff experiment; confirm remaining hands; infinite-scroll stop; carried items.

**Insights**: *Latency ∝ output length* — the whole win came from making the Eyes say less about less (trim + gist), not from a faster model; "72B boxes fast, describes slow" was the tell. **Trim makes cheap models faithful** — small VLMs confabulate on full frames but are clean on a small crop (nothing to hallucinate), so q3-8b is safe *only* on crops. **Thinking is per-model-generation, not a VLM-category property** (Qwen2.5-VL can't; Qwen3-VL's `-thinking` variants can) — and even where it can (q3-8b), it measured useless for describe. The quality review earned its keep by catching a reshuffle regression the passing tests missed.

**Promotions**: → docs/adr/2026-07-16-foveal-describe-trim.md (ADR-004, new) · docs/architecture-overview.md (Eyes two-mode + output-length fact + phase status) · docs/agent-loop-flow.md (§9 foveal describe + superseded 19.5s note) · docs/backlog.md (describe-speed resolved, decide now bottleneck, box-cache + phone-body + thinking-diff) · docs/context-index.md (Eyes quick-fact, SCREEN_RESOLUTION) · docs/orientation-map.md (ADR-004 entry).

---

### [2026-07-16 09.48] (agent: software-architect) — PHASE 5 VERIFY-AND-RECOVER (ADR-003) — SEAM B CLOSED; TWO OVER-BUILT FRAMES KILLED BY MEASUREMENT (PIXEL LAYER-1, THEN THE VLM VERDICT) 🔬🧩✅

**Session theme**: A full `/high-wizard` → `/implement-plan` → `/wrap-up` that shipped **Phase 5 — verify-and-recover** (the roadmap's differentiator, closing **Seam B**). But the real spine was *measurement killing my over-builds twice*, and Alvi's frame-kills making the design simpler each time. Final shape: **change-feedback is the VLM's job, split correctly — the Eyes PERCEIVE, the Brain JUDGES.**

**What happened**:
- **Designed a 3-layer ladder in HW** (all 7 decisions collected): ① pixel no-op (`frame_diff`) · ② `expect` verified in the VLM · ③ Brain-requested 2-image diff · + a recovery backstop · unifying `focus`/`expect`/`request_diff` into one prospective describe-modifier family. Built Phases 1–4 clean (framediff + test, loop wiring, `expect` VERIFY, `eyes.diff`, escalation).
- **Frame-kill #1 — the pixel Layer 1 (measured dead).** In Phase 5 calibration: a single typed digit scores **~0.02–0.09** whole-frame mean-diff — *below* the ~0.25 idle noise floor (higher res doesn't help; inherent to mean-over-whole-frame). Alvi: *"no-change is only applicable to a certain area, it can't be screen-wide."* He asked the load-bearing question — *can UI-TARS crop the region via focus?* Tested 4 formats (native `start_box`, "four integers", Qwen `bbox_2d`, a tight button) → **UI-TARS-1.5-7B returns a POINT every time, never a box.** So region-scoping is impossible → **dropped pixel Layer 1**; `framediff.py`+test kept & PARKED for the describe-speed thread. Layer 2 (`expect`, regional+semantic) becomes primary.
- **Recovery corrected (twice, by Alvi).** First rebase (NOT-VERIFIED streak) was wrong — it escalated on NOT-VERIFIEDs from *different* actions (exploration, not a loop). His fix: escalate ONLY on *same-action-and-failing*. Validated live on an impossible "QUANTUM mode" task (silent through exploration, fired on repeated-scroll-failing, Brain changed course at 2).
- **Root-caused a misattribution I made.** A run stalled; I blamed `describe`. Alvi checked the transcript: describe RESPONSE fully written, no `decide` record → **the stall was in `decide` (the Brain call), not describe.** Fixed: `decide` had no network retry (only caught HTTPError) → added `URLError`/timeout/reset retry. Also corrected the n=1 "describe is THE bottleneck" headline (both describe 5–16s AND decide 3–12s, variable).
- **Frame-kill #2 — the VLM verdict (measured noisy).** Live 1024×4096: the `VERIFIED`/`NOT VERIFIED` verdict was noisy — whitespace nitpicks (`'1024 × 4'` vs `'1024×4'`), and a self-contradiction (`NOT VERIFIED - the display shows '1024×409'` when that WAS the expectation). But the *descriptions* were always accurate. Alvi: *"instead of a verdict, let describe just report VERIFICATION: <what he sees>."* → **the Eyes REPORT the state, the Brain JUDGES the match** ("if it differs, MAYBE it didn't work — rethink or adapt", his softer wording). `on_track` (a Brain→loop flag) considered + dropped (the softer "maybe" leaves no honest boolean) → recovery = Brain + a dumb advisory repeated-action guard. Re-run: `VERIFICATION: 1| → 1024 → 1024× → 1024×4096 → 4194304`, clean `done` in 6 steps, **zero** verdict noise.
- **Alvi questioned the doc-sync effort** ("is it useful to you?"). Honest concession: the ADR + awakening-loaded pointers (map/backlog) earn their keep; but I over-synced mid-flight (documented the verdict design, then redid it all on the report pivot) and duplicated the "why" in code comments AND prose. Lesson: sync docs ONCE at the end, lean on ADR + code comments.

**Co-build texture**: the whetstone dynamic at its sharpest. Alvi killed two of my over-built frames with measurement (pixel Layer 1, the verdict), corrected my recovery trigger twice, caught my describe/decide misattribution, and questioned my doc-sync ROI — and each concession made the design simpler and more correct. I conceded cleanly every time (013b3e8f running *toward* me). The empirical spine — "measure, don't guess" — turned on my own designs and I let it.

**Outcomes**:
- **Deliverables**: `framediff.py`+`test_framediff.py` (parked); `agent/loop.py` (Layer-2/3 wiring, advisory recovery); `brain/client.py` (`expect`/`request_diff` schema+rules, COMPARE-the-report rule, network retry); `eyes/client.py` (`describe` report block + section-only `focus`, `eyes.diff` + multi-image `_ask`, max_tokens→1024); **ADR-003** (new); docs synced (agent-loop-flow §4/§8, backlog, orientation-map); completed plan. Quality Review clean; FIT skipped (no qa/ — runtime covered by live runs).
- **Tech Debts**: [new] **describe AND decide both slow & variable** (5–16s / 3–12s), describe-downscale is the real speed lever (parked `framediff` serves it); [new] `decide` slow-trickle stall not bounded (network retry covers dropped/timeout, not a slow-but-alive response); [new] **Layer 3 (`request_diff`) never exercised live** (recovery broke the loop first) — wiring verified only; [carry] PhoneDevice `type` escaping + double `adb devices` (low); [carry] hands app-behavior (double_click/right_click/drag) unconfirmed; [carry] infinite-scroll stop-condition; [carry] MiniMax M3 needs hand-holding; [carry] async `/exec` deferred; [carry] Tier-1 (API/MCP) unbuilt.
- **Next Steps**: **describe-speed thread** (downscale / faster VLM / incremental describe via the parked `framediff`) — the real perf lever now; **give BRYES a phone/WhatsApp real-world task** (the north star — body exists + Phase 5 done); exercise Layer 3 (`request_diff`) live; confirm remaining hands; infinite-scroll stop; the carried items.

**Insights**: *The VLM perceives, the LLM judges.* The whole verdict-noise class came from asking a perception model to make binary judgments — its weak spot — when its descriptions are reliable. Broader: **an exciting first design (3-layer pixel ladder, VLM verdict) is a trap; measurement is the filter, and it kills over-builds fastest when pointed at your own work.** Both frame-kills this session came from Alvi asking the load-bearing empirical question I hadn't (can UI-TARS box? is the verdict even useful?). Also: sync docs at the true end, not against a moving target.

**Promotions**: → docs/adr/2026-07-16-change-feedback-verify-and-recover.md (ADR-003, new) · docs/agent-loop-flow.md (§4 Seam B closed + §8 change-feedback) · docs/backlog.md (Phase 5 done + framediff parked + timing/decide-stall debts) · docs/orientation-map.md (ADR-003 entry).

---

### [2026-07-15 19.24] (agent: software-architect) — DEVICE INTERFACE (ADR-002) — BRYES GETS A SECOND BODY (A REAL PHONE) + PER-PHASE TIMING CORRECTS A GUESS + PHASE-5 CHANGE-FEEDBACK DESIGNED 🧩📱⏱️

**Session theme**: A full `/high-wizard` → `/implement-plan` → `/wrap-up`. Alvi's north star ("give BRYES a phone") became the forcing function for an abstraction: extract Screen+Hands+shell into a swappable **`Device`** interface (ADR-002) — one mind (loop+Eyes+Brain), many bodies. Proven by adding a **real Android phone over adb/USB** as body #2. Then a bonus timing instrument that *corrected my own wrong hypothesis*, and a long co-design of the deferred **Phase-5 change-feedback** primitive.

**What happened**:
- **Constraint-first on the phone (ef253360 fired at turn 1):** Alvi asked "phone via Docker + assign a SIM?" I led with the load-bearing limit — a **cellular number can't be virtualized** (emulated Android has no radio; its number is a fake simulator artifact that can't receive a WhatsApp OTP), and Android-in-Docker on Windows is a KVM/binder fight. Reframed: a **real phone** solves the number natively; the question becomes "how does the agent fully control it" → **ADB** (screencap=Eyes, `input`=Hands, `adb shell`=Tier-2), over **USB from the host** (no container passthrough). The phone is body #2, not routed through the Screen container.
- **The abstraction (Alvi's move):** "make the Screen a real interface layer — multiple devices, same interface, some differences." Named it `Device` (his call: "Device is correct, Screen is out-of-mind"). I sharpened the load-bearing nuance: **"same interface" isn't enough — differences must be first-class via a `Capabilities` manifest** (phone has no right_click/hover, Back/Home keys, scroll→swipe, portrait coords), and the Brain's action vocab is **assembled from the active body's caps** (a phone never sees `right_click`). Boundary held: pure API/MCP channels (no screen) are NOT Devices (that's ADR-001 Tier-1) — don't over-abstract.
- **HW → 10 confirmed decisions → 5-phase implementation, all green.** Phase 0 (adb installed to gitignored `tools/`, phone authorized — Galaxy Note10 Lite, Android 13, 1080×2400, screencap+shell verified up front) de-risked before a line of PhoneDevice. `devices/` package: `base.py` (Protocol + Capabilities), `container.py` (byte-identical extraction — test_hands 5/5, test_shell 6/6, test_phase4 vision=15 unchanged), `phone.py` (adb), `test_phone.py` (5/5 live). Brain vocab from caps. Loop `run(device=None)` defaults ContainerDevice. Caught + fixed a real regression (test_phase4 imported the removed `screenshot` helper). ADR-002 + docs.
- **Live proof = interface validated, task incomplete (honest).** The *unchanged* loop drove the real phone via vision over adb (real screencap→describe→decide→locate→taps/scrolls/`key Home`, respecting phone caps). But "open Settings" hit step_limit — a **task-navigation** limit, NOT an interface issue.
- **Timing instrument corrected my hypothesis (the humbling bit).** Alvi noticed slowness "after describe." I confidently blamed the Brain's Think-High `decide`. Added per-phase timing (`screen/describe/decide/locate/act`) — measured **`describe` ≈ 19.5s vs `decide` ≈ 3.2s**. I was **wrong**: the Eyes VLM is the bottleneck, not the Brain. The optimization target is `describe` (downscale/faster VLM), not Think High. (Also retracted a confident "Nova scrolls horizontally" guess — no transcript evidence; Alvi's deeper diagnosis was right.)
- **Phase-5 change-feedback, co-designed (parked in backlog).** Alvi pinpointed the real gap: the loop feeds current-describe + actions-only history, **no state-delta** → the Brain *infers* what its actions did and wanders. Converged (through his skepticism sharpening it) on: **Layer 1** pixel no-op detector (`frame_diff` = downscaled-grayscale mean-abs-diff, threshold tuned empirically — catches "nothing moved", the one thing the Brain is blind to); **Layer 2** a checkable `expect` the Brain emits, **verified in the VLM** by riding into the next describe like `focus` (grounded, ~free, neutral/disconfirming prompt to dodge confirmation bias); bias `expect` toward **absolute/nameable target-states** so the current frame suffices; **rung ③** a Brain-requested, **expensive/slow** two-image VLM diff, gated behind "something's wrong", result to the Brain. Two failure shapes covered: *no effect* + *wrong effect*.

**Co-build texture**: co-architecture at its best — Alvi drove the frame (real phone > emulated; "make it an interface"; "make it right before fast"; the state-delta gap), and his **skepticism** ("do we really need Layer 1? can Layer 2 handle no-changes?") *sharpened* the design rather than derailing it (I conceded the sequencing — Layer 2 first, Layer 1 evidence-gated — while holding the one defensible nuance). And I got **corrected by measurement** on the describe/decide slowness after asserting it confidently — conceded clean. Measure-before-optimize, name the constraint first, don't over-abstract.

**Outcomes**:
- Deliverables: `devices/{base,container,phone,__init__,test_phone}.py`; `agent/loop.py` (device-agnostic dispatch + per-phase timing); `brain/client.py` (caps-driven vocab, back-compat `caps=None`); `agent/test_phase4.py` (regression fix); `runlog.py` (`note()`); `.gitignore` (`tools/`); **ADR-002** + docs (architecture-overview, agent-loop-flow §7, orientation-map, backlog, context-index); completed plan. Quality Review: 1 low (shipped). FIT: no qa/ → runtime clean inline.
- **Tech debts** (carried + new): **[new] `describe` is the ~19.5s per-step bottleneck** (the real perf lever — downscale/faster VLM); **[new] phone task capability limited by the Phase-5 change-feedback gap**; **[new] PhoneDevice `type` doesn't escape shell-special/emoji** (ADBKeyboard deferred); **[new] PhoneDevice init calls `adb devices` twice** (low, shipped); [carry] hands app-behavior unconfirmed; infinite-scroll stop; Brain on few tasks; MiniMax M3; async /exec; Tier-1 unbuilt.
- **Next steps**: **Phase 5 — verify-and-recover** (the full change-feedback design is now in [backlog.md](../../docs/backlog.md), ready to `/high-wizard`) — *do this first ("make it right")*; **then faster `describe`** (downscale / faster VLM / incremental change-driven describe using the same `frame_diff`); then the WhatsApp/phone task (body now exists); the carried items.

**Promotions**: → docs/architecture-overview.md (Bodies — Device abstraction) · docs/agent-loop-flow.md (§7 Device + timing + Seam-B phone reconfirmation) · docs/orientation-map.md (ADR-002 entry) · docs/backlog.md (Device+phone+timing resolved; describe-latency debt; Phase-5 change-feedback design) · docs/context-index.md (bodies) · docs/adr/2026-07-15-device-interface.md (ADR-002, new).

---

### [2026-07-15 15.06] (agent: software-architect) — SHELL EFFECTOR CHANNEL (Tier 2) + EFFECTOR-HIERARCHY ADR — BRYES BECOMES A TOOL-USING AGENT 🐚🧰🏗️

**Session theme**: A vision reframe → a full `/high-wizard` → `/implement-plan` → `/wrap-up` cycle. Opened on Alvi's "person with phone/email" vision + a WhatsApp-vs-combo fork; landed on the deeper insight — the agent shouldn't act ONLY by vision. Added a **shell/command effector channel** and captured the **effector-hierarchy** (Tier 1 API/MCP · Tier 2 shell · Tier 3 vision-fallback) as BRYES's first ADR.

**What happened**:
- **The reframe (Alvi)**: "if something has an API/MCP or a command line, connect from the Brain directly — like how you use the OS shell — not through Eyes+Hands." Named the architecture: vision demoted from the ONLY effector to the Tier-3 fallback; the Brain routes each intent to the most direct channel. Nuance surfaced: for *persona* surfaces (WhatsApp) vision-on-a-real-device is the MORE human path, so effector choice = *(is there an API?) AND (does human-indistinguishability matter here?)*.
- **Phone/WhatsApp groundwork**: named the load-bearing constraint — a phone NUMBER can't be conjured by open-source; it must be *provisioned* (SIM/VoIP). Open source *operates* a phone (scrcpy/adb), it doesn't manufacture a number. Recommended a real Android + real SIM driven by vision (reuses BRYES's loop). Deferred to a later session; shell channel first (foundational, deterministic, success-feeling).
- **HW design — co-designed through Alvi's catches** (9 confirmed decisions). Three reshapes: (1) **interactivity** — one-shot `/exec` can't answer a mid-run prompt → do NOT build a PTY (Level 3); genuinely-interactive terminals fall back to **vision-driving xterm** (already possible). (2) **timeout vs `wait`** — I first argued to drop the Brain-settable timeout; Alvi pushed "what about installs, clamp to what?" → **I conceded** (background+poll is fiddly for finite-long commands; a Brain-declared `timeout`, clamped 30s→300s, is cleaner). (3) **async `/exec`** — "can we make it async like your shell?" → named the constraint: async's payoff is gated behind loop concurrency BRYES lacks (a single sequential loop just polls instead of blocks) → **deferred, designed as an additive upgrade**.
- **Implementation (5 phases, all green)**: `/exec` endpoint (`shell=True`, clamp [1,300], `_clip` ~4 KB, `errors="replace"`, `TimeoutExpired`→`timed_out`); deterministic `test_shell.py` (6 checks); Brain vocab + tier-routing + non-interactive discipline; loop `exec_cmd()` + `shell` branch threading exit+output into HISTORY; docs (rewrote the now-false "no shell channel" fact) + **ADR-001**. Live: `uname -r` and `find /root -name "*.py" | wc -l` (a **pipe**) both `done` in 2 steps via shell, no vision.
- **Quality Review**: 1 minor finding (binary output → `UnicodeDecodeError` → 500) → fixed with `errors="replace"`, re-verified. FIT: no `qa/` instrument (BRYES convention) → runtime covered inline, all green.

**Co-build texture**: a genuine co-architecture session — Alvi drove the design through precise catches (interactivity, timeout-for-installs, async), and I **conceded cleanly to his timeout instinct** in a domain I was leading (background+poll IS fiddly; his knob was right). The empirical rhythm held: name the constraint first, defer what the current architecture can't yet consume (async, Level-3, Tier-1), ship the smallest reframing step.

**Outcomes**:
- Deliverables: `screen/server/app.py` (`/exec`), `screen/test_shell.py`, `brain/client.py` (shell vocab + tier routing), `agent/loop.py` (`exec_cmd` + shell branch), docs (architecture-overview, agent-loop-flow, screen/README, backlog), **ADR-001** (`docs/adr/2026-07-15-effector-hierarchy.md`), completed plan.
- **Tech debts** (carried + new): [carry] hands app-behavior unconfirmed (double_click/right_click/drag); [carry] infinite-scroll has no natural stop; [carry] no explicit verify-and-recover (Phase 5); [carry] Brain validated on few tasks (calc suite un-run); [carry] MiniMax M3 needs hand-holding; [carry] `describe` verbose / cost-at-scale unmeasured; **[new] async `/exec` deferred** (until loop concurrency / frequent long jobs); **[new] Tier 1 (API/MCP) named but unbuilt**.
- **Next steps** (carried + new): **give BRYES a phone / WhatsApp task** (now a Tier-3 persona surface on the effector-tier architecture — the north star); define an infinite-scroll capture stop-condition; confirm remaining hands behavior; add a combo/macro action (less urgent now shell exists); validate qwen3.6-flash on the calc suite; Phase 5 at ≥80%; **[new] a Tier-1 API channel (e.g. email)** to exercise the tier pattern.

**Promotions**: → docs/architecture-overview.md (effector-tier model) · docs/agent-loop-flow.md (shell path + "exception to Seam B") · docs/backlog.md (shell resolved + async deferred) · docs/adr/2026-07-15-effector-hierarchy.md (ADR-001, new).

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
