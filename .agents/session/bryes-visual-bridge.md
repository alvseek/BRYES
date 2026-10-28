# BRYES — The Visual Bridge

Handing BRYES's eyes and hands to an agent outside it: the primitive surface, the host-body
fixes it forced, and the first real build driven through it.

---

### [2026-10-28 18.00] (agent: software-architect) — A BRIDGE FOR A CALLER THAT IS ITS OWN BRAIN, AND THREE HOST FIXES IT FORCED 🔌🎯🧱

- **Summary**: Built `api/bridge.py`, a primitive HTTP surface (windows, pointer, screenshot, down/up-scaled shots, act, locate, profiles) for a caller that needs no Brain, and drove a real Unreal edit through it: a `Print String` node and three execution wires in `BP_CombatBody_Enemy`, compiled clean, unsaved.
- **Context**: The Unreal-driving council had already measured that vision alone cannot wire a pin (1/5) and that BRYES should be a body, not a decision-maker. This session built the body's primitive layer, then proved it from outside.
- **Discussion**:
  - **What BRYES is**:
    - **Alvi's Input**: "making sure BRYES can act as a bridge from agent outside BRYES to do visual thing", then the correction "both inside and outside agent need to have those vocabulary so they can communicate well, especially the locate by description".
    - **My Response**: Retired the Unreal-API channel (SP-3) and made the surface primitives only: no goal, no loop, no decision. Profiles became shared vocabulary, not private knowledge.
  - **Screenshots**:
    - **Alvi's Input**: asked for a downscaled shot and a focused one, "for practicality, let's name it /downscaleshot and /upscaleshot", each returning its multiplier.
    - **My Response**: Both routes, with one mapping rule and the numbers in headers: `frame_px = origin + returned_px / scale`.
  - **The last task**:
    - **Alvi's Input**: bring Unreal to the foreground, open Project Settings, GAME → LSGI Combat Encounter, Default Arena Provider → LSGIArenaLevelProvider, close it.
    - **My Response**: All five steps through the bridge, each target measured on a zoomed crop first.
- **Key Interactions**: "nice. that was well done", after the settings edit; "why are you driving?" when I answered a design question with code instead of words; "lemme think lemme think" before the screenshot redesign.
- **Issues Encountered**:
  - **Problem Description**: Every action refused with `could not bring the target window to the foreground` while another app held focus.
  - **Root Cause**: Windows refuses `SetForegroundWindow` to a process that does not already own the foreground; a bridge started from a terminal never does.
  - **Resolution**: `_raise_window` borrows the current foreground thread's input queue via `AttachThreadInput` for the length of the call.
  - **Problem Description**: Typing into the Unreal context menu made the text appear and then the menu vanished.
  - **Root Cause**: The foreground window while a menu is open is the menu itself, a different window, so the guard raised the editor and dismissed it.
  - **Resolution**: `foreground_is_target` walks the GW_OWNER chain, so a window the target owns counts as the target.
  - **Problem Description**: A drag from a pin moved the node instead of wiring it.
  - **Root Cause**: The press was 17 px right of a 12 px pin, on the node body. No error anywhere.
  - **Resolution**: Measure pins on a 6x crop; the retry at (1305,959) landed the wire. `Ctrl+Z` named the earlier mistake (`Undo: Move Node`).
- **Outcomes**:
  - **Deliverables**: `api/bridge.py` + `api/test_bridge.py` (8 model-free tests); `profiles/windows/profile.md` and `profiles/windows/unreal-editor/profile.md` plus their catalog section; the host fixes (`foreground_is_target`, `_raise_window`, `_ensure_pointer_in_frame`, `pointer()`, `safe_point`); the bridge section in `docs/procedures/drive-the-desktop.md`; `api/README.md`; the orientation map; a council plan with SP-1, SP-2, SP-4, SP-6 closed and SP-5 at three of three wires.
  - **Progress Made**: Every route proven live; the screenshot/focus/pointer chain measured end to end; the settings task completed.
  - **Tech Debts**:
    - **[new] The bridge exposes 1 of the Eyes' 4 primitives**: no `describe`, no `box`, no `diff`. A caller must read images itself.
    - **[new] `/locate` sees the whole frame**, with no focus region and no profile priming.
    - **[new] The Unreal settings change is applied in the editor but was not verified as written to `DefaultGame.ini`**; the window was closed without an explicit save.
    - **[new] `BP_CombatBody_Enemy` holds an unsaved `Print String` node and three wires** from the proof run.
    - **[carry] The window enumerator lives in `api/bridge.py`**, not `devices/windows.py`, to avoid a conflict with SP-2; it can move now that SP-2 is merged.
    - **[carry] Unreal's `L_TitleScreen` level** was open during the settings task; the blueprint tab was not re-checked afterwards.
  - **Next Steps**:
    - Add `describe` and `diff` to the bridge, the two that a caller cannot do for itself.
    - Decide whether `locate` should take a focus region and the profile's visual half.
    - Finish SP-5's remaining record work and run the council's completion checklist + QA handoff.
- **Insights**:
  - **New Understanding**: A guard written for a person driving one app breaks for a background caller: focus is not a property a server can hold, so the check has to move to what actually matters (which window owns focus, and where the pointer is).
  - **Pattern Recognition**: `8c1d5e93` and `0eb34b96` in one session: the pick that dismissed the menu was a *neighbour* of the cause (the raise), and the drag that moved a node was a valid action, just not the intended one.
  - **Improvement Areas**: I twice claimed a mechanism was blocked (menus, drag) from one failed attempt; the user's own eyes on his screen corrected both.
- **Promotions**:
  → Promoted to [.agents/knowledge/visual-bridge.md](../knowledge/visual-bridge.md) — the surface, the mapping rule, the three host fixes, and what driving Unreal by hand costs.
  → Promoted to [docs/procedures/drive-the-desktop.md](../../docs/procedures/drive-the-desktop.md) — the bridge section, the frame paragraph, and the failure modes.

---
