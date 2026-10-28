# BRYES — Driving Unreal: Measurement and Action Surface

How BRYES measures its own grounding on real editor frames, and what it gained so the agent can
aim a pixel and drop a delete-anything drag: the host frame, window selection, a delta drag, the
coordinate verbs, and a drag that proves itself.

---

### [2026-10-28 13.06] (agent: software-architect) — I MEASURED THE EYES, CAUGHT MY OWN ANSWER KEY, AND LEARNED THE DROP POINT IS NOT A POINTING TASK 🎯📐🖱️

- **Summary**: Built a snapshot grounding tester and got the first real number for the Unreal editor (headers 2/3, pins 1/5, asset tiles 6/6, empty canvas 0/6), then built the action surface: the host frame is now the target's monitor, a named window selects the body, a drag can end at an offset, and the Brain can aim a pixel.
- **Context**: The session began as an awakening and turned into a council. Alvi wants the agent to do Unreal Blueprint work itself, including dragging inside the graph. The plan came from a Council of Wizards with five sub-plans; SP-1 and SP-2 ran here, and Alvi dropped SP-3 (the Unreal API channel) at wrap-up.
- **Discussion**:
  - **Where the numbers come from**:
    - **Alvi's Input**: "lessons are for me, not for agents, the knowledge should be populated from basic windows + unreal knowledge". Then, on the corpus: "you can take it directly using bryes… check the result first to only use monitor where the unreal editor shown."
    - **My Response**: Dropped the lesson screenshots as a corpus and recorded that the profiles are authored from general knowledge, never from the lessons. The tester now scores a live capture.
  - **What the numbers mean**:
    - **Alvi's Input**: "sorry, I don't understand all of those. what is 2/3 1/5 0/4 6/6 ?" and later "what is it for?"
    - **My Response**: Explained hit-out-of-attempts, then the purpose: a wrong click on a blueprint does not fail, it puts the wire somewhere else. Both questions were my explanation failing, not his reading.
  - **Priority**:
    - **Alvi's Input**: "why you suggest to proceed SP-2 and SP-3?" then "between SP-2 and SP-3 which one is more priority?" then "ok let's do SP-2 now".
    - **My Response**: Said SP-3 was the higher priority (wiring is what vision fails at), built SP-2 when he chose it, and pulled its host requirements forward so SP-3 would have been unblocked. SP-3 was then dropped, which leaves R7's wiring with no exact channel.
- **Key Interactions**: He answered a five-decision round in one line, corrected the corpus twice, and chose the worktree so a second agent could run SP-3. His "the WindowsDevice.screenshot() should only screenshot that only monitor" was the frame decision; his note that Unreal opens child windows on the primary monitor became a profile rule.
- **Issues Encountered**:
  - **Problem Description**: The first pin measurement read 2/5 on one frame and 1/5 on another.
  - **Root Cause**: My pin boxes were 5 to 10 px off, cutting the pin glyph. Marked by eye from a full-frame view, on targets 14 px wide.
  - **Solution Process**: Zoomed 4x into the pin rows on the overlay, re-marked every pin as a 24x24 box centred on the glyph, re-ran both frames.
  - **Resolution**: Both frames then read 1/5 with a 10.6 px median error, so the misses are the model's, not the key's. The rule: small targets are marked on a zoomed crop and divided back.
  - **Problem Description**: The whole-desktop frame contained two screens, one of them unrelated to the task.
  - **Root Cause**: `screenshot()` grabbed `all_screens=True` since the host body was built, when the desktop was one screen.
  - **Resolution**: The frame is now the monitor resolved by `MonitorFromWindow`, the origin is that rect's corner, and `caps` reports the frame.
- **Outcomes**:
  - **Deliverables**: `grounding.py` + `test_grounding.py` (snapshot tester, model-free tests); `devices/windows.py` frame and caps; `agent/loop.py` window selection, the no-window refusal, delta drag, coordinate verbs, post-drag diff; `brain/client.py` schema and prompt; `api/server.py` window as selector; `devices/test_host_frame.py`, `agent/test_drag_and_pointer.py`. The council plan and its three contracts under `plans/2026-10-28-bryes-unreal-driving/`.
  - **Progress Made**: SP-1 and SP-2 done and merged to main; nine model-free suites green; the quality review found five issues and all five were fixed.
  - **Tech Debts**: **No live host run has exercised any of it** — the new frame, the delta drag or the coordinate verbs. `ruff` is still not installed, so the lint dimension is checked by eye. There is no `qa/` instrument, so no checklist exists for these changes. `WINDOWS_CAPS` still carries the virtual-desktop size as a fallback for capture.
  - **Next Steps**: A live host run with `BRYES_ALLOW_HOST=1` against a launched window, with a goal that forces `click_at` and an offset drag, then the transcript read for `CHANGES SINCE YOUR LAST ACTION`. Then SP-4 (the Windows and Unreal profiles) and SP-5 (the live `lsgi` build). With SP-3 dropped, R7's three wires need a decision: vision at 1/5 on pins, zoomed and verified, or by hand.
- **Insights**:
  - **New Understanding**: A hit rate belongs to the frame it was measured on. The same model on the same elements moves from 2/5 to 1/5 when the image around them changes, so "how good are the Eyes" is not a number until the frame shape is fixed.
  - **Pattern Recognition**: Asking a grounding model for empty space is asking it for nothing: 0 for 6, and every answer landed on an object. That is not a model defect, it is a probe defect, and it is the evidence behind the delta drag.
  - **Improvement Areas**: I reported rates as bare fractions that the reader could not decode, twice, before he asked. A measured rate needs its denominator said out loud.
- **Promotions**:
  → Promoted to [docs/orientation-map.md](../../docs/orientation-map.md) — a `grounding.py` entry and the host-frame note on `devices/`
  → Promoted to [.agents/knowledge/grounding-measurement.md](../knowledge/grounding-measurement.md) — the numbers, the method, and the frame rule
