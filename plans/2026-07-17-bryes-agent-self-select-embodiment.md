# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES
- **Date**: 2026-07-17
- **Agent**: claude-software-architect
- **Theme**: Agent self-selects its embodiment (which Device/body) + knowledge (which profiles) at task start — a Brain pick from `profiles/index.md`, before the perceive→act loop begins
- **Source Protocol**: `/high-wizard` — [Procedure](//@agent-memory/control-files/procedures/high-wizard.md)

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **OBJECTIVES**
Give BRYES agency over its own **embodiment**. At task start — *before* the perceive→act loop, text-only (there's no body to screenshot yet) — the Brain reads a catalog ([profiles/index.md](../profiles/index.md)) and picks **{ which device/body, which app-profiles }**, or picks **no body at all** for a pure-answer task. This replaces hand-passing `profile="android/whatsapp"` to `run()`. The mind chooses its body per task (ADR-002's "one mind, swappable bodies" made active), then runs the normal loop from a screen overview — or, when no body is needed, just answers.

### **Related Documents**
- [docs/adr/2026-07-15-device-interface.md](../docs/adr/2026-07-15-device-interface.md) — ADR-002, the `Device` abstraction this builds on (bodies + Capabilities)
- [profiles.py](../profiles.py) + [profiles/android/profile.md](../profiles/android/profile.md), [profiles/android/whatsapp/profile.md](../profiles/android/whatsapp/profile.md) — the profile (knowledge) system
- [docs/adr/2026-07-16-structured-output-standard.md](../docs/adr/2026-07-16-structured-output-standard.md) — ADR-005, structured-output mechanism the picker reuses
- [docs/standards/quality-standard.md](../docs/standards/quality-standard.md) — quality dimensions applied at review
- New ADR (this feature) — created in Phase 2 (section G)

### **SUCCESS CRITERIA**
- [ ] [profiles/index.md](../profiles/index.md) exists — hand-authored, fixed markdown format (`## <body>` sections; `` `<path>` — description `` items). A minimal `profiles/linux/profile.md` exists so the container body is representable.
- [ ] The Brain picks `{device, profiles}` **upfront** (before any screenshot) from the catalog via `structured_call` (ADR-005), returning `Embodiment(device: str|None, profiles: list[str], reason: str)`.
- [ ] `run()` with **no** `device`/`profile` args → picks, derives+instantiates the body, loads the (possibly multiple) profiles, runs the loop; with **explicit** args → forced, no pick.
- [ ] `load_profiles(list)` merges multiple profile inheritance chains, de-duplicating the shared OS base.
- [ ] `device=None` → **answer-only** path returns `{status: "answered", answer: ...}`, no loop.
- [ ] Constraints enforced: every chosen profile sits **under the chosen device** (one body/run); unknown device or unreachable body → **fail clearly** (no substitution).
- [ ] Tests: catalog validate, `load_profiles` multi+dedup, device mapping, picker (mockable), answer-only, override rules — all model-free/offline.
- [ ] Live validation: the WhatsApp task **self-selects** `android` + `android/whatsapp` on the phone and the loop runs (end-to-end *send* still gated on an unlocked phone — existing tech debt, not this plan).
- [ ] `docs/standards/quality-standard.md` dimensions met; ruff clean on new/changed files.
- [ ] ADR recorded; `docs/context-index.md` updated (full prose doc-sync of architecture-overview/loop-flow tracked as existing tech debt).

---

## **SCOPE**

### In Scope
- **`profiles/index.md`** — hand-authored catalog, fixed markdown format (bodies at `##`, profiles as `` `path` — desc `` items).
- **`profiles/linux/profile.md`** — minimal base so the container body is representable in the catalog.
- **`profiles.py`** — `load_profiles(list[str])` (merge multiple chains, dedup shared ancestors); a validator (each path sits under the chosen device + resolves on disk).
- **`brain/client.py`** — `select_profiles(goal, catalog) -> Embodiment` (the upfront pick, via `structured_call`, deepseek primary + gemini backup); `answer(goal) -> str` (the no-body path).
- **`agent/loop.py` `run()`** — upfront pick when `device`+`profile` both None; root→Device map + instantiate; `load_profiles`; the `device=None` answer-only branch; the override rules; fail-clearly on unknown/unreachable body.
- **Root→Device map**: `{ "android": PhoneDevice, "linux": ContainerDevice }`.
- **Tests** — offline/model-free for catalog, `load_profiles`, mapping, overrides, answer-only; picker with a mocked Brain.
- **ADR** (section G) + a `docs/context-index.md` entry.

### Out of Scope (deferred — same bucket as "prove one loop first")
- **`switch_profile`** (mid-run profile re-selection) and **mid-run device switching** — until one embodied loop lands.
- **Device-availability probing / fallback** — MVP fails clearly if the chosen body is unreachable.
- **`dumpsys` foreground auto-detection** — the Brain-pick replaces it.
- **`WindowsDevice`** — the `windows` root maps to nothing yet (clean error).
- **Auto-generating `index.md` from the tree** — hand-authored per decision C.
- **Baking the operating profile into the literal system-prompt string** — stays per-call `context=` (proven, unchanged).
- **WhatsApp reply-composition as an "answer"** — delivering a reply *through* WhatsApp is a normal embodied task (phone body), NOT the `device=None` path.
- **Full prose doc-sync** of `architecture-overview.md` / `agent-loop-flow.md` — tracked as existing tech debt; this plan updates the ADR + context-index only.

---

## **CONFIRMED DECISIONS**
*These decisions were collected during investigation — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A/B decisions made by the agent with reasoning, per [What to Surface](../procedures/wait-options.md#what-to-surface)). The reasons serve as the analysis record.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | Catalog source-of-truth | **Hand-authored** `profiles/index.md` | Alvi maintains it; only 2–3 profiles today. Validation is against the **filesystem** (does `profiles/<path>/profile.md` exist), not by parsing the catalog — so no parser rigor needed. (Auto-generation deferred.) |
| 2 | Catalog format | **Fixed markdown**: `## <body>` headers + `` - `<path>` — description `` items | Fed to the Brain — LLMs read markdown lists most reliably; YAML/JSON rigor unneeded since validation is filesystem-based. `##` = the device choice; nested items = profiles under it. |
| 3 | Pick return shape | **Explicit** `Embodiment(device: str\|None, profiles: list[str], reason: str)` — device chosen, NOT derived | Device is a first-class choice (Alvi: "choose which device it wants to execute"). Deriving device from a profile root breaks on *device+no-profile* and *no-device* cases. `profiles` is a list → multiple profiles under one body. `reason` aids transcript debugging. |
| 4 | Picker model + effort | Reuse `decide`'s stack — deepseek-v4-flash primary + gemini-2.5-flash-lite backup, `reasoning.effort="high"` | One-shot, load-bearing pick; consistent with ADR-005; cheap. |
| 5 | Override rule | Picker runs **only when both `device` and `profile` are None**. Explicit `profile` → load + derive/validate its device; explicit `device` → use it, no auto-pick | Keeps the test override clean (`run(goal, profile="android/whatsapp")` forces phone+profile, no pick) so the loop can be validated independently of the pick. No new flag. |
| 6 | Root→Device map + one-body enforcement | `{ "android": PhoneDevice, "linux": ContainerDevice }`; every chosen profile must sit under the chosen `device`; mixed-root or unknown device → **raise** | The ef253360 constraint in code: one body per run. `linux → ContainerDevice` (the container is an Ubuntu desktop), `android → PhoneDevice`. |
| 7 | Device + no profile | **Allowed** — the body runs with no app-manual (today's generic default) | A device is enough to act; the profile is optional knowledge. |
| 8 | No device (`device=None`) — answer-only | **BUILD now**: `run()` branches to `answer(goal) -> text`, returns `{status: "answered", answer}`, no loop | North-star-aligned (WhatsApp-assistant sometimes just answers); small (one Brain call + one branch); non-entangling (returns to caller — delivering a reply *through* an app is a normal embodied task). Validation: `device=None ⇒ profiles=[]`. Misclassification risk accepted (prompt guidance + `reason` + test override). |
| 9 | Unreachable chosen device | **Fail clearly** with the reason; **no substitution** — even if it's the only way to reach the goal | Alvi: don't silently fall back to another body. `PhoneDevice()` already raises descriptively on no/locked device; surface it as a clean run failure. |
| 10 | Eyes/Brain feeding | **Unchanged** — `prof_visual` into every `describe(context=)`, `prof_operating` into every `decide(context=)` (loaded once, stable for the run) | Proven plumbing; the pick only changes *which* profiles fill it. Not re-plumbed into the literal system-prompt string (unnecessary scope). |
| 11 | `profiles/linux/profile.md` | **Add** a minimal base | So the container body is representable at the catalog `##` level and pickable even with no app-profiles. |

---

## **SOLUTION**

### Architecture Overview

A new **selection stage** runs at the top of `run()`, *before* the perceive→act loop. When the caller forces nothing, the Brain reads the catalog and returns an `Embodiment` — a body + profiles, or no body (answer-only). The loop itself is **unchanged**; only its *entry* gains the pick. The pick is text-only (goal + catalog) because there is no body to screenshot yet.

```
run(goal, device=None, profile=None)
  ├─ both None → AUTO PICK: emb = select_profiles(goal, read_catalog())
  │      ├─ emb.device is None → return {"status":"answered", "answer": answer(goal), ...}   (NO loop)
  │      └─ else → root = emb.device; validate profiles ⊂ root; device = _ROOT_DEVICE[root]()  (may fail → clear error)
  ├─ profile given → paths = [profile]|list; root = _root_of(paths); device = device or _ROOT_DEVICE[root]()
  └─ device given, no profile → use that Device instance; no profile
  → prof = load_profiles(paths)   →   [EXISTING loop, unchanged: fed prof_visual / prof_operating]
```

### Component 1: The catalog (hand-authored)
- **Purpose**: The menu the Brain picks from — bodies at the `##` level, profiles beneath. Also makes the container body representable.
- **Key Files**: NEW [profiles/index.md](../profiles/index.md) (fixed markdown: `## <body>` + `` - `<path>` — desc `` items); NEW [profiles/linux/profile.md](../profiles/linux/profile.md) (minimal desktop base).

### Component 2: Profile loading — multi-path merge
- **Purpose**: Load and merge *several* profile chains into one `{visual, operating}`, de-duplicating the shared OS base.
- **Key Files**: [profiles.py](../profiles.py) — NEW `load_profiles(paths: list[str])`, `_iter_profile_files(path)`, `read_catalog()`, `profile_exists(path)`; refactor `load_profile(path)` → `load_profiles([path] if path else [])` (back-compat, single-path callers unaffected).
- **Core logic**: for each path, walk its segments yielding each existing `profile.md`; collect across all paths into an ordered, de-duplicated file list (OS base first, then apps in pick order); parse `Terms & Vocab` / `Visual` / `Operating` from each once; `_join` as today.

### Component 3: The picker + answerer (Brain)
- **Purpose**: The upfront embodiment pick, and the no-body answer.
- **Key Files**: [brain/client.py](../brain/client.py) — NEW `Embodiment` Pydantic model, `select_profiles(goal, catalog)`, `answer(goal)`; NEW `_PICK_PROMPT`.
- **`Embodiment`**: `device: str | None` (`"android"` | `"linux"` | `None`), `profiles: list[str]` (paths under the device; may be empty), `reason: str`. Elicited via `structured_call` (ADR-005, `response_format json_schema`, strict:false, our Pydantic validation), same deepseek-primary + gemini-backup fallback loop as `decide`, `reasoning.effort="high"`, `schema_name="embodiment"`.
- **`answer(goal)`**: reuses `structured_call` with a trivial `Answer(answer: str)` model (no *new* transport path, gets the model-fallback for free; strict:false ⇒ safe on reasoning models). Returns the plain answer string.

### Component 4: Orchestration (`run()`)
- **Purpose**: Turn the pick (or the overrides) into a concrete body + profiles, then run the existing loop — or answer.
- **Key Files**: [agent/loop.py](../agent/loop.py) — NEW `_ROOT_DEVICE = {"android": PhoneDevice, "linux": ContainerDevice}`, `_root_of(paths)` (shared first segment; raises on mixed), `_validate_under(root, paths)` (each path under `root` **and** `profile_exists`), `resolve_embodiment(goal, *, picker, read_catalog)` (PURE decision — no instantiation, injectable picker → unit-testable); `run()` selection stage + answer-only branch + override rules.
- **Fail-clearly**: unknown `root` → `RuntimeError`; body instantiation failure (e.g. `PhoneDevice()` on no/locked phone) → wrapped `RuntimeError("chose body '<root>' but it's unavailable: …")`. No substitution.
- **Transcript**: the pick runs before `runlog.start` (which needs `device.caps`); after start, log the chosen embodiment as a note. Answer-only runs return before `runlog.start` (no device) — no run transcript (minor, noted).

### Component 5: Tests (offline / model-free)
- **Purpose**: Prove every non-hardware piece without a phone or a live model.
- **Key Files**: [profiles.py](../profiles.py) tests (extend/create `test_profiles.py`); NEW `agent/test_run_selection.py` (or top-level) for `resolve_embodiment` + the answer-only branch with a mocked picker/answerer.

<!-- OPTIONAL SECTION A -->
### Integration Architecture

| Component | Integrates With | Data Flow | Dependencies |
|-----------|-----------------|-----------|--------------|
| `profiles/index.md` (catalog) | `select_profiles` | catalog text → Brain prompt | filesystem |
| `profiles.py` `load_profiles` | `run()` | `list[path]` → `{visual, operating}` | filesystem |
| `brain` `select_profiles` / `answer` | `run()` | `goal + catalog` → `Embodiment` / `goal` → text | `structured.py`, OpenRouter (ADR-005) |
| `run()` orchestration | `devices`, `profiles`, `brain` | `Embodiment` → body + profiles → loop (or answer) | all of the above; `_ROOT_DEVICE` map |
| existing loop | `devices`, `eyes`, `brain` | unchanged; consumes `prof_visual` / `prof_operating` | unchanged |

<!-- OPTIONAL SECTION B -->
### System Flow Diagrams

**Current State** (profile hand-passed):
```mermaid
sequenceDiagram
    participant Caller
    participant run as run()
    participant Loop
    Caller->>run: run(goal, profile="android/whatsapp")
    run->>run: load_profile(profile)
    run->>Loop: perceive→decide→act (fed prof_visual / prof_operating)
    Loop-->>Caller: {status:"done"/…}
```

**End Result** (Brain self-selects embodiment):
```mermaid
sequenceDiagram
    participant Caller
    participant run as run()
    participant Brain
    participant Dev as Device
    participant Loop
    Caller->>run: run(goal)   %% no device/profile forced
    run->>Brain: select_profiles(goal, catalog)
    Brain-->>run: Embodiment{device, profiles, reason}
    alt device is None (answer-only)
        run->>Brain: answer(goal)
        Brain-->>Caller: {status:"answered", answer}
    else device chosen
        run->>Dev: _ROOT_DEVICE[device]()   %% instantiate (unreachable → clear fail)
        run->>run: load_profiles(profiles)
        run->>Loop: perceive→decide→act (UNCHANGED)
        Loop-->>Caller: {status:"done"/…}
    end
```

<!-- OPTIONAL SECTION C -->
### Technical Considerations

- **One body per run (ef253360)**: all chosen profiles must share the top-level segment. `_root_of` raises on a mixed-root pick; `_validate_under` rejects a path not under the chosen device. Enforced in code, not left to the prompt.
- **Unreachable chosen body**: `PhoneDevice()` already raises a descriptive error on no/locked/unauthorized device; we wrap+surface it as a clean run failure and **do not** substitute another body (decision 9) — even if it's the only path to the goal.
- **Misclassification risk (answer-only vs act)**: the Brain could pick `device=None` for a task that needs on-screen action. Mitigations: `_PICK_PROMPT` says "only no-body if NO on-screen action is needed"; the `reason` field is logged; the test override forces a body. Accepted for MVP.
- **Catalog drift (hand-authored)**: a test asserts every `` `path` `` in `index.md` resolves to a real `profile.md` on disk, so a stale catalog fails loudly rather than silently offering a dead pick.
- **Extra pick latency/cost**: one additional Brain call per task (≈ a `decide`), only when nothing is forced. Acceptable; it replaces a human hand-passing the profile.
- **`answer()` via `structured_call`**: a 1-field `Answer(answer:str)`, strict:false — reuses the only transport + the model-fallback; no meaningful format constraint on the reasoning stream (consistent with ADR-005).

<!-- OPTIONAL SECTION F -->
### Solution Options & Evaluation

#### Solution Options

| # | Solution | Description |
|---|----------|-------------|
| 1 | Hand-passed profile (status quo) | A human passes `profile="android/whatsapp"` to `run()`. |
| 2 | `dumpsys` foreground auto-detect | An OS probe reads the foreground app and maps it to a profile. |
| 3 | **Brain-pick from a catalog** (CHOSEN) | The agent reads a catalog and chooses body + profiles from the goal, before the loop. |

#### Evaluation

| Solution | Pros | Cons |
|----------|------|------|
| Hand-passed | Simple, deterministic | No agency; a human must know the profile; doesn't choose the body |
| `dumpsys` detect | Deterministic OS truth | Phone-only; knows only the *current* app (no destination operating-knowledge upfront, when starting on a launcher); still doesn't *choose* a body |
| Brain-pick | Task-aware; chooses the **body** too; gives operating knowledge from step 1; cross-body uniform (no per-OS probe); matches ADR-002 "one mind, swappable bodies" | A model judgment (can misclassify); one extra call per task |

#### Selected Approach
- **Chosen**: Brain-pick from a catalog (`profiles/index.md`).
- **Rationale**: Only Brain-pick gives the agent agency over its **embodiment** (the goal, not the OS state, drives it), hands the Brain the destination app's operating manual from step 1 (which `dumpsys` cannot, since a run starts on a launcher), and works uniformly across bodies. The misclassification risk is mitigated (prompt + `reason` + test override); the one-call cost replaces a human decision.

<!-- OPTIONAL SECTION G -->
### ADR Output
- **ADR File**: [docs/adr/2026-07-17-embodiment-selection.md](../docs/adr/2026-07-17-embodiment-selection.md) — ADR-006 (created during this planning phase).
- **Decision Summary**: The agent self-selects its embodiment (which `Device` body) and knowledge (which profiles) at task start via a Brain pick from a hand-authored catalog — including a no-body answer-only mode — replacing the hand-passed profile; builds on ADR-002 (Device) and ADR-005 (structured output).

---

## **IMPLEMENTATION PHASES**

### Phase 1: Catalog + multi-profile loading (pure, offline)
*No Brain, no device — filesystem only. Testable without hardware.*

- [ ] **Step 1.1**: Create the catalog + linux base
  - **Action**: Author `profiles/linux/profile.md` (minimal desktop base) and `profiles/index.md` (the catalog).
  - **Implementation**: `linux/profile.md` mirrors `android/profile.md`'s section shape (Terms & Vocab / Visual / Operating) with true, minimal desktop content (windowed GUI; mouse+keyboard; `shell` available). `index.md` fixed format: intro line ("pick ONE body + zero-or-more profiles, or no body to answer directly"), then `## android — …` and `## linux — …` sections, each listing `` - `<path>` — <desc> `` for every existing `profile.md` under it.
  - **Testing**: eyeball; covered mechanically by Step 1.3's drift test.
  - **Success Criteria**: both files exist; every `` `path` `` in `index.md` has a matching `profiles/<path>/profile.md`.

- [ ] **Step 1.2**: `load_profiles(list)` + helpers in `profiles.py`
  - **Action**: Add multi-path loading, catalog read, existence check; refactor `load_profile` onto it.
  - **Implementation**: `_iter_profile_files(path)` yields each existing `profile.md` down a path; `load_profiles(paths)` collects an ordered, de-duplicated file list across all paths (base first) and joins `Terms/Visual/Operating` once each (reuse `_parse_sections` + `_join`); `read_catalog()` returns `index.md` text (or ""); `profile_exists(path)`; `load_profile(path) = load_profiles([path] if path else [])`.
  - **Testing**: `test_profiles.py`.
  - **Success Criteria**: single-path parity with old `load_profile`; multi-path merges with the shared base appearing once; ruff clean.

- [ ] **Step 1.3**: Tests for Phase 1
  - **Action**: Write `test_profiles.py` (model-free).
  - **Implementation**: assert `load_profiles(["android/whatsapp"]) == load_profile("android/whatsapp")`; `load_profiles(["android/whatsapp","android"])` includes the android base **once** (no duplicate `Terms`); `profile_exists` true/false cases; `read_catalog()` non-empty; **drift test** — every `` `path` `` parsed from `index.md` satisfies `profile_exists`.
  - **Testing**: run the file.
  - **Success Criteria**: all checks green.

### Phase 2: The picker + answerer (Brain)
- [ ] **Step 2.1**: `Embodiment` + `select_profiles` in `brain/client.py`
  - **Action**: Add the upfront pick.
  - **Implementation**: `Embodiment(device: str|None, profiles: list[str], reason: str)` with field descriptions (device = which body or null-for-answer; profiles must sit under the device). `_PICK_PROMPT` explains: choose ONE body + zero-or-more profiles from the catalog for the GOAL, before seeing any screen; choose `device=None` ONLY if no on-screen action is needed. `select_profiles(goal, catalog, *, model=None, timeout=60, retries=2)` calls `structured_call(Embodiment, …, reasoning={"effort":"high"}, schema_name="embodiment")` with the SAME attempt/backup escape as `decide` (last attempt → `BACKUP_MODEL`).
  - **Testing**: Step 2.3.
  - **Success Criteria**: returns a validated `Embodiment`; ruff clean.

- [ ] **Step 2.2**: `answer(goal)` in `brain/client.py`
  - **Action**: Add the no-body answerer.
  - **Implementation**: `Answer(answer: str)`; `answer(goal, *, model=None, timeout=60)` via `structured_call` (reasoning high, backup escape), returns `.answer`.
  - **Testing**: Step 2.3.
  - **Success Criteria**: returns a string; ruff clean.

- [ ] **Step 2.3**: Tests for the Brain layer (mocked transport)
  - **Action**: Offline tests with `structured_call` monkeypatched.
  - **Implementation**: patch `brain.client.structured_call` to return a canned `Embodiment` / `Answer`; assert `select_profiles`/`answer` parse + return correctly; assert the enum/prompt wiring doesn't error.
  - **Testing**: run.
  - **Success Criteria**: green, no network.

### Phase 3: Orchestration (`run()`)
- [ ] **Step 3.1**: Resolution helpers in `agent/loop.py`
  - **Action**: Add `_ROOT_DEVICE`, `_root_of`, `_validate_under`, `resolve_embodiment` (pure).
  - **Implementation**: `_ROOT_DEVICE = {"android": PhoneDevice, "linux": ContainerDevice}`; `_root_of(paths)` returns the shared segment-0 or raises on mixed/empty; `_validate_under(root, paths)` raises unless every path starts `root + "/"` (or == root) **and** `profile_exists`; `resolve_embodiment(goal, *, picker, read_catalog)` calls the injected picker → `{"mode":"answer","reason"}` when `device is None`, else validates + returns `{"mode":"loop","root","profiles","reason"}` (raises on unknown root).
  - **Testing**: Step 3.3.
  - **Success Criteria**: pure (no instantiation), unit-testable; ruff clean.

- [ ] **Step 3.2**: `run()` selection stage
  - **Action**: Wire selection + answer-only + overrides into `run()`.
  - **Implementation**: at the top of `run()`, branch: (both `device`&`profile` None) → `plan = resolve_embodiment(goal, picker=select_profiles, read_catalog=read_catalog)`; `answer` mode → `return {"status":"answered","answer":answer(goal),"reason":…}`; loop mode → instantiate `_ROOT_DEVICE[root]()` (wrap failure as clear `RuntimeError`), `profile_paths = plan["profiles"]`. Forced `profile` (str|list) → `_root_of` + `_validate_under` + instantiate if no device. Forced `device` only → use it, no profile. Then `prof = load_profiles(profile_paths)` (replaces `load_profile(profile)`); log the chosen embodiment as a `runlog.note` after `runlog.start`. Existing loop body untouched.
  - **Testing**: Step 3.3 + Phase 4 live.
  - **Success Criteria**: forced paths behave exactly as before for a single profile; auto path resolves + instantiates; answer-only returns without a loop; ruff clean.

- [ ] **Step 3.3**: Tests for orchestration (no hardware)
  - **Action**: `agent/test_run_selection.py`.
  - **Implementation**: `resolve_embodiment` with a mocked picker — `device=None` → answer mode; `android` + `["android/whatsapp"]` → loop mode with right root/paths; mixed-root pick → raises; unknown device → raises; `_root_of`/`_validate_under` direct cases. `run()` answer-only: monkeypatch `select_profiles`→`Embodiment(device=None,…)` and `answer`→canned → assert `{"status":"answered"}` and NO device/loop touched.
  - **Testing**: run.
  - **Success Criteria**: green, offline.

### Phase 4: Live validation + docs
- [ ] **Step 4.1**: Live self-selection
  - **Action**: Prove the pick end-to-end on real infra.
  - **Implementation**: (a) **answer-only smoke** — `run("what is the capital of France?")` → `{"status":"answered", answer contains "Paris"}`, no device. (b) **WhatsApp self-select** — with the phone connected+unlocked, `run("message Mas Vin on WhatsApp saying hi")` with NO `profile`/`device` arg → confirm from the transcript the Brain returned `device="android"`, `profiles=["android/whatsapp"]`, `PhoneDevice` instantiated, and the loop ran. (End-to-end *send* remains gated on the unlocked-phone / send-button tech debt — not this plan.)
  - **Testing**: observed live + transcript.
  - **Success Criteria**: answer-only returns the answer; WhatsApp run self-selects the phone+profile and enters the loop; an unplugged phone fails clearly.
- [ ] **Step 4.2**: Docs
  - **Action**: Update `docs/context-index.md` with the embodiment-selection mechanism + link ADR-006. (ADR-006 file authored during planning.)
  - **Implementation**: add a "Quick facts" line / index entry describing `run()` self-selecting body+profiles from `profiles/index.md` (and the answer-only mode); note full prose sync of architecture-overview/loop-flow stays on the existing doc-sync tech debt.
  - **Testing**: n/a (docs).
  - **Success Criteria**: context-index reflects the new startup behavior.

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

### Phase 1: Catalog + multi-profile loading
- [x] **Step 1.1**: Create the catalog + linux base
  - **Implementation Log**: Created [profiles/linux/profile.md](../profiles/linux/profile.md) (minimal desktop base — Terms & Vocab / Visual / Operating, matching `android/profile.md`'s shape: windowed GUI, focus, mouse+keyboard, shell available, X keysyms) and [profiles/index.md](../profiles/index.md) (fixed-format catalog: intro on how to pick, then `## android — …` and `## linux — …` sections listing `` - `<path>` — desc `` for `android`, `android/whatsapp`, `linux`).
  - **Testing Log**: Verified on disk — the 3 catalog paths (`android`, `android/whatsapp`, `linux`) each have a matching `profiles/<path>/profile.md`. Mechanical drift assertion added in Step 1.3.
  - **Success Criteria**: PASS — both files exist; every `` `path` `` in `index.md` resolves to a real `profile.md`.
  - **Tech Debts**: None.
  - **Result**: Catalog + linux base in place; the container body is now representable in the catalog.

- [x] **Step 1.2**: `load_profiles(list)` + helpers in `profiles.py`
  - **Implementation Log**: [profiles.py](../profiles.py): added `INDEX_FILE` const; `_iter_profile_files(path)` (yields each existing `profile.md` down a path); `load_profiles(paths)` (collects an ordered, de-duplicated file list across all paths — shared OS base once — then joins `Terms/Visual/Operating` via the same `_join`/UI-ELEMENTS-head as before); `read_catalog()`; `profile_exists(path)`. Refactored `load_profile(path)` → `load_profiles([path] if path else [])` (single-path output byte-identical to the old impl).
  - **Testing Log**: Smoke via `python -c`: single==multi parity True; UI-ELEMENTS + whatsapp content present; dedup (base once) True; `profile_exists` true/false correct; catalog non-empty. Formal test in Step 1.3.
  - **Success Criteria**: PASS — single-path parity with old `load_profile`; multi merges base once; ruff clean.
  - **Tech Debts**: None.
  - **Result**: Multi-profile loading + catalog/existence helpers in place; existing single-path callers (the loop's feeding) unaffected.

- [x] **Step 1.3**: Tests for Phase 1
  - **Implementation Log**: Created [test_profiles.py](../test_profiles.py) (model-free, project `check()`/PASS-FAIL style): single==multi parity; chain-merge content; **dedup** (adding an ancestor path is a no-op + base phrase count == 1); empty/None safe; `profile_exists` true/false; catalog non-empty + ≥3 entries; **drift guard** (every `` `path` `` parsed from `index.md` resolves via `profile_exists`).
  - **Testing Log**: `python test_profiles.py` → ALL PASS, exit 0 (16 checks). One initial FAIL was a bad assertion (a term legitimately appears in both the glossary and the Visual prose) → replaced with the stronger "adding an ancestor is a no-op" dedup proof. `ruff check profiles.py test_profiles.py` → All checks passed.
  - **Success Criteria**: PASS — all checks green, offline, ruff clean.
  - **Tech Debts**: None.
  - **Result**: Phase 1 fully proven without hardware or a model; the drift guard will catch a stale catalog.

### Phase 2: The picker + answerer (Brain)
- [x] **Step 2.1**: `Embodiment` + `select_profiles`
  - **Implementation Log**: [brain/client.py](../brain/client.py): added `Embodiment(device: str|None, profiles: list[str], reason: str)` (field descriptions steer the pick — device = body-or-null, profiles under the device); `_PICK_PROMPT` (choose ONE body or null, profiles under it, null only when NO on-screen action needed, never mix bodies); `select_profiles(goal, catalog, *, model, timeout, retries)` via the new `_structured_with_fallback` helper (`schema_name="embodiment"`, `reasoning.effort="high"`), records the choice to the transcript. **DRY**: factored `_structured_with_fallback` (primary attempts → last escapes to `BACKUP_MODEL`, error-body recording) shared by the picker + answerer; `decide()` left untouched (it has its own enum post-validation retry).
  - **Testing Log**: `brain/test_embodiment.py` (Step 2.3) — parse + schema_name + fallback-escape + exhaustion, all green.
  - **Success Criteria**: PASS — returns a validated `Embodiment`; ruff clean.
  - **Tech Debts**: None (the picker call is unexercised **live** until Step 4.1 — noted there).
  - **Result**: The upfront embodiment pick exists, reusing the ADR-005 structured mechanism + model-fallback.

- [x] **Step 2.2**: `answer(goal)`
  - **Implementation Log**: [brain/client.py](../brain/client.py): added `Answer(answer: str)`, `_ANSWER_PROMPT`, and `answer(goal, *, model, timeout, retries)` — the no-body path, via the same `_structured_with_fallback` (`schema_name="answer"`), returns the plain answer string. Reuses the only transport (no duplicate plain-text HTTP path) and gets the model-fallback for free; strict:false keeps it safe on reasoning models.
  - **Testing Log**: covered in Step 2.3 (`answer()` returns "Paris" from a canned `Answer`).
  - **Success Criteria**: PASS — returns a string; ruff clean.
  - **Tech Debts**: None.
  - **Result**: The answer-only path's Brain call exists.

- [x] **Step 2.3**: Tests for the Brain layer
  - **Implementation Log**: Created [brain/test_embodiment.py](../brain/test_embodiment.py) (model-free): monkeypatches `structured_call` + `_load_key` (and nulls `runlog`) — asserts `select_profiles` parses device/profiles + uses `schema_name="embodiment"`; `device=None` pick; `answer()` returns the string; the **fallback escape** (primary `StructuredError` → last attempt uses `BACKUP_MODEL`, tried primary first); total exhaustion → `RuntimeError`.
  - **Testing Log**: `python brain/test_embodiment.py` → ALL PASS, exit 0 (9 checks). `ruff check brain/client.py brain/test_embodiment.py` → All checks passed.
  - **Success Criteria**: PASS — green, offline, ruff clean.
  - **Tech Debts**: None.
  - **Result**: Picker + answerer proven without network; the fallback escape is verified deterministically.

### Phase 3: Orchestration (`run()`)
- [x] **Step 3.1**: Resolution helpers
  - **Implementation Log**: [agent/loop.py](../agent/loop.py): imports updated (`answer, select_profiles` from brain; `PhoneDevice` from devices; `load_profiles, profile_exists, read_catalog` from profiles). Added `_ROOT_DEVICE = {"android": PhoneDevice, "linux": ContainerDevice}`, `_make_device(root)` (instantiate + wrap failure as a clear `RuntimeError`, no substitution), `_root_of(paths)` (shared segment-0 or raise on mixed/empty), `_validate_under(root, paths)` (each path under root **and** `profile_exists`), and the PURE `resolve_embodiment(goal, *, picker, catalog_reader)` (injectable picker → answer/loop dict; raises on unknown body).
  - **Testing Log**: import OK; smoke — `_root_of` mixed raises, `_validate_under` bad path raises, `_ROOT_DEVICE` maps correctly. Formalized in Step 3.3.
  - **Success Criteria**: PASS — pure (no instantiation), unit-testable; ruff clean.
  - **Tech Debts**: None.
  - **Result**: The decision layer exists and is hardware-free.

- [x] **Step 3.2**: `run()` selection stage
  - **Implementation Log**: [agent/loop.py](../agent/loop.py) `run()`: moved the cp1252-safe stdout reconfigure to the TOP; added the selection stage — (both `device`&`profile` None) → `resolve_embodiment(picker=select_profiles, catalog_reader=read_catalog)`; `answer` mode → `answer(goal)` + `return {"status":"answered", "answer", "reason"}` (no loop); loop mode → `_make_device(root)` + `profile_paths`. Forced `profile` (str|list) → `_root_of` + `_validate_under` + `device or _make_device(root)`. Forced `device` only → use it. Then `prof = load_profiles(profile_paths)` (was `load_profile(profile)`). Logs `embodiment_note` via `runlog.note` after `runlog.start`. Loop body untouched.
  - **Testing Log**: Step 3.3 (answer-only run returns answered without a device; forced mixed/bogus profiles raise pre-hardware).
  - **Success Criteria**: PASS — single forced profile behaves as before; auto/answer/override branches correct; ruff clean.
  - **Tech Debts**: Answer-only runs return before `runlog.start`, so they have no run transcript (minor — noted in plan).
  - **Result**: `run()` now self-selects its embodiment (or answers), with clean test overrides.

- [x] **Step 3.3**: Tests for orchestration
  - **Implementation Log**: Created [agent/test_run_selection.py](../agent/test_run_selection.py) (model-free, injected fake picker / monkeypatched `select_profiles`,`answer`,`_make_device`): `resolve_embodiment` answer-mode, loop-mode, unknown-body raise, mixed-root raise, nonexistent-profile raise; `run()` answer-only → `{status:"answered"}` with `_make_device` proven NOT called; `run()` forced mixed / bogus profiles raise before any hardware.
  - **Testing Log**: `python agent/test_run_selection.py` → ALL PASS, exit 0 (8 checks). `ruff check agent/loop.py agent/test_run_selection.py` → All checks passed. Re-ran the model-free suite (profiles, embodiment, run_selection, type_into) → all PASS (no regressions).
  - **Success Criteria**: PASS — green, offline, ruff clean.
  - **Tech Debts**: None.
  - **Result**: Orchestration wiring proven without a phone/container/model; the full loop on a real body remains for Step 4.1 (live).

### Phase 4: Live validation + docs
- [~] **Step 4.1**: Live self-selection — *answer-only + pick PASS live; phone-loop BLOCKED on hardware*
  - **Implementation Log**: Ran two live validations (real models). Phone-loop deferred (needs the phone connected+unlocked).
  - **Testing Log**:
    - **(a) answer-only, live PASS** — `run("What is the capital of France?")` → the Brain picked `device=None` (*"a pure factual question… without any on-screen action"*), `answer()` returned **"Paris"**, `{"status":"answered"}`, no device instantiated.
    - **(b) WhatsApp self-selection, live PASS (pre-instantiation)** — `resolve_embodiment("message Mas Vin on WhatsApp…", picker=select_profiles, catalog_reader=read_catalog)` → `{"mode":"loop", "root":"android", "profiles":["android/whatsapp"], reason:"…best done on an Android phone with the WhatsApp profile"}`. The Brain self-selected the phone + profile correctly from the goal + catalog.
    - **(c) full phone-loop — RAN LIVE, self-selection PASS; send content contaminated**: with the phone unlocked (WhatsApp already foreground), `run("message Mas Vin on WhatsApp saying hi")` with NO args → **the Brain self-selected `device=android`, `profiles=["android/whatsapp"]`**, `PhoneDevice` instantiated, the loop drove real WhatsApp for 10 steps and **tapped the green Send button** (the profile's "send = TAP, not Enter" Operating knowledge held) → message **delivered** (✓✓, 17:21), `status: done`. **VERIFIED against the actual screen** (`artifacts/wa_verify.png`), NOT the Brain's self-report (c4f7a2e9): the sent message was **"Hi" + leftover stale draft** ("The BRYES agent has been able to use whatsapp from phone…") — NOT a clean "hi". **Root cause (CORRECTED — Alvi read the raw decide response; my first analysis was wrong):** the Brain's *thought* said "use clear_first" but its emitted action JSON **OMITTED `clear_first`** → no clear was ever requested → the stale draft stayed and got sent with "Hi". (My earlier claim that `clear_field`'s `NotImplementedError` caused it was wrong — clear was never even attempted. That gap is *latent* — it would bite IF `clear_first` were emitted — but it did NOT cause this.) This is one instance of a broader **decide-fidelity** issue found in the transcript: across 11 decide responses the Brain set `visual_focus` 8× but **`visual_expectation` 0×** — it reasons about verifying in its `thought` ("to verify the text appears") but never emits the field, so Phase-5 verify-and-recover is effectively dead in practice. Rough edges: several `VISUAL_FOCUS FAILED`, a Translator popup mid-run, one malformed-JSON decide (unescaped quotes → StructuredError → fallback recovered), one ~80s decide spike.
  - **Success Criteria**: PASS for this plan's objective — **embodiment self-selection validated live end-to-end** (answer-only + the WhatsApp pick + the real phone loop). The *clean send* is a separate concern and is NOT clean (see the finding below).
  - **Tech Debts** (surfaced by the live run — all SEPARATE from embodiment selection; decide/Phase-5 machinery):
    - **[NEW · decide-fidelity] The Brain omits optional fields it reasons about.** `visual_expectation` emitted **0/11** (Phase-5 verify is dead in practice); `clear_first` omitted when its thought intended it (the stale-send cause). Fix is a decide prompt/schema tuning problem (make the prediction/clear fields reliably emitted) — its own focused pass.
    - **[NEW · robustness] One decide returned malformed JSON** (unescaped quotes inside the `thought`) → StructuredError → fallback/retry recovered. Consider hardening.
    - **[LATENT] `PhoneDevice.clear_field` = NotImplementedError** — did NOT cause this run (clear was never requested), but would no-op a real `clear_first`. Android clear gesture (long-press → select-all → delete / ADBKeyboard) still needed for reliable message-replace.
    - Carried: `VISUAL_FOCUS FAILED` frequency on the phone; ~80s decide spike once.
  - **Result**: The north-star mechanism works — the agent self-selects its body + app knowledge from the goal and drives real WhatsApp to a delivered message. The plan's objective is met; the live run surfaced one real, honest defect (phone clear gesture) that's now first-priority follow-up.

- [x] **Step 4.2**: Docs
  - **Implementation Log**: [docs/context-index.md](../docs/context-index.md): split the Bodies line and added an **Embodiment selection ([ADR-006])** Quick-fact — `run(goal)` self-selects `{device, profiles}` from `profiles/index.md` or answers directly (`device=None`); root→body map; one body per run; explicit args override; `load_profiles` merges. ADR-006 authored during planning. Full prose sync of architecture-overview / agent-loop-flow stays on the existing doc-sync tech debt.
  - **Testing Log**: n/a (docs).
  - **Success Criteria**: PASS — context-index reflects the new startup behavior + links ADR-006.
  - **Tech Debts**: architecture-overview.md / agent-loop-flow.md prose not yet synced (existing doc-sync debt).
  - **Result**: The new startup behavior is documented + discoverable.

---

## **QUALITY REVIEW**
*Filled by procedure Step 16 (delegated to `/analyze-code-quality` in embedded mode) after all execution phases are complete. **Static** review — answers "is the code clean?".*

- **Scope**: `profiles.py`, `brain/client.py`, `agent/loop.py`, `test_profiles.py`, `brain/test_embodiment.py`, `agent/test_run_selection.py`, `profiles/index.md`, `profiles/linux/profile.md`, `docs/context-index.md`, `docs/adr/2026-07-17-embodiment-selection.md`. Reconciled vs `git status --short`: exact match; the only diff-not-in-scope file is this plan (the audit doc) — correctly excluded.
- **Quality Standard**: [docs/standards/quality-standard.md](../docs/standards/quality-standard.md) found — 9 dimensions applied. **Strong passes**: Dim 1 (error handling — `_structured_with_fallback` retries + escapes to backup + records error bodies; `_make_device` wraps failures as clear `RuntimeError`, no substitution; stdout reconfigured utf-8-safe FIRST); Dim 6 (no stray prints/TODOs/commented code; ruff clean); Dim 7 (snake_case, module-per-role, co-located model-free `test_*.py`); **Dim 9 ★** (picker + answerer use `response_format json_schema` + Pydantic validation via `structured.py`, strict:false, NO tool-calling — fully compliant). Dims 2/3 N/A (no UI). ruff clean on all Python in scope.
- **Findings**:

| # | Severity | File | Issue | Fix Options |
|---|----------|------|-------|-------------|
| 1 | Medium | `brain/client.py` `select_profiles` | The name undersells it — it picks the whole **embodiment** (device **and** profiles), not just profiles. Against this project's "names are load-bearing" convention it reads misleadingly. | A) Rename `select_profiles` → `select_embodiment` (updates brain/client.py, agent/loop.py import+call, brain/test_embodiment.py, + ADR-006 & context-index references) `✓✓`  B) Keep `select_profiles` |
| 2 | Low | `brain/client.py` | The OpenRouter headers dict `{"HTTP-Referer": …, "X-Title": …}` is duplicated in `decide` and `_structured_with_fallback`. | A) Extract a module constant `_OR_HEADERS` and use in both `✓✓`  B) Skip |
| 3 | Low | `agent/loop.py` | The root-segment idiom `str(p).strip("/").split("/")[0]` is repeated in `_root_of` and `_validate_under`. | A) Share a tiny `_first_seg(path)` helper `✓✓`  B) Skip |

- **Fixed**: All 3 approved (1→A, 2→A, 3→A).
  - **#1 (Medium)** — renamed `select_profiles` → **`select_embodiment`** across brain/client.py (def), agent/loop.py (import + `run()` call + `resolve_embodiment` picker), brain/test_embodiment.py, agent/test_run_selection.py, docs/context-index.md, docs/adr/2026-07-17-embodiment-selection.md. *(Alvi considered a `select_device` + `select_profiles` + composite split; we kept the single coupled call — device+profiles is one decision, splitting would reason about the app twice + double the upfront pick latency. Rename chosen.)* Plan body left with the historical name (the finding + this Fixed note record the rename).
  - **#2 (Low)** — extracted `_OR_HEADERS` module constant in brain/client.py; `decide` + `_structured_with_fallback` now share it.
  - **#3 (Low)** — added `_first_seg(path)` helper in agent/loop.py; `_root_of` + `_validate_under` share it.
  - **Verified**: ruff clean on all 6 Python files; the model-free suite (test_profiles 16 / test_embodiment 9 / test_run_selection 8 = 33 checks) all PASS; no `select_profiles` remains outside the (historical) plan.

---

## **FINAL INTEGRATION TEST**
*Filled by procedure Step 17 after Quality Review is resolved. **Runtime** verification through the qa/ instrument — answers "does it actually work end-to-end?".*

- **Scope**: `profiles.py`, `brain/client.py`, `agent/loop.py` (the runtime paths — selection, pick, answer, loop).
- **qa/ Status**: **None (by project convention).** BRYES has no `qa/` playbook instrument — its quality standard uses model-free `test_*.py` scripts + **live manual runs** for runtime verification (see quality-standard §7/§8). Not setting one up (out of scope).
- **Playbooks Run**: N/A — runtime verified via live runs (below).
- **R/I/A/O Results**: Live runs (real models + real phone):
  - **Answer-only** — `run("What is the capital of France?")` → Brain picked `device=None`, `answer()` → "Paris", `{status:"answered"}`, no loop. **PASS.**
  - **WhatsApp self-select loop** — `run("message Mas Vin on WhatsApp saying hi")` (no args) → self-selected `android`+`android/whatsapp`, `PhoneDevice`, 10-step loop, tapped Send, delivered. **Self-selection PASS** (verified against `artifacts/wa_verify.png`, not the Brain's report).
- **Findings**: **1 real defect surfaced by the live send** — `PhoneDevice.clear_field` is `NotImplementedError`, so `clear_first` silently no-ops and a stale compose draft is sent with the new text (the run sent "Hi" + leftover draft). This is a **pre-existing, explicitly out-of-scope** debt (this plan deferred phone `clear_first`), now **elevated to critical-path** by the live evidence. No defect in the embodiment-selection code itself.
- **Fixed**: N/A for this plan (the clear_field gesture is separate, out-of-scope follow-up work — logged as the elevated tech debt in Step 4.1). The embodiment-selection feature is runtime-verified clean.

---

## **POST-COMPLETION**
After all phases are executed, logged, and both **Quality Review** + **Final Integration Test** are filled, move this plan to `plans/completed/`:
`mkdir -p ./plans/completed && mv ./plans/[this-file].md ./plans/completed/[this-file].md`
