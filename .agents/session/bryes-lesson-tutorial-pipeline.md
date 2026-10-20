# BRYES — Lesson Capture and Tutorial Authoring

Teaching pages built from real screenshots: a capture-only Windows body, a labelled
recorder, and a builder that refuses a step with no evidence.

---

### [2026-10-20 21.05] (agent: software-architect) — BRYES BECOMES THE CAMERA: TWO REAL UNREAL LESSONS, AND A PROCEDURE THAT REFUSES TO TEACH FROM PIXELS 📷📘✋

- **Context**: Alvi pivoted the project mid-session. After the prior-art audit and the destination answer, he proposed BRYES as a *module for an agent mentor to teach him Unreal*: the agent produces documents with screenshots, step by step, possibly HTML. Four requirements: a screenshot-based document pipeline, an "Eyes brief" like the WhatsApp profile, a look at Jev AI for the slow operation, and a model refresh (DeepSeek V4.1 Flash for the Brain). Session began as an awakening; ended with a shipped capability.
- **Discussion**:
  - **The constraint named before any design**: a screenshot records what the screen showed, never *why* the step exists or in what order. Deriving instructions from pixels produces a confident wrong tutorial, the worst artifact for a beginner. So the design splits: BRYES captures, the mentor authors, the learner drives.
  - **Alvi's Input**: *"I want this BRYES to be a module for agent mentor (or maybe you) to teach me unreal"*, with the four requirements, then **A (you drive, BRYES records)** and **A (LSGI battle loop)** when the two design questions were put to him.
  - **My Response**: checked the repo before recommending anything, which surfaced the blocker the question did not mention: **BRYES had no Windows body at all**, so it could not see Unreal. Then built the capture half.
  - **Models, measured not recalled**: `deepseek/deepseek-v4.1-flash-1017` accepts image input ($0.30/$1.20 per M), `nvidia/nemotron-3.5-super-vl` names GUI screenshots at $0.15/$0.50, and **UI-TARS-2 is a research model with no public weights or API** (LLMDB + the ByteDance repo), so grounding does not improve by waiting. None of it is needed for the lesson half, because the mentor reads the images.
  - **Jev, verified**: TypeSafe's System One model, 1.14 adds experimental image input and a **Box** question type (normalised edges + confidence, ~$0.042/M input, output free). It cannot replace the Brain, which must emit free text, and it is a bake-off candidate rather than a swap.
  - **Alvi's Input (second half)**: *"can you make some kind of skill / procedures to create this tutorial lessons with BRYES? put it in BRYES?"* then *"lemme ask him manually"* about the Unreal agent, and finally the wrap-up.
- **Key Interactions**: Alvi's `go` twice, each one a green light for a complete phase rather than a step. His A/A answers settled the two questions that would otherwise have been guessed. His request for a procedure is what turned a one-off script into a capability.
- **Issues Encountered**:
  - **Problem Description**: four real defects, all found by running rather than reading.
  - **Root Cause**: each was an assumption that survived because nothing tested it.
  - **Solution Process**: (1) the body advertised the **primary screen** (2560x1440) while `ImageGrab(all_screens=True)` returns the virtual desktop (2705x2520), fixed by reading `SM_C[XY]VIRTUALSCREEN`; (2) `--list-windows` **crashed on cp1252** the moment a window title carried an arrow glyph, the exact hazard AGENTS.md warns about, fixed with an encode-with-replace helper; (3) the annotation badges sat at each box's top-left and covered `File`, `Outliner`, `Details`, `Content Drawer`, the labels that say what the box is, moved to straddle the top-right and then to sit above the box when there is room; (4) a PowerShell `Set-Content -Encoding utf8` put a **BOM in the commit subject**, amended immediately rather than left.
  - **Resolution**: all four re-run after the fix. Also caught in the **procedure document** itself: a gate claimed "every shot is newer than the lesson text", which the builder never checked and which is backwards, since capture precedes authoring. The gates now state which three the build enforces and which one only a reader can.
- **Outcomes**:
  - **Deliverables**: `devices/windows.py` (capture-only body, DPI-aware, window-scoped grab), `capture.py` (labelled shot + provenance log), `lesson.py` (markdown + shots to HTML, callouts burned in), `test_lesson.py` (4 checks, 2 of them negative), `docs/procedures/make-a-lesson.md` + `/make-lesson` skill, two lessons under `lessons/`, and the README/AGENTS/orientation-map entries. Pushed as `53bd1d0`, 26 files, +1346/−2.
  - **Progress Made**: the first lesson (`lsgi-01-editor-anatomy`, 4 steps, 3 screenshots, 11 callouts) and the second (`lsgi-02-blueprint-editor`, 5 steps, 4 screenshots, 5 callouts) are built from live captures of his editor at 13:01:54 and 13:16:54. Lesson 2 retargeted itself after the capture showed the Blueprint editor rather than the Content Browser, which is the pipeline behaving correctly.
  - **Tech Debts**:
    - **[new] `capture.py` has no automated test.** It needs a live desktop, so `test_windows.py` covers the device and the matcher while the CLI is proven only by hand.
    - **[new] ruff was never run** (not installed in `C:\Python313`), so no lint claim is made for the four new Python files.
    - **[new] Lesson images are committed as PNG**, about 2.5 MB for two lessons. Fine at this size; a series wants LFS or an assets repo.
    - **[new] Badge placement still overlaps non-essential chrome** in dense captures (the menu bar's `Debug`, a Details header).
    - **[new] No lessons index page.** Two pages and no front door.
    - **[new] Lessons live in BRYES while they teach LSGI.** `--out` supports the move; nothing has moved.
    - **[carry] The whole 2026-08-23 set is untouched**: grid-form probe, Windows-MCP install, `AutomationId` rule, verification-before-driving, stale module READMEs, the model-doc contradictions, and the runtime debts.
  - **Next Steps**:
    - **Unreal semantics for lesson 3**, from the `unreal` agent (`Claude Unreal`), asked through the structured `/ask-agent` prompt: what `STT_ChooseFirstOffered` is responsible for, its Context/Input/Output, what runs around it, which concepts come first, and which docs are authoritative. The reply becomes a cited source, not just input.
    - Generate a `lessons/index.html` when a third lesson exists.
    - Decide the image policy before the folder grows.
- **Insights**:
  - **New Understanding**: the pivot is not a consolation prize for the audit. The loop (drive by vision) is what prior art already does better; **capture plus annotation is the part with no off-the-shelf equivalent**, and it is the part that fits a learner who drives.
  - **Pattern Recognition**: `ef253360` fired early and saved the session: naming "a screenshot cannot teach" before designing turned four requirements into one split. `a319438e` ran again on the model question, where the honest answer was *UI-TARS-2 has no API*, not *here is the newest model*.
  - **Improvement Areas**: I wrote a gate in the procedure that the code did not enforce, which is the "a check that cannot fail" failure in documentation form. The fix belongs in the doc and it was applied there, but the instinct to write the check I wished existed is the thing to watch.
- **Promotions**:
  → Promoted to [docs/procedures/make-a-lesson.md](../../docs/procedures/make-a-lesson.md) — the procedure, served as `/make-lesson`.
  → Promoted to [docs/orientation-map.md](../../docs/orientation-map.md) — an entry for the procedure, with its update trigger.
  → Promoted to [README.md](../../README.md) and [AGENTS.md](../../AGENTS.md) — the third body and the lesson pipeline, stated where agents and humans enter.
