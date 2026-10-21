# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES
- **Date**: 2026-10-20
- **Agent**: software-architect
- **Theme**: Host body — drive the real Windows desktop instead of the Docker sandbox
- **Source Protocol**: `/high-wizard` — /high-wizard

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **INHERITED CONTEXT**
*Filled at investigation step 0 with whatever was settled before this plan existed. The two sources are recorded separately and never merged — write "None" under a part that does not apply.*
*These decisions are **not yours to reopen**. If one looks wrong, STOP and surface it to [USER-NAME] — do not silently re-decide it here or in Confirmed Decisions below.*

### From the Parent Plan
- **Parent plan**: None — not a sub-plan.
- **Assigned scope**: N/A.
- **Integration contracts**: None.
- **Pushed-down open items**: None.

### From Pre-Planning Discussion
- **Discussion**: Pre-planning discussion with Alvi, 2026-10-20 (same session, immediately before this plan).
- **Agreed scope**: add a body that operates the working Windows OS directly instead of the disposable Docker sandbox, so BRYES can drive the machine Unreal lives on.

| # | Settled decision | Chosen | His reason | Status |
|---|------------------|--------|------------|--------|
| 1 | Whether BRYES drives, or only captures | It drives | "wdym, it CAN drive Unreal" — the capture-only body was a build-time choice, not a capability limit | Settled |
| 2 | What the new body targets | The working operating system, not the sandbox | "add bypass sandbox from docker feature, and directly operate on the working operating system" | Settled |
| 3 | How to plan this piece | High Wizard | "using QW or HW?" then "go" | Settled |

- **Considered and rejected**: Hardware HID input (a Pico or Arduino presenting as a real keyboard/mouse) → not chosen; it costs a device and buys nothing on a local desktop that accepts synthetic input. It stays a fallback if synthetic input is refused, not a decision to make now.
- **Left open**: the input mechanism (SendInput / UI Automation / hardware HID); the safety posture and default guard; whether Unreal's Python or Remote Control API enters as a Tier-1 action in this plan or a later one.

---

## **OBJECTIVES**
Give BRYES a body that drives the **real Windows desktop**, so a run can operate applications that live outside the disposable container (Unreal Editor first), without giving up the safe default: the container stays what an unqualified run picks, and reaching the host is a deliberate act.

### **Related Documents**
- [ADR-002 — the Device interface](docs/adr/2026-07-15-device-interface.md) — the body abstraction this extends; it already names "a future Windows desktop"
- [ADR-001 — effector hierarchy](docs/adr/2026-07-15-effector-hierarchy.md) — API > shell > vision, the reason an Unreal API action is a later Tier-1, not this plan
- [docs/architecture-overview.md](docs/architecture-overview.md) — the current module coupling
- [docs/quality-standard.md](docs/quality-standard.md) — the nine dimensions this implementation is reviewed against
- [devices/windows.py](devices/windows.py) — the capture-only body this upgrades

### **SUCCESS CRITERIA**
- [ ] `run(goal, device="windows", window="<title substring>")` drives the real desktop end to end on one real task, verified by the next frame showing the effect
- [ ] Host targeting refuses unless `BRYES_ALLOW_HOST=1`; `shell()` refuses unless `BRYES_ALLOW_HOST_SHELL=1`. Both proven by a test, not by reading the code
- [ ] The auto-picker cannot select the host: `profiles/index.md` is unchanged and `resolve_embodiment` never returns `windows`
- [ ] A click lands correctly on every monitor in the current layout, including a non-zero virtual origin (unit-tested with a simulated origin, since the live layout is currently 0,0)
- [ ] `act()` is unit-testable without touching the real mouse: an injected fake input layer records the events
- [ ] The container and phone suites still pass unchanged

---

## **SCOPE**

### In Scope
- Driving on `WindowsDevice`: `act()` for the pointer verbs, `clear_field()`, `type_into()`, and a gated `shell()`
- A thin input adapter over `pyautogui` that owns three things the library does not: the virtual-origin translation, the foreground guard, and an injectable seam for tests
- Registering the body in `_ROOT_DEVICE` so `device="windows"` resolves, and confirming `KNOWN_DEVICES` picks it up without further wiring
- The `window` parameter on `run()` and on `POST /tasks`, passed to the body and nowhere else
- Model-free tests for the adapter and the gates, plus one live smoke script that drives the real desktop

### Out of Scope
- **UI Automation / element-level control.** Needs a probe first; Unreal's Slate UI is unmeasured, and Aquazone's WinForms is its own plan
- **Unreal's Python or Remote Control API as a Tier-1 action.** The right long-term effector per ADR-001, deliberately deferred
- **Hardware HID.** Measured unnecessary: pyautogui reached both monitors when the layout had two
- **Any change to the lessons pipeline, the Eyes, or the Brain prompt.** The Brain's vocabulary already follows `caps`
- **Retiring or altering the container body.** It stays the default and the disposable surface

---

## **CONFIRMED DECISIONS**
*Decisions made **by this plan** — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A and B decisions made by the agent, recorded with their reasoning). The reasons serve as the analysis record.*
*Decisions settled before this plan existed — by a parent, or in a pre-planning discussion — belong in [INHERITED CONTEXT](#inherited-context) above, not here. Keeping them separate is what shows which decisions this plan actually owns.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | How a run reaches the host body | Explicit `device="windows"` **and** `BRYES_ALLOW_HOST=1`; never in the profile catalog | Alvi's call (1A). The vector that decides it is the localhost task API, which has no auth: a page open in a browser can POST to `127.0.0.1:8100` even when it cannot read the reply. With the gate, that POST starts nothing |
| 2 | What the body may do | `ALL_VERBS` plus `has_shell=True`, and `shell()` gated by its own `BRYES_ALLOW_HOST_SHELL=1` | Alvi's call (2C). A click can be undone by noticing it; a recursive delete cannot, and the two deserve separate switches |
| 3 | Input mechanism | `pyautogui` 0.9.54 for pointer and keyboard | Alvi's call (B), then measured: it reached the centre of both monitors on the two-monitor layout, including the one at negative y. Writing a ctypes layer was rejected as reinventing a maintained library. Cost accepted: 7 transitive packages |
| 4 | What the body captures | The whole virtual desktop | Alvi's call (A). Image and screen share one frame, so nothing can go stale when a window moves or resizes |
| 5 | Image-to-screen coordinate mapping | One translation in the body, `screen_xy(x, y) = (x + origin_x, y + origin_y)` | Measured trap: on the earlier layout the virtual origin was (0,−1080), so ignoring it put every click on the upper monitor 1080 px off. The live layout is now a single monitor at (0,0), which is why the test simulates a non-zero origin instead of trusting today's desk |
| 6 | `pyautogui.FAILSAFE` | Disabled inside the body | Measured: with the flag on, a target beyond the primary raised `FailSafeException` instead of moving, and the restore failed too. The body's own foreground guard replaces what the flag was standing in for |
| 7 | Focus handling | Before each action, compare `GetForegroundWindow()` to the target; re-raise, and after three failures raise an error rather than act | A stale coordinate is a wrong click; a wrong click into whatever took focus is the failure this plan exists to prevent |
| 8 | Where the gates live | On `act()`, `clear_field()`, `type_into()` and `shell()` inside `WindowsDevice`, plus a fail-fast check in `_make_device` | Every path that acts constructs the body, so the checks cover `run()`, the task API and any future caller. Deliberately **not** in the constructor: `capture.py` builds a `WindowsDevice` for screenshots, and gating construction would break the lesson pipeline for no safety gain. Corrected while writing the solution; the original decision said "constructor" |
| 9 | `window` parameter | On `run()` and `POST /tasks`, passed to the body only | The loop, the Brain and the Eyes never see it: it names a surface, not a fact about the task. Keeping it out of the prompt avoids spending tokens on a constant |

---

## **SOLUTION**

### Architecture Overview

The body abstraction does the work it was built for: **nothing above the body changes except one parameter.** `WindowsDevice` owns the window and the coordinate space; a new `HostInput` adapter owns `pyautogui` and the focus guard; the loop and the task API pass a window title through and never look inside.

- **Downward:** every action arrives as an *image-space* coordinate (what the Eyes saw). The body adds the live virtual origin and hands *screen-space* coordinates to the adapter.
- **Outward:** `windows` joins `_ROOT_DEVICE`, so `device="windows"` resolves and `KNOWN_DEVICES` derives it with no extra wiring.
- **Gate:** `_make_device("windows")` refuses early with a clear message; `act()` and `shell()` refuse again at the point of use. Capture keeps working, because `screenshot()` is never gated.

### Component 1: HostInput adapter
- **Purpose**: the only code that talks to `pyautogui`, and the seam that makes the body testable without moving the real mouse. Absolute screen coordinates in, actions out.
- **Key Files**: [`devices/host_input.py`](devices/host_input.py) (new)

### Component 2: WindowsDevice, driving
- **Purpose**: turn a verb plus an image coordinate into the right adapter call, keep the target window in front, and hold both gates.
- **Key Files**: [`devices/windows.py`](devices/windows.py) (extended)

### Component 3: Wiring
- **Purpose**: let a caller name the body and the window, from Python or over the task API, without either one learning what a window is.
- **Key Files**: [`agent/loop.py`](agent/loop.py) (`_ROOT_DEVICE`, `run()`, `_make_device`), [`api/jobs.py`](api/jobs.py) (`submit`), [`api/server.py`](api/server.py) (`/tasks`)

### Integration Architecture

| Component | Integrates With | Data Flow | Dependencies |
|-----------|----------------|-----------|--------------|
| `HostInput` | `WindowsDevice` | screen `(x, y)` + verb → `pyautogui` call | `pyautogui` |
| `WindowsDevice` | `HostInput`, `_ROOT_DEVICE`, the Brain's caps | image `(x, y)` → `+ origin` → screen `(x, y)` → adapter | `host_input`, the live virtual origin |
| `_make_device` | `run()`, `api/jobs.py` | `device="windows"` + `window=` → constructed body, or a clear refusal | `BRYES_ALLOW_HOST` |
| `run()` / `POST /tasks` | the body only | `window` string passed through untouched | none above the body |
| `KNOWN_DEVICES` | `api/server.py` validation | derives from `_ROOT_DEVICE`, no code change | none |

<!-- OPTIONAL SECTION C: Include when significant technical constraints exist -->
### Technical Considerations

- **The virtual origin is not zero on every desk.** Measured twice in one session: (0,−1080) with a monitor above, then (0,0) after the layout changed. Image coordinates and screen coordinates differ by that origin, so it is read **per action**, not cached at import. A cached origin is a click 1080 px off after any display change.
- **`pyautogui.FAILSAFE` must be off.** With it on, a target beyond the primary raised `FailSafeException` and the pointer could not even be restored. The body's foreground guard is the safety property that replaces it.
- **`pyautogui.size()` reports the primary only.** It is not used for anything; the virtual box comes from `GetSystemMetrics(76..79)`.
- **UIPI.** Synthetic input cannot reach a window running at a higher integrity level than the Python process. If Unreal runs elevated and BRYES does not, `act()` will look successful and change nothing. Only the live smoke test detects this.
- **Typing beyond ASCII.** `pyautogui.write` follows the keyboard layout, so Indonesian text or symbols cannot be typed that way. `type_text` uses `write` for ASCII and a clipboard paste (via `pyperclip`, already installed as a pyautogui dependency) for anything else.
- **Seven transitive packages.** `pyautogui` brings `pytweening`, `pyscreeze`, `pyrect`, `pyperclip`, `pymsgbox`, `pygetwindow`, `mouseinfo`. Accepted with the choice; listed in `requirements.txt` so the tree is visible.
- **Display changes mid-run.** Capturing a whole desktop means the image size can change between two frames. The body re-reads the box each capture, and the Eyes receive whatever size the frame actually is.

<!-- OPTIONAL SECTION F: Include for brainstorming/decision tasks, multiple viable approaches -->
### Solution Options & Evaluation

#### Solution Options
The effector choice, as it was actually narrowed. Each was measured or rejected on evidence, not preference.

| # | Solution | Description |
|---|----------|-------------|
| 1 | Write the input layer ourselves (ctypes `SendInput`) | ~120 lines, no dependency, full control of the virtual-desktop normalisation |
| 2 | `pyautogui` | Coordinate input, image search included, BSD-3, 7 transitive packages |
| 3 | `pynput` | Coordinate input via `SetCursorPos`, LGPL-3.0 |
| 4 | `uiautomation` / `pywinauto` | Element-level control by name, needs the app to publish an accessibility tree |
| 5 | Hardware HID (Pico/Arduino) | Real keyboard/mouse device; immune to injection filters |
| 6 | Windows-MCP as the body | An existing MCP server that clicks by element name; adopting it replaces the loop |

#### Evaluation

| Solution | Pros | Cons |
|----------|------|------|
| 1. ctypes ourselves | No dependency, exact control | Reinvents a maintained library, and the maintenance is ours |
| 2. `pyautogui` | Measured working on both monitors, BSD-3, image search later | 7 packages; `FAILSAFE` must be off; `size()` is primary-only |
| 3. `pynput` | Also measured working on both monitors | LGPL-3.0; no image search |
| 4. UIA libraries | Layout-proof where a tree exists | Unreal's Slate is unmeasured; a null result drives nothing |
| 5. Hardware HID | Works past injection filters and elevation | A device, a flashing step, and no need on a local desk |
| 6. Windows-MCP | Real prior art, element-addressed | Not a body: adopting it means replacing BRYES's loop |

#### Selected Approach
- **Chosen**: `pyautogui` (2), behind a thin `HostInput` adapter.
- **Rationale**: it and `pynput` both moved the pointer correctly to every monitor, including the one at negative y, once `FAILSAFE` was off. `pyautogui` won on licence and on bringing image search we may want for visual verification later. Writing it ourselves (1) was rejected outright on Alvi's call that prior art exists. Element-level (4) waits on a tree probe, and hardware (5) has no problem left to solve here.

<!-- OPTIONAL SECTION G: Include when task produces an architecture decision record -->
### ADR Output

- **ADR File**: [`docs/adr/2026-10-21-host-body-and-gates.md`](docs/adr/2026-10-21-host-body-and-gates.md)
- **Decision Summary**: BRYES gains a body that acts on the real Windows desktop, reachable only by explicit request plus an environment gate, with `shell` behind a second gate and image-to-screen coordinates translated by a live virtual origin.

---

## **IMPLEMENTATION PHASES**

### Phase 1: The adapter, and a body that can act
- [x] **Step 1.1**: `HostInput`, the only code that touches pyautogui
  - **Action**: Create `devices/host_input.py` with a small class that performs one action per call in **screen** coordinates: `click`, `double_click`, `right_click`, `hover`, `scroll`, `drag`, `press(chord)`, `type_text`, `pointer`.
  - **Implementation**: `pyautogui.FAILSAFE = False` set once at module import, with the measured reason in a comment. `type_text` writes ASCII directly and falls back to clipboard-paste (`pyperclip`, `ctrl+v`) for anything outside the layout. `press` maps the Brain's semantic chords (`Enter`, `ctrl+a`, `Escape`) to pyautogui key names. The class is passed in, not imported at the call site, so a fake can replace it.
  - **Testing**: `devices/test_host_input.py` with a `Recorder` fake: assert each verb calls the expected pyautogui function with the expected arguments, and that `type_text("harga Rp1.250.000")` takes the clipboard path while `"hello"` takes `write`. No test may call the real input.
  - **Success Criteria**: the adapter tests pass with the real module never invoked; `python -c "import devices.host_input"` succeeds on Windows.

- [x] **Step 1.2**: `WindowsDevice` gains verbs, the origin translation and both gates
  - **Action**: Extend `devices/windows.py`: `caps` advertises `ALL_VERBS` with `has_shell=True`; add `_origin()` (live `GetSystemMetrics(76/77)`), `screen_xy(x, y)`, `_ensure_foreground()`, `act()`, `clear_field()`, `type_into()`; keep `screenshot()` ungated.
  - **Implementation**: `act()` reads the verb, translates the image coordinate through `screen_xy`, calls `_ensure_foreground()` (three attempts, then `RuntimeError` naming the window), and dispatches to `HostInput`. `_require_host()` raises `RuntimeError` unless `BRYES_ALLOW_HOST=1`; `_require_host_shell()` the same for `BRYES_ALLOW_HOST_SHELL=1`. `clear_field` is `ctrl+a` then `Delete`; `type_into` delegates to `default_type_into`.
  - **Testing**: `devices/test_windows_drive.py`, model-free: with a fake input and a monkeypatched origin of `(100, -200)`, `act({"type":"click","x":10,"y":20})` must produce `click(110, -180)`. Gate tests unset the env vars and assert refusal for `act`, `clear_field`, `type_into`, `shell`. `screenshot()` must still work with the gate unset.
  - **Success Criteria**: translation and gate tests pass; the existing `devices/test_windows.py` still passes unchanged.

- [x] **Step 1.3**: `shell()`, on the host, behind its own gate
  - **Action**: Implement PowerShell `shell()` to the same result shape the container returns.
  - **Implementation**: reuse the existing subprocess implementation, add `_require_host_shell()` as the first line, and keep the timeout result shape identical.
  - **Testing**: refusal without the env var; with it set and a stub runner, the `{ok, exit_code, stdout, stderr}` shape is asserted. The live call is left to Phase 3.
  - **Success Criteria**: a shell call with `BRYES_ALLOW_HOST_SHELL` unset raises before any process starts.

### Phase 2: Wiring, so a caller can name the body and the window
- [x] **Step 2.1**: `_ROOT_DEVICE` and `run(window=...)`
  - **Action**: register `"windows"`; let `_make_device` take the window and refuse early when `BRYES_ALLOW_HOST` is unset; add `window=None` to `run()` and pass it only for the windows root.
  - **Implementation**: `_make_device(root, **kw)` forwards `window` to `WindowsDevice`; the fail-fast gate raises `RuntimeError` with the two ways to fix it (set the variable, or use the container). `run()` signature gains `window`, documented as body-specific.
  - **Testing**: `agent/test_run_selection.py` extended: `device="windows"` with the gate unset raises before a screenshot; `window` reaches the body (asserted with a stub body); a `linux` run ignores `window`.
  - **Success Criteria**: the selection tests pass and no existing test changes behaviour.

- [x] **Step 2.2**: The task API accepts `window`
  - **Action**: `submit(goal, device, profile, max_steps, window=None)` and `POST /tasks {window}`.
  - **Implementation**: pass-through, with one validation: `window` without `device="windows"` is a 400, because it silently does nothing otherwise.
  - **Testing**: `api/test_jobs.py` and `test_server.py` extended model-free with a stub run: the field arrives at the job; the 400 fires for a bare `window`.
  - **Success Criteria**: both API suites pass; a `window` on a linux run is refused, not ignored.

- [x] **Step 2.3**: Dependencies and prose
  - **Action**: `pyautogui` in `requirements.txt`; the host body described in `README.md` beside the other bodies; `docs/architecture-overview.md` updated where it lists bodies.
  - **Implementation**: requirements with a one-line comment naming the transitive tree; README gains a short paragraph and the two environment variables in the variables table.
  - **Testing**: `pip install -r requirements.txt` into a clean venv resolves; the README's variable table lists both gates.
  - **Success Criteria**: a fresh environment installs from the file; no doc claims a capability the code does not have.

### Phase 3: Live proof, and the record
- [x] **Step 3.1**: A smoke script that drives the real desktop
  - **Action**: `devices/smoke_windows_drive.py`, manual only, clearly marked as moving the real mouse.
  - **Implementation**: takes a window title and a goal, runs `run(..., max_steps=3)` with `verbose=True`, prints the transcript path, and restores the pointer on exit. Refuses to start unless both `BRYES_ALLOW_HOST` and a `--yes` flag are present.
  - **Testing**: run it against the Unreal editor: click the Outliner, and confirm the next frame differs from the previous one.
  - **Success Criteria**: a real step lands where the screenshot said; the transcript records it; the pointer is restored.

- [x] **Step 3.2**: ADR-009
  - **Action**: write `docs/adr/2026-10-21-host-body-and-gates.md`.
  - **Implementation**: from the ADR template, with the measured evidence (the two monitor layouts, the fail-safe failure, the origin), the two gates, and what was intentionally left out.
  - **Testing**: the links in it resolve; the plan links to it and it links back.
  - **Success Criteria**: the ADR states the decision, the alternatives, and what would reverse it.

---

## **EXECUTION LOG**
**Execution Protocol for AI**:
I have to use this document as my **ONLY** source of truth to execute and track the plan steps iteratively. I should **NOT** use additional tools like ToDos because it lacks the context of what should I do. Everytime I want to implement a step I have to check the reference to the original step plan above. Everytime a step has been finished I need to go back to this document to log what was done.
*In other words*:
- I have to make this document as the source of truth for the implementation phase on what I have worked on and what I will be working
- The original plan must be fully in my context, therefore, I have to make sure I loaded the **Plan File** before executing any task and read carefully the reference to the original step
- I have to do the implementation by doing it in order per step THEN, I ALWAYS have to fill the step log rightly after

**Definition of Done (applies to ALL steps)**:
- ✅ **Code Quality**: Code compiles/runs without errors
- ✅ **Testing**: Tests written and passing
- ✅ **Logged**: Implementation and testing logged below
- 🚫 **Blocked**: Get input from [USER-NAME] before assuming

### Phase 1:
- [x] **Step 1.1**: `HostInput`, the only code that touches pyautogui
  - **Implementation Log**: Created `devices/host_input.py` (106 lines): `HostInput(bind=None, clipboard=None)`, `pyautogui.FAILSAFE = False` at import with the measured reason, a `_KEY_ALIASES` table for the synonyms a model reaches for, `press()` splitting chords into `press`/`hotkey`, and `type_text()` typing ASCII directly and pasting anything non-ASCII through `pyperclip`. Created `devices/test_host_input.py` with a `RecorderPy` fake, so no test moves the pointer.
  - **Testing Log**: `python devices/test_host_input.py` green on six checks: pointer verbs one-to-one; scroll moves then scrolls; drag moves then drags; keys alias and chords become hotkeys case-insensitively; ASCII types, non-ASCII pastes; pointer returns ints. One test defect found and fixed while running it: my first "non-ASCII" example was `harga Rp1.250.000`, which is entirely ASCII, so the test asserted the clipboard path against a string that correctly took the `write` path.
  - **Success Criteria**: Pass — the adapter tests pass with the real module never invoked, and `import devices.host_input` works on Windows.
  - **Tech Debts**: none
  - **Result**: Pass

- [x] **Step 1.2**: `WindowsDevice` gains verbs, the origin translation and both gates
  - **Implementation Log**: Extended `devices/windows.py`: `caps` now advertises `ALL_VERBS` with `has_shell=True`; added `_env_flag`, `_require_host`, `_require_host_shell`, `_origin_xy` (live `GetSystemMetrics(76/77)`, never cached), `screen_xy`, `_get_input` (lazy `HostInput`, so a capture-only process never imports pyautogui), `_ensure_foreground` (three raises, then a `RuntimeError` that refuses to act on whatever holds focus), and the real `act`/`clear_field`/`type_into`. `screenshot()` untouched and ungated. Created `devices/test_windows_drive.py` with a `FakeInput` recorder and a simulated origin of `(100, −200)`.
  - **Testing Log**: `python devices/test_windows_drive.py` green on nine checks: all four acting paths refuse without `BRYES_ALLOW_HOST`; the screenshot still works ungated (2560×1440); every pointer verb translates by the live origin; scroll is signed by direction; drag translates both ends; type/key/clear_field reach the adapter; an unknown verb raises `ValueError`; a named-but-absent window refuses instead of clicking blind.
  - **Success Criteria**: Pass, with one amendment recorded in Tech Debts — the "existing `test_windows.py` unchanged" line could not hold, because that smoke asserted the *old* contract (`verbs == frozenset()`, `NotImplementedError`). Updated to assert the new one instead; all six of its checks pass.
  - **Tech Debts**: `devices/test_windows.py` was amended, not preserved (see above). Its shell check now opens both gates for the length of the call and restores the environment afterwards.
  - **Result**: Pass

- [x] **Step 1.3**: `shell()`, on the host, behind its own gate
  - **Implementation Log**: `shell()` now calls `_require_host_shell()` first, which chains `_require_host()`, so neither switch alone is enough; the subprocess body and its result shape are unchanged from the capture-only version.
  - **Testing Log**: covered in `devices/test_windows_drive.py`: with only `BRYES_ALLOW_HOST` set it refuses; with both set, `Write-Output bryes-host-shell-ok` returns `ok=True` and the text on stdout. `devices/test_windows.py` also round-trips a real PowerShell call with both gates open.
  - **Success Criteria**: Pass — a shell call with `BRYES_ALLOW_HOST_SHELL` unset raises before any process starts.
  - **Tech Debts**: none
  - **Result**: Pass

### Phase 2:
- [x] **Step 2.1**: `_ROOT_DEVICE` and `run(window=...)`
  - **Implementation Log**: `_ROOT_DEVICE` gained `"windows": WindowsDevice`; `_make_device(root, **kw)` now refuses early for the host when `BRYES_ALLOW_HOST` is unset (one readable line instead of dying at the first click) and forwards `**kw`; `run()` gained `window=None`, materialises a body NAME through `_make_device`, and raises `ValueError` when `window` arrives with anything other than `device="windows"`. The transcript's embodiment note now carries the window.
  - **Testing Log**: `python agent/test_run_selection.py` ALL PASS, 12 checks, three of them new: the host refuses without the variable (both `_make_device` and `run`), it resolves with the gate open and carries `window`, and a `window` with no host body is refused. Two existing-check repairs were needed and made: (a) the "unknown body" fixture used `"windows"` as its example, which stopped being unknown the moment the body was registered, so it now uses `"macos"`; (b) `_raises()` caught only `RuntimeError`, so it was widened to `(RuntimeError, ValueError)` because `run()` now refuses a contradictory argument with the more accurate type.
  - **Success Criteria**: Pass
  - **Tech Debts**: a negative fixture that names a real thing decays the moment the thing becomes real; the comment beside it now says so.
  - **Result**: Pass

- [x] **Step 2.2**: The task API accepts `window`
  - **Implementation Log**: `JobManager.submit(..., window=None)` threads it into `_run_job`, which spends it at body construction (`_make_device(device, window=window)`) so the loop itself never sees it. `POST /tasks` accepts the field and returns 400 when it arrives without `"device": "windows"`.
  - **Testing Log**: `python api/test_server.py` ALL PASS (15 checks, three new: window on a non-host body 400, window with no device 400, `windows` is in `KNOWN_DEVICES`); `python api/test_jobs.py` ALL PASS (21). One environment gap surfaced first: Flask was declared in `requirements.txt` but not installed in `C:\Python313`, so the API suite could not run at all until it was installed.
  - **Success Criteria**: Pass
  - **Tech Debts**: none
  - **Result**: Pass

- [x] **Step 2.3**: Dependencies and prose
  - **Implementation Log**: `requirements.txt` gained `pyautogui>=0.9.54` (with its transitive tree named in a comment) and `pyperclip>=1.8` (imported directly by the adapter, so listed rather than assumed). `README.md`'s third-body paragraph was rewritten from "records instead of drives" to the gated driving body, and both environment variables joined the variables table. `docs/architecture-overview.md`'s body table now describes `WindowsDevice` instead of calling it future work.
  - **Testing Log**: `pip install -r requirements.txt --dry-run` resolves with everything satisfied; every suite above re-run green after the doc edits.
  - **Success Criteria**: Pass
  - **Tech Debts**: none
  - **Result**: Pass

### Phase 3:
- [x] **Step 3.1**: A smoke script that drives the real desktop
  - **Implementation Log**: `devices/smoke_windows_drive.py`, rewritten after the accident to obey both harness rules: it launches the target itself (`--launch "<cmd>"`), addresses it by **hwnd from the target's pid**, and terminates only that process. `WindowsDevice` gained `hwnd=`, `windows_of_pid()`, `top_window_of_pid()` and `window_title()`, so a driver names its target by handle instead of by title substring.
  - **Testing Log**: four live proofs, in order of what they close. (1) The accident's root cause: the previous probe matched the largest window containing "Notepad", which was Alvi's own document, typed into it, and then killed the shared single-instance process. (2) `artifacts/probe_host_live.py` against a throwaway Tkinter target: clicked it, typed, and read the text back from the target's own title — `bryes-probe-target|bryes host body ok 12345`, so **synthetic input reaches a real un-elevated application**. (3) `artifacts/probe_loop_fake.py` with a scripted brain: `run()` resolved the host body, captured whole-desktop frames, clicked, typed, reported done, title `bryes-probe-target|hello from the loop` — **the loop wiring drives the body**, with 6 model calls avoided by stubbing. (4) **The real-model smoke**, after Alvi added `OPENROUTER_API_KEY`: `smoke_windows_drive.py` launched its own target, the Brain saw it, chose `type_into "hello"` on the first step, the second step confirmed and stopped — `status: done, steps: 2`, and the target's title came back **`bryes-probe-target|hello`**. Timing recorded: describe 10.6 s, decide 31.4 s across two steps.
  - **Success Criteria**: Pass on substance — `run()` drove the real desktop end to end on one real task, verified by the target's own state rather than a screenshot. The target was a throwaway window rather than Unreal, because the editor was closed while that work shipped elsewhere.
  - **Tech Debts**: none open. The Unreal run is a repeat of the same command once the editor is open.
  - **Result**: Pass

- [x] **Step 3.2**: ADR-009
  - **Implementation Log**: wrote `docs/adr/2026-10-21-host-body-and-gates.md` from the template: problem, the two-gate decision with the measured origin and fail-safe evidence, requirements and success criteria, and four rejected alternatives.
  - **Testing Log**: the ADR links back to this plan and is linked from it; `docs/architecture-overview.md` now references it beside the body table.
  - **Success Criteria**: Pass
  - **Tech Debts**: none
  - **Result**: Pass

...{next phases as needed}...

---

## **QUALITY REVIEW**
*Filled by procedure Step 16 (delegated to `/analyze-code-quality` in embedded mode) after all execution phases are complete. **Static** review — answers "is the code clean?".*

- **Scope**: devices/host_input.py, devices/windows.py, devices/smoke_windows_drive.py, agent/loop.py, api/jobs.py, api/server.py, capture.py and their tests — reconciled against `git status --short`, which also sees the new files.
- **Quality Standard**: docs/quality-standard.md present; Dimensions 1 (error handling), 4 (efficiency), 5 (security), 7 (consistency), 8 (tooling), 9 (project conventions) applied.
- **Findings**:
  - **Critical — `agent/loop.py:_make_device`.** `run(device="linux")` and `POST /tasks {"device":"linux"}` were **broken**: `window=None` was forwarded to every body constructor and `ContainerDevice` accepts no such parameter (`RuntimeError: chose body 'linux' but it's unavailable: ContainerDevice.__init__() got an unexpected keyword argument 'window'`). No test caught it, because every test builds an instance or a fake and never a body name. Fixed by dropping `None` kwargs before construction, with two regression checks added.
  - **Medium — `devices/host_input.py` set `pyautogui.FAILSAFE = False` at import.** That mutates a third-party module for anything else in the process. Moved into `HostInput.__init__`, so the side effect happens when the adapter is used rather than when the file is imported.
  - **Medium — `type_text` could not type a newline.** `pyautogui.write("a\nb")` produces no line break, so multi-line text arrived mangled. Now splits on newlines and presses Enter between lines, with a test asserting the write/press/write sequence.
  - **Low — `find_window_rect`** has no production caller any more (capture goes through `grab_window`). Kept and documented as the injectable pure-function seam the matcher test uses.
- **Fixed**: all four, then every suite re-run green (7 suites; 21 and 15 checks in the API pair).
- **Fixed**: [What was fixed from approved findings, or "N/A"]

---

## **QA HANDOFF**
*Filled by procedure Step 17 after Quality Review is resolved. This plan is **not** runtime-verified — this section records the plan for that verification, which happens in a QA session with the stack up.*

- **Scope**: devices/windows.py, devices/host_input.py, agent/loop.py, api/jobs.py, api/server.py, tests, README, docs/architecture-overview.md, docs/adr/2026-10-21-host-body-and-gates.md
- **QA instrument**: NOT SET UP — BRYES has no `qa/` directory, no `qa/qa-map.md` and no bench, so `/generate-qa-checklist` auto-skips. Nothing was invented to fill the gap.
- **Integration coverage**: **NONE** — no bench and no stack, so this plan ships without integration coverage. Confirmed with Alvi before implementation (the alternative was to build the QA instrument first, which is a larger piece of work than this plan).
- **Checklist**: none — skipped, no QA instrument in this project
- **Coverage split**: unit only — `devices/test_host_input.py`, `devices/test_windows_drive.py`, `agent/test_run_selection.py`, `api/test_jobs.py`, `api/test_server.py`, all model-free
- **Runtime verification**: **NOT DONE.** Next action: the Phase 3 live smoke (`devices/smoke_windows_drive.py`) is the closest thing this plan has, and it is a manual proof, not a regression suite. Building the instrument (`/map-qa-instrument create` → `/build-qa-bench`) is the follow-up that would make this project's future plans runtime-verifiable at all.

> Do not read a filled checklist as a passed one. This section says a verification *plan* exists, nothing more.

---

## **POST-COMPLETION**
After all phases are executed, logged, and both **Quality Review** + **QA Handoff** are filled, move this plan to `plans/completed/`:
`mkdir -p ./plans/completed && mv ./plans/[this-file].md ./plans/completed/[this-file].md`
