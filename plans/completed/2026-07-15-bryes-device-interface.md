# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES
- **Date**: 2026-07-15
- **Agent**: claude-software-architect
- **Theme**: Device interface (ADR-002) — extract Screen+Hands+shell into a swappable `Device` abstraction so the agent can inhabit multiple vision-controllable bodies (Docker desktop today, Android phone next, Windows later); Brain+Eyes+loop stay device-agnostic.
- **Source Protocol**: `/high-wizard` — [Procedure](//@agent-memory/control-files/procedures/high-wizard.md)

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **OBJECTIVES**
Extract BRYES's Screen + Hands + shell (today a single HTTP-backed Docker desktop) into a swappable **`Device`** abstraction — a *vision-controllable body* (screenshot + pointer/keyboard + optional shell) — so the perceive→decide→act loop, the Brain, and the Eyes stay **device-agnostic** and the agent can inhabit multiple bodies. Prove the abstraction by adding a second, differently-shaped device — an **Android phone over ADB/USB** — and validate it **live on the physical device**. Capture the architecture as **ADR-002** (orthogonal to ADR-001: ADR-001 = which effector *tier*; ADR-002 = which *body*).

### **Related Documents**
- [architecture-overview.md](../docs/architecture-overview.md) - The 4-piece HTTP architecture being refactored
- [agent-loop-flow.md](../docs/agent-loop-flow.md) - The loop data-flow (Screen/Hands/Eyes/Brain wiring)
- [ADR-001 effector-hierarchy](../docs/adr/2026-07-15-effector-hierarchy.md) - The orthogonal tier axis (API/shell/vision)
- [backlog.md](../docs/backlog.md) - Open work; the phone/WhatsApp north star

### **SUCCESS CRITERIA**
- [ ] `Device` Protocol + `Capabilities` manifest defined; the loop depends on the abstraction, never on a transport
- [ ] `ContainerDevice` extracted; today's behavior **byte-identical** (`test_hands.py` + `test_shell.py` pass unchanged)
- [ ] Brain action vocabulary assembled from the **active device's `caps.verbs`** (device-capabilities preamble); container run still works end-to-end
- [ ] `PhoneDevice` implemented against the interface (adb `screencap` / `input` / `adb shell`, phone capabilities)
- [ ] **Live**: the agent performs a real action on the physical phone *through the unchanged loop* — the interface validated by device #2
- [ ] **ADR-002** written; docs updated (architecture-overview, agent-loop-flow, orientation-map, context-index/backlog)
- [ ] No regressions to the container path

---

## **SCOPE**

### In Scope
- **`devices/` package**: `base.py` (`Device` Protocol + `Capabilities` dataclass), `container.py` (`ContainerDevice` wrapping today's HTTP calls to `localhost:8000`), `phone.py` (`PhoneDevice` via adb)
- **Brain**: device-capabilities preamble + action list parameterized from `caps.verbs` (keep the tuned prose intact)
- **Loop**: `run(goal, device=None)` defaults to `ContainerDevice`; the action dispatch becomes device-agnostic
- **Phase 0 (host prep)**: adb platform-tools (installed ✓) + connect/authorize the physical phone (`adb devices` sees it)
- **`PhoneDevice` capability mapping**: no `right_click`; Back/Home named keys; `scroll`→adb swipe; android shell flavor; configurable `adb_path`
- **ADR-002** + doc updates (architecture-overview, agent-loop-flow, orientation-map, context-index/backlog)
- **Live validation** of one real action on the physical phone through the loop

### Out of Scope
- **Tier-1 API/MCP channels** (no screen) — a *different* effector abstraction, deliberately excluded (ADR-001's future tier)
- **`WindowsDevice`** — named as the third body, not built now (YAGNI until a real Windows task)
- **The WhatsApp end-to-end task** (the north-star use case) — a follow-up once the phone *body* works
- **ADBKeyboard / emoji-robust text input** — deferred until a task needs emoji (`input text` suffices for the first proof)
- **Eyes changes** — none needed (coordinate space is read per-screenshot → resolution-agnostic)
- **Async / loop concurrency** — unchanged (single sequential loop, per ADR-001's deferred async)
- **ADB-over-WiFi** — USB first (most reliable); WiFi is a later convenience, not this plan

---

## **CONFIRMED DECISIONS**
*These decisions were collected during investigation — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A/B decisions made by the agent with reasoning, per [What to Surface](../procedures/wait-options.md#what-to-surface)). The reasons serve as the analysis record.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | Interface form | Python `Device` **Protocol** + `Capabilities` dataclass; transport private per device | Dependency inversion — the loop depends on the abstraction; HTTP / adb / pyautogui are each device's private detail. Interface earns its keep at the *second* implementation (the phone), so now is the right time (not premature). |
| 2 | Name | **`Device`** (not `Screen`) | The interface bundles perceive **+** act **+** shell; "Screen" is only the perceive half. Alvi: "Device is correct." |
| 3 | Phone scope in this plan (D1) | **B** — `PhoneDevice` fully written **+ live bring-up** | Phone is adb-ready (confirmed); writing it against the interface validates the abstraction against a genuinely different 2nd body, and live proof is the milestone. |
| 4 | Brain device-awareness (D2) | **A** — device-capabilities preamble + parameterized action list; keep tuned prose | The Brain only sees verbs the active device supports (no `right_click` on a phone); preserves the bake-off-proven prompt. Vocab is hardcoded today in `brain/client.py` (SYSTEM_PROMPT + VALID_ACTIONS + JSON enum). |
| 5 | Package layout + default device (D3) | **A** — `devices/` package; `run(device=None)` defaults to `ContainerDevice` | Back-compatible: existing `run(goal)` calls + `test_phase4.py` keep working; container stays the zero-config default body. |
| 6 | adb install | **A** — manual platform-tools zip → gitignored `tools/`; configurable `adb_path` | No admin, self-contained; installed ✓ (`v37.0.0` at `tools/platform-tools/adb.exe`). A configurable path is the right `PhoneDevice` shape anyway. |
| 7 | `scroll` on phone (write-through) | Keep the `scroll` verb; `PhoneDevice` implements it as an adb **swipe** | Stable Brain vocab across bodies; the Brain reasons in *intents* (scroll down), each device translates intent→primitive. |
| 8 | Eyes (write-through) | **Unchanged** | `eyes/client.py:160` reads the coordinate space from each screenshot's actual dims → portrait phone frames work as-is. Device-agnostic mind. |
| 9 | ADR-002 vs ADR-001 | **Orthogonal** — tier (how to act) vs body (which body) | A device's `Capabilities` expresses which tiers it offers (`has_shell`, `verbs`). |
| 10 | `ContainerDevice` extraction | **Byte-identical**; no "improvements" during the refactor | `test_hands.py` + `test_shell.py` are the safety net; separating refactor from enhancement reduces risk. |

---

## **SOLUTION**

### Architecture Overview

Today the loop is hard-wired to one body: `agent/loop.py` calls `screenshot()` / `hands()` / `exec_cmd()`, each an HTTP request to the container's Flask API at `localhost:8000`. This plan **inverts that dependency**: the loop depends on a **`Device`** abstraction — a *vision-controllable body* exposing `screenshot()`, `act()`, and (optionally) `shell()`, plus a `Capabilities` manifest. Concrete devices implement it; **transport is each device's private detail**. The Brain reads the active device's `Capabilities` to assemble its action vocabulary. The Eyes are untouched (already resolution-agnostic).

```
                    ┌───────────────────────────────────────┐
  HOST (Python)     │  agent/loop.py   run(goal, device)      │
                    │    depends on ▶ Device (Protocol)        │
                    │    brain.decide(goal, obs, hist, caps)   │──▶ OpenRouter (Eyes+Brain)
                    └──────────────────┬──────────────────────┘      (unchanged)
                                       │ device.screenshot() / act() / shell()
                        ┌──────────────┴───────────────┐
                        ▼                               ▼
              ┌───────────────────┐          ┌───────────────────────┐
              │ ContainerDevice   │          │ PhoneDevice            │
              │  transport: HTTP  │          │  transport: adb (USB)  │
              │  → localhost:8000 │          │  → screencap/input/sh  │
              │  DESKTOP_CAPS     │          │  PHONE_CAPS 1080×2400  │
              └───────────────────┘          └───────────────────────┘
              (today's Screen, byte-identical)   (new — device #2, the proof)
```

The mind (loop + Brain + Eyes) is written once; bodies are swappable. `WindowsDevice` (future) slots in the same way. Pure API/MCP channels (no screen) are deliberately NOT `Device`s.

### Component 1: `devices/base.py` — the `Device` Protocol + `Capabilities` (NEW)
- **Purpose**: the abstraction the loop depends on (dependency inversion). Defines `Capabilities` (`name`, `width`, `height`, `verbs: set[str]`, `has_shell`, `shell_flavor`, `keys: dict`) and the `Device` Protocol (`caps`, `screenshot() -> bytes`, `act(action: dict) -> None`, `shell(command, timeout, stdin) -> dict`, `pointer() -> tuple | None`).
- **Key Files**: `devices/base.py` (new), `devices/__init__.py` (new)

### Component 2: `devices/container.py` — `ContainerDevice` (NEW; wraps today's Screen)
- **Purpose**: today's HTTP-backed Screen re-expressed as a `Device`, **behavior byte-identical**. Wraps the exact `urllib` calls the loop uses now (`/screenshot`, `/action`, `/exec`, `/pointer`) with the same 4-retry cold-connection handling. Advertises `DESKTOP_CAPS`: all 8 pointer verbs (incl. `right_click`/`hover`), `has_shell=True`, `shell_flavor="bash"`, X-style key names.
- **Key Files**: `devices/container.py` (new)

### Component 3: `devices/phone.py` — `PhoneDevice` (NEW; device #2)
- **Purpose**: the Android body over adb/USB — the proof the interface holds against a different shape. `screenshot()` = `adb exec-out screencap -p` (raw PNG bytes via `subprocess`, binary-clean); `act()` maps verbs → `adb shell input` (tap / swipe / text / keyevent); `shell()` = `adb shell`. Advertises `PHONE_CAPS`: **1080×2400**, verbs `{click, double_click, scroll, drag, type, key}` (**no** `right_click`/`hover`), `keys={"Back":"KEYCODE_BACK","Home":"KEYCODE_HOME","Enter":"KEYCODE_ENTER",...}`, `has_shell=True`, `shell_flavor="android"`. `scroll`→swipe, `drag`→swipe-with-duration. Configurable `adb_path` (default `tools/platform-tools/adb.exe`) + optional `serial`.
- **Key Files**: `devices/phone.py` (new)

### Component 4: `brain/client.py` — device-aware vocabulary (MODIFY)
- **Purpose**: assemble the Brain's action set from the active device's `Capabilities` instead of a hardcoded superset. `decide(goal, observation, history, *, caps, ...)`: inject a **device preamble** (name, resolution, available verbs, named keys, shell flavor) into `SYSTEM_PROMPT`; build the JSON-schema action enum + the validated action set from `caps.verbs ∪ {wait, screenshot, done, fail} ∪ (shell if caps.has_shell)`. The tuned prose (symbol-naming, focus discipline, shell-vs-vision, wait-for-loading) stays. The Brain never sees a verb the body can't do.
- **Key Files**: `brain/client.py` (modify)

### Component 5: `agent/loop.py` — device-agnostic dispatch (MODIFY)
- **Purpose**: `run(goal, ..., device=None)` defaults to `ContainerDevice()`. Replace the module-level `screenshot()`/`hands()`/`exec_cmd()` with `device.screenshot()`/`device.act()`/`device.shell()`. Pass `device.caps` into `decide()`. The point-and-do dispatch (locate → act) is unchanged — only the transport call swaps. Defensively skip + log any verb the device doesn't support.
- **Key Files**: `agent/loop.py` (modify)

### Integration Architecture

| Component | Integrates With | Data Flow | Dependencies |
|---|---|---|---|
| `agent/loop.py` | `Device`, Brain, Eyes | screenshot bytes → describe → decide(caps) → locate → `device.act` | `devices/base` (Protocol), brain, eyes |
| `devices/base.py` | all devices, loop, Brain | defines the `Device` + `Capabilities` contract | none (pure interface) |
| `ContainerDevice` | Flask API `:8000` | `device.*` → HTTP → xdotool/scrot/bash | `devices/base`, running container |
| `PhoneDevice` | `adb` + physical phone | `device.*` → `adb` subprocess → screencap/input/shell | `devices/base`, adb, USB phone |
| `brain/client.py` | loop, `Capabilities` | goal+obs+hist+**caps** → JSON action (from `caps.verbs`) | `devices/base` (reads caps only) |
| `eyes/client.py` | loop | screenshot → describe/locate | **unchanged** (resolution-agnostic) |

### Technical Considerations

- **Byte-identical extraction risk**: `ContainerDevice` must reproduce today's HTTP calls exactly (endpoints, payload shapes, the 4-retry cold-connection handling in `loop._open`). Mitigation: `test_hands.py` + `test_shell.py` hit the endpoints directly and must stay green **unchanged**; a live container calc/shell run confirms the loop path. No behavior "improvements" during the extraction.
- **adb screenshot must be binary-clean**: `adb exec-out screencap -p` returns raw PNG on stdout. In **Python**, `subprocess.run([...], capture_output=True).stdout` is byte-clean (verified during Phase 0 via the pull method). Do NOT shell-pipe it through PowerShell (`>` re-encodes and corrupts) — `PhoneDevice` uses `subprocess` directly, so this is inherently avoided.
- **Capability differences are first-class**: the phone drops `right_click`/`hover`, adds Back/Home; `scroll`→swipe, `drag`→swipe. The Brain only receives verbs in `caps.verbs`, so it can't emit `right_click` on the phone. `key` maps through `caps.keys` (named key → `KEYCODE_*`); desktop chords like `ctrl+a` are absent from phone caps.
- **Text input**: `adb shell input text` handles ASCII (spaces need `%s`/escaping); **emoji/Unicode deferred** (ADBKeyboard) until a task needs it — out of scope for the first proof.
- **Phone keep-awake**: `adb shell svc power stayon usb` (stays awake while USB-connected), set at `PhoneDevice` init — avoids the screen sleeping mid-loop.
- **Device liveness**: `PhoneDevice` verifies on init that `adb devices` shows the serial as `device` (not `unauthorized`/absent), failing fast with a clear message.

### Solution Options & Evaluation

#### Solution Options

| # | Solution | Description |
|---|---|---|
| 1 | **Python `Device` Protocol + `Capabilities`** | Loop depends on an in-process Protocol; each device wraps its own transport (HTTP/adb/pyautogui). *Chosen.* |
| 2 | Uniform HTTP contract for every device | Every body runs a little server speaking `/screenshot`+`/action`+`/exec`; phone needs an adb-backed server, Windows a pyautogui server. |
| 3 | No abstraction — `if device_type == ...` in the loop | Branch on device kind inside `loop.py`; no new package. |
| 4 | Full plugin/registry framework | Entry-point discovery, dynamic device registration, config-driven. |
| 5 | ABC base class (inheritance) instead of Protocol | Devices subclass a `Device` ABC rather than satisfy a structural Protocol. |

#### Evaluation

| Solution | Pros | Cons |
|---|---|---|
| 1 Protocol + Capabilities | Clean DIP; transport stays private; smallest honest surface; Pythonic; easy 3rd device | Interface must be right — mitigated by validating with a 2nd device NOW |
| 2 Uniform HTTP | Network-uniform; language-agnostic | Forces a server per body (heavy for adb, a subprocess); needless daemon + port management |
| 3 No abstraction | Least code now | The exact coupling we're removing; `loop.py` grows a device switch; defeats the goal |
| 4 Plugin framework | Very extensible | Massive over-engineering for 2–3 known devices (YAGNI — the over-eng trap) |
| 5 ABC inheritance | Explicit contract | Heavier than a Protocol; forces a base class; no gain at this size |

#### Selected Approach
- **Chosen**: **Solution 1 — Python `Device` Protocol + `Capabilities` manifest.**
- **Rationale**: the minimal honest expression of dependency inversion — the loop depends on an abstraction, transport is each device's secret. It reuses Brain/Eyes/loop untouched, drops the phone in as a second implementation that *validates* the interface, and admits a third body (`WindowsDevice`) with no framework. HTTP-uniform (2) adds daemons the design doesn't need; no-abstraction (3) keeps the coupling we're removing; a plugin framework (4) is the over-engineering trap our own reasoning memory warns against; an ABC (5) is heavier than a Protocol for no gain at 2–3 devices.

### ADR Output
- **ADR File**: [ADR-002: Device Interface](../docs/adr/2026-07-15-device-interface.md)
- **Decision Summary**: BRYES's Screen+Hands+shell is abstracted into a swappable `Device` (a vision-controllable body: screenshot + act + optional shell) with a per-device `Capabilities` manifest; loop/Brain/Eyes stay device-agnostic, transport is device-private, and pure API/MCP channels are excluded — proven by adding an Android `PhoneDevice` over adb as device #2.

---

## **IMPLEMENTATION PHASES**

### Phase 0: Host prep & phone reachability — ✅ COMPLETE (during planning)
- [x] **Step 0.1**: Install adb platform-tools
  - **Action / Implementation**: downloaded Google `platform-tools-latest-windows.zip` → extracted to `tools/platform-tools/` (gitignored via `/tools/`).
  - **Result**: DONE — `adb v37.0.0` at `tools/platform-tools/adb.exe`.
- [x] **Step 0.2**: Connect + authorize the phone
  - **Action / Implementation**: enabled USB debugging on the Galaxy Note10 Lite, accepted the RSA prompt, `adb devices`.
  - **Result**: DONE — `RR8NB06SZEW` (`SM_N770F`, Android 13 / SDK 33) shows `device`.
- [x] **Step 0.3**: Verify core primitives
  - **Testing**: `adb shell echo`, `adb shell wm size`, screencap→pull.
  - **Result**: DONE — shell ✓, resolution **1080×2400**, screencap ✓ (26 KB PNG). (`input`/Hands proven live in Phase 3.)

### Phase 1: Extract the `Device` interface + `ContainerDevice`
- [ ] **Step 1.1**: `devices/base.py` — the contract
  - **Action**: define `Capabilities` (dataclass) + `Device` (Protocol) + `devices/__init__.py`.
  - **Implementation**: `Capabilities(name, width, height, verbs: set, has_shell, shell_flavor, keys: dict)`; `Device` methods `caps`, `screenshot()->bytes`, `act(dict)->None`, `shell(command, timeout=None, stdin=None)->dict`, `pointer()->tuple|None`.
  - **Testing**: `python -c "import devices"`; a Protocol conformance check.
  - **Success Criteria**: module imports; contract expresses all verbs the loop uses today.
- [ ] **Step 1.2**: `devices/container.py` — `ContainerDevice` (byte-identical)
  - **Action**: move today's HTTP calls behind the `Device` contract.
  - **Implementation**: wrap `GET /screenshot`, `POST /action`, `POST /exec`, `GET /pointer` with the **same** 4-retry `_open` logic; define `DESKTOP_CAPS` (8 pointer verbs incl. `right_click`/`hover`, `has_shell=True`, `shell_flavor="bash"`, X key names, 1280×800-class).
  - **Testing**: `test_hands.py` + `test_shell.py` pass **unchanged**.
  - **Success Criteria**: behavior identical to today; both tests green.
- [ ] **Step 1.3**: `agent/loop.py` — depend on `Device`
  - **Action**: `run(goal, ..., device=None)` defaults `ContainerDevice()`; replace `screenshot()/hands()/exec_cmd()` with `device.screenshot()/act()/shell()`; thread `device.caps` toward `decide()` (still static prompt until Phase 2); defensively skip+log unsupported verbs.
  - **Testing**: a live container run through the loop (`run("compute 12+34+56")` or a `uname -r` shell goal).
  - **Success Criteria**: container task completes end-to-end via the abstraction; no regression.
- [ ] **Step 1.4**: Regression gate
  - **Testing**: re-run `test_phase4.py` (loop smoke) + `test_hands.py` + `test_shell.py`.
  - **Success Criteria**: all green; the container path is byte-identical.

### Phase 2: Brain device-awareness (vocab from `caps`)
- [ ] **Step 2.1**: `brain/client.py` — assemble vocab from `caps`
  - **Action**: `decide(goal, observation, history, *, caps=None, ...)` — **`caps` defaults to the full/desktop vocabulary** so `brain/test_phase3.py` + any existing caller keeps working (back-compat, mirrors `run(device=None)`).
  - **Implementation**: build the JSON-schema `action` enum + `VALID_ACTIONS` from `caps.verbs ∪ {wait, screenshot, done, fail} ∪ (shell if caps.has_shell)`; inject a **device preamble** (name, WxH, available verbs, named keys, shell flavor) into `SYSTEM_PROMPT`; keep the tuned prose intact.
  - **Testing**: unit-check the assembled action set for `DESKTOP_CAPS` vs `PHONE_CAPS` (phone lacks `right_click`/`hover`).
  - **Success Criteria**: Brain only offered verbs the active device supports.
- [ ] **Step 2.2**: Container regression
  - **Testing**: a live container run (Brain sees `DESKTOP_CAPS`); `test_phase4.py` green.
  - **Success Criteria**: container task still clean end-to-end.

### Phase 3: `PhoneDevice` (device #2) + live proof
- [ ] **Step 3.1**: `devices/phone.py` — the Android body
  - **Action**: implement `Device` over adb.
  - **Implementation**: `screenshot()` = `subprocess` `adb -s <serial> exec-out screencap -p` (bytes); `act()` maps `click/double_click→input tap`, `scroll/drag→input swipe`, `type→input text`, `key→input keyevent` (via `caps.keys`); `shell()` = `adb shell`; `PHONE_CAPS` (1080×2400, verbs w/o `right_click`/`hover`, Back/Home/Enter keys, `shell_flavor="android"`); configurable `adb_path` (default `tools/platform-tools/adb.exe`, **resolved relative to the repo root** like `.env` in brain/eyes — not cwd) + optional `serial`; init sets `svc power stayon usb` + liveness check.
  - **Testing**: covered by 3.2.
  - **Success Criteria**: `PhoneDevice` satisfies the `Device` Protocol.
- [ ] **Step 3.2**: `devices/test_phone.py` — deterministic smoke
  - **Action**: model-free checks mirroring `test_hands.py`/`test_shell.py`.
  - **Implementation**: `screenshot()` returns non-empty PNG bytes; `shell("echo ...")` round-trips; a harmless `key` (e.g. a no-op keyevent) executes; liveness/`adb devices` guard.
  - **Success Criteria**: all checks green against the live phone.
- [ ] **Step 3.3**: Live proof — the loop drives the phone
  - **Action**: `run(goal, device=PhoneDevice())` on a simple, safe on-screen goal (e.g. from Home, open a known app such as **Settings**).
  - **Implementation**: the **unchanged** loop runs screencap→describe→decide→locate→`device.act` (tap); save a `capture-NN.png` deliverable.
  - **Success Criteria**: the agent performs a real action on the physical phone through the unchanged loop — **the interface is validated by device #2**.

### Phase 4: ADR-002 + docs
- [ ] **Step 4.1**: Finalize ADR-002
  - **Action**: the ADR file (created at planning, Step 11 tail) — verify it matches what was built; adjust if implementation revealed anything.
  - **Success Criteria**: ADR-002 accurate + linked to this plan.
- [ ] **Step 4.2**: Update docs
  - **Action**: `docs/architecture-overview.md` (Device abstraction + bodies table), `docs/agent-loop-flow.md` (device boundary), `docs/orientation-map.md` (ADR-002 + `devices/` entries), `docs/context-index.md` + `docs/backlog.md` (device interface done; phone body ready; WhatsApp task next).
  - **Success Criteria**: docs reflect the new architecture; orientation map indexes ADR-002. (`/map-orientation` + `/update-project-context` refresh at wrap-up.)

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

### Phase 0: Host prep & phone reachability — ✅ COMPLETE
- [x] **Step 0.1 / 0.2 / 0.3**: adb installed (`v37.0.0`, gitignored `tools/`), phone authorized (`RR8NB06SZEW`, Android 13, 1080×2400), primitives verified (shell ✓, screencap ✓ 26 KB PNG). `input` proven in Phase 3.

### Phase 1: Extract `Device` + `ContainerDevice`
- [x] **Step 1.1**: [devices/base.py]
  - **Implementation Log**: Created `devices/base.py` — `ALL_VERBS` (frozenset of the 8 pointer/keyboard verbs), `Capabilities` (frozen dataclass: name/width/height/verbs/has_shell/shell_flavor/keys), and the `@runtime_checkable Device` Protocol (`caps`, `screenshot()->bytes`, `act(dict)->None`, `shell(command,timeout,stdin)->dict`, `pointer()->tuple|None`). Created `devices/__init__.py` exporting `Device`/`Capabilities`/`ALL_VERBS`. Python 3.14 → PEP-604 unions used.
  - **Testing Log**: `python -c "import devices"` OK; a minimal `Dummy` body `isinstance(..., Device)` → **True** (runtime Protocol conformance); `Capabilities` sample constructs. All green.
  - **Result**: PASS — the contract expresses every verb the loop uses today; module imports cleanly.
- [x] **Step 1.2**: [devices/container.py — byte-identical]
  - **Implementation Log**: Created `devices/container.py` — `ContainerDevice` wrapping the exact former `screenshot()`/`hands()`/`exec_cmd()` transport (urllib to `localhost:8000`, same `_open` 4-retry, same `runlog.record("action"/"exec")` transcript records) + `pointer()` (GET /pointer). `DESKTOP_CAPS` = docker-desktop 1280×800 (from entrypoint `SCREEN_RESOLUTION=1280x800x24`), all 8 verbs, `has_shell=True`/`bash`, empty `keys` (xdotool takes X keysyms directly). Exported from `devices/__init__.py`.
  - **Testing Log**: `isinstance(ContainerDevice(), Device)` → **True**; caps + all 4 methods present. Container was already up → `test_hands.py` **5/5 PASS**, `test_shell.py` **6/6 PASS**, both unchanged (server untouched — only new `devices/` files added).
  - **Result**: PASS — behavior byte-identical; both regression tests green.
- [x] **Step 1.3**: [agent/loop.py — depend on Device]
  - **Implementation Log**: Removed the module-level `SCREEN`/`_open`/`screenshot`/`hands`/`exec_cmd` (now in `ContainerDevice`); added `from devices import ContainerDevice, ALL_VERBS`. `run(..., device=None)` defaults to `ContainerDevice()`. Dispatch now calls `device.screenshot()` / `device.act({...})` (all point/scroll/drag/type/key sites) / `device.shell(cmd, timeout=, stdin=)`. Added a defensive guard: a verb not in `device.caps.verbs` (or `shell` when `not caps.has_shell`) is skipped+logged, not errored. `decide()` call unchanged (caps threaded in Phase 2).
  - **Testing Log**: `import agent.loop` OK. Live run `run("...uname -r", max_steps=4)` → screenshot(container)→describe→decide→`device.shell`→**done in 2 steps**; history `ran shell 'uname -r' -> exit 0; out: 6.6.87.2-...WSL2`. The full loop path works through the abstraction.
  - **Result**: PASS — loop depends only on `Device`; container task completes end-to-end; no regression.
- [x] **Step 1.4**: [regression gate]
  - **Implementation Log**: Caught a real regression — `agent/test_phase4.py` imported the removed module-level `screenshot` helper. Fixed the caller: `from loop import run` + `from devices import ContainerDevice`, and the final capture uses `ContainerDevice().screenshot()` (the helper moved into the device). Mechanical consequence of the extraction, in scope.
  - **Testing Log**: `import agent.test_phase4` OK. Launched gnome-calculator in the container → **`test_phase4.py` PASS**: vision loop drove 7→+→8→= via `device.act` (point-and-do with real coordinates: `(48,323)`/`(249,468)`/`(114,322)`/`(316,443)`), display read **15**, done in 5 steps, exit 0. `test_hands.py` **5/5**, `test_shell.py` **6/6** (final confirmation).
  - **Result**: PASS — vision (point-and-do), shell, and loop-orchestration paths all work through the `Device` abstraction; container path byte-identical. **Phase 1 complete.**

### Phase 2: Brain device-awareness
- [x] **Step 2.1**: [brain/client.py — vocab from caps]
  - **Implementation Log**: Split the static `SYSTEM_PROMPT` into `_BASE_PROMPT` (tuned prose, kept verbatim) + `_JSON_SCHEMA` (with an `__ACTION_ENUM__` placeholder). Added `_actions_for(caps)` (verbs from `caps.verbs` + wait/screenshot + shell-if-has_shell + done/fail; `caps=None` → full desktop set), `_device_preamble(caps)` (ACTIVE BODY header: name, WxH, exact action list, shell flavor, named keys; empty for `caps=None`), and public `build_system_prompt(caps=None)`. `decide(..., caps=None, ...)` now builds `system_prompt`/`valid_actions` from caps (back-compat default). `caps` read **duck-typed** — no `devices` import, Brain stays decoupled. Wired the loop: `decide(caps=device.caps)` + `static["brain.SYSTEM_PROMPT"]=build_system_prompt(device.caps)`.
  - **Testing Log**: `_actions_for` → desktop **13** actions (incl. right_click/hover/shell), phone **11** (no right_click/hover); phone preamble lists exact set + Back/Home keys; `caps=None` prompt = original prose (back-compat). `brain/test_phase3.py` (calls `decide` without caps) → both scenarios correct (click '+', then 'done'). Loop imports clean.
  - **Result**: PASS — Brain vocabulary is device-shaped; the Brain is only offered verbs the active body supports.
- [x] **Step 2.2**: [container regression]
  - **Testing Log**: `test_phase4.py` with the device-aware Brain (loop passes `DESKTOP_CAPS`) → 7→+→8→= via `device.act`, display **15**, **done in 6 steps**, exit 0. The Brain even chose the `shell` verb (offered because `DESKTOP_CAPS.has_shell`) to open the calc — confirming shell stays available on the desktop body.
  - **Result**: PASS — container task clean end-to-end with the device-aware Brain; no regression. **Phase 2 complete.**

### Phase 3: PhoneDevice + live proof
- [x] **Step 3.1**: [devices/phone.py]
  - **Implementation Log**: `PhoneDevice` over adb: `screenshot()`=`adb exec-out screencap -p` (bytes via subprocess), `act()` maps click→`input tap`, double_click→two taps, scroll→`input swipe` (vertical, direction-aware), drag→`input swipe … 500`, type→`input text` (space→%s), key→`input keyevent` (via `_keycode` + `PHONE_KEYS`); `shell()`=`adb shell`. `PHONE_CAPS` (verbs w/o right_click/hover, Back/Home/Enter+ keys, android flavor) with width/height filled live from `wm size`. Init: auto-detect single serial, liveness `_assert_live`, `svc power stayon usb`. `adb_path` resolves from repo root. Exported from `devices/__init__.py`.
  - **Testing Log**: covered by 3.2.
  - **Result**: PASS — satisfies the Device Protocol; constructs against the live phone.
- [x] **Step 3.2**: [devices/test_phone.py — smoke]
  - **Implementation Log**: `devices/test_phone.py` — model-free checks mirroring test_hands/test_shell.
  - **Testing Log**: **5/5 green** on the live phone: connected android-phone 1080×2400 (shell=android); caps touchscreen-shaped (no right_click/hover; Back/Home present); screencap → valid PNG 1080×2400 (4.3 MB); `adb shell` echo round-trips; `act(key)` executes (KEYCODE_WAKEUP).
  - **Result**: PASS — the phone body's Device primitives all work.
- [x] **Step 3.3**: [live proof — loop drives the phone]
  - **Implementation Log**: `run("Open the Settings app", device=PhoneDevice(), max_steps=8)` — the **unchanged** loop against the physical phone.
  - **Testing Log**: The loop drove the phone end-to-end over adb: real `screencap` frames → describe → decide → `locate` → real actions (`scroll`/`click`/`key Home`), respecting phone caps (used scroll/click/key, never right_click/hover). **The Device interface is validated by device #2 with the loop unchanged.** The specific task hit step_limit (didn't reach Settings) — a **task-navigation** limitation, NOT an interface issue.
  - **Result**: PASS **for the interface goal** (real actions on the phone through the unchanged loop = ADR-002's success criterion). **Tech debt / out-of-scope**: phone *task* capability is limited by a missing change-feedback signal (loop feeds current-describe + actions-only history, no state-delta) — the deferred Phase-5 verify-and-recover, now concretely pinpointed. Separate thread. **Phase 3 complete.**

### Phase 4: ADR-002 + docs
- [x] **Step 4.1**: [finalize ADR-002]
  - **Implementation Log**: ADR-002 (`docs/adr/2026-07-15-device-interface.md`) was written at planning (Step 11 tail); verified it matches what was built (Protocol + Capabilities, ContainerDevice byte-identical, PhoneDevice adb, caps-driven Brain vocab, API/MCP excluded, orthogonal to ADR-001). No adjustment needed.
  - **Result**: PASS — ADR-002 accurate + linked to this plan.
- [x] **Step 4.2**: [update docs]
  - **Implementation Log**: Updated **architecture-overview.md** (new "Bodies — the Device abstraction" section + `devices/` in repo layout), **orientation-map.md** (ADR-002 entry), **agent-loop-flow.md** (new §7: Device abstraction + per-phase timing + Seam-B phone reconfirmation), **backlog.md** (Device + phone + timing in Recently-resolved; describe-latency tech debt with the measured ~19.5s; Phase-5 change-feedback primitive pinpointed; WhatsApp next-step notes the phone body), **context-index.md** (bodies quick-fact).
  - **Result**: PASS — docs reflect ADR-002; orientation map indexes it. (`/map-orientation` + `/update-project-context` verified at wrap-up.) **Phase 4 complete.**

---

## **QUALITY REVIEW**
*Filled by procedure Step 16 (delegated to `/analyze-code-quality` in embedded mode) after all execution phases are complete. **Static** review — answers "is the code clean?".*

- **Scope**: `devices/{base,container,phone,__init__,test_phone}.py`, `agent/loop.py`, `agent/test_phase4.py`, `brain/client.py`, `runlog.py` + docs (architecture-overview, agent-loop-flow, orientation-map, backlog, context-index) + ADR-002 + this plan. **Reconciliation**: git diff matches the Execution Log **except** the timing instrumentation (`runlog.note()` + loop per-phase timing) — a user-requested enhancement *outside* ADR-002's scope, surfaced explicitly and accepted.
- **Quality Standard**: none found (`**/quality-standard.md` absent) — freeform review against LLM best practices.
- **Findings**: 0 critical, 0 medium, **1 low** — `PhoneDevice` init calls `adb devices` twice (`_only_device` + `_assert_live`) when auto-detecting the serial (init-only redundancy). Known limitation (already Out-of-Scope): `PhoneDevice.type` doesn't escape device-shell-special chars / emoji (deferred to ADBKeyboard). Correctness gate: all 9 changed `.py` compile clean; test_hands 5/5, test_shell 6/6, test_phone 5/5, test_phase3 back-compat, test_phase4 vision=15, live container + phone runs.
- **Fixed**: N/A — shipped as-is (Alvi: "ship it"; the low finding left as Option A, init-only cost).

---

## **FINAL INTEGRATION TEST**
*Filled by procedure Step 17 after Quality Review is resolved. **Runtime** verification through the qa/ instrument — answers "does it actually work end-to-end?".*

- **Scope**: `devices/` package, `agent/loop.py`, `brain/client.py`, `runlog.py`.
- **qa/ Status**: **Missing** — BRYES has no `qa/` instrument (project convention: runtime verified via deterministic phase/smoke tests + live loop runs, not a qa/ playbook). FIT covered inline instead.
- **Playbooks Run**: N/A — no qa/ instrument.
- **R/I/A/O Results**: N/A (no qa/) — but runtime was verified end-to-end inline: `test_hands.py` 5/5, `test_shell.py` 6/6, `test_phone.py` 5/5 (live phone), `test_phase4.py` vision loop = 15 (container, device-aware Brain), live container shell run + live phone loop run (real actions over adb).
- **Findings**: **Runtime clean** — every smoke + live run green. The phone "open Settings" *task* hit step_limit (interface validated; task incompletion is the out-of-scope Phase-5 change-feedback gap, documented in backlog).
- **Fixed**: N/A.

---

## **POST-COMPLETION**
After all phases are executed, logged, and both **Quality Review** + **Final Integration Test** are filled, move this plan to `plans/completed/`:
`mkdir -p ./plans/completed && mv ./plans/[this-file].md ./plans/completed/[this-file].md`
