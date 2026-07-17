# ADR-006: Embodiment Selection — the Agent Chooses its Body + Knowledge at Task Start

**Date**: 2026-07-17

**Status**: Accepted

---

## Problem

BRYES can inhabit multiple bodies (ADR-002: `ContainerDevice`, `PhoneDevice`) and can be primed with per-app knowledge (the profile system: `profiles/<os>/…/profile.md` feeding the Eyes + Brain). But *which* body and *which* profiles were hand-wired: a human passed `device=`/`profile="android/whatsapp"` to `run()`. The agent had no agency over its own embodiment — it couldn't decide "this is a WhatsApp task, so I need the phone + the WhatsApp manual," nor "this is a pure question, I need no body at all." For a WhatsApp-assistant that helps whoever messages it, the agent must make that choice itself, from the goal, before it starts.

---

## Decision

**We decided to**: add an upfront **embodiment-selection stage** to `run()` — before the perceive→act loop, the Brain reads a catalog (`profiles/index.md`) and returns an `Embodiment { device, profiles, reason }`: which body to inhabit and which profile(s) to load, or **no body** (answer the goal directly). The mind chooses its body per task, then runs the unchanged loop from a screen overview — or, when no body is needed, just answers.

The pick is **text-only** (goal + catalog) because there is no body to screenshot yet. The chosen `device` string (`"android"` / `"linux"`) maps to a concrete `Device` class via a small `_ROOT_DEVICE` table; the chosen `profiles` (a list — multiple allowed) are merged and fed to the Eyes/Brain exactly as before. Every chosen profile must sit under the chosen body (**one body per run**). If nothing is picked-worthy, `device=None` routes to a one-call `answer(goal)` and returns — no loop. The pick reuses the ADR-005 structured-output mechanism (`response_format json_schema`, strict:false, our Pydantic validation, deepseek primary + gemini backup). Explicit `device=`/`profile=` args to `run()` **override** the pick (the test/manual path).

**Why we chose this:**
- Agency over embodiment — the *goal* drives the body choice (ADR-002's "one mind, swappable bodies" made active), not a human or an OS probe.
- It hands the Brain the destination app's **operating manual from step 1** — which a foreground-app detector (`dumpsys`) cannot, since a task starts on a launcher, not inside the target app.
- Cross-body uniform (no per-OS detection code), and it composes cleanly with the existing profile + Device layers.

---

## What to Build (Requirements)

**Core Requirements:**
- `profiles/index.md` — a hand-authored catalog, fixed markdown: `## <body>` sections (the device choice) with `` - `<path>` — description `` items beneath (the profiles). Plus a minimal `profiles/linux/profile.md` so the container body is representable.
- `profiles.py`: `load_profiles(paths: list[str])` merging several inheritance chains, de-duplicating the shared OS base; `read_catalog()`; `profile_exists(path)`; `load_profile` refactored onto `load_profiles` (single-path callers unaffected).
- `brain/client.py`: `Embodiment(device: str|None, profiles: list[str], reason: str)` + `select_embodiment(goal, catalog)` via `structured_call` (ADR-005, `reasoning.effort="high"`, deepseek+gemini fallback); `answer(goal) -> str` (no-body path) via a trivial `Answer(answer: str)`.
- `agent/loop.py` `run()`: a `_ROOT_DEVICE = {"android": PhoneDevice, "linux": ContainerDevice}` map; `resolve_embodiment` (pure, injectable picker — unit-testable); `_root_of` / `_validate_under` (one-body-per-run enforcement); the `device=None` answer-only branch; the `device`/`profile` override rules; fail-clearly (no substitution) when the chosen body is unknown or unreachable.
- Offline/model-free tests for catalog + `load_profiles` + resolution + answer-only; a catalog drift test.

**Success Criteria:**
- `run(goal)` with no args self-selects `{device, profiles}` and runs the loop on the chosen body — validated live on the WhatsApp task (Brain picks `android` + `android/whatsapp`, `PhoneDevice` instantiates, loop enters).
- `device=None` returns `{status: "answered", answer}` with no loop.
- A mixed-root pick, an unknown body, or an unreachable body each **fail clearly** with the reason — no silent fallback to another body.
- Explicit `device=`/`profile=` still force the embodiment (the test override), so the loop can be validated independently of the pick.

---

## Alternatives Rejected

- **Hand-passed profile (status quo)**: no agency; a human must know the profile and the body — the exact limitation being removed.
- **`dumpsys` foreground auto-detection**: phone-only, and it knows only the *current* app — so it cannot supply the destination app's operating knowledge upfront (a run starts on a launcher), and it doesn't *choose* a body at all.
- **Derive the body from the profile's top folder (no explicit `device`)**: breaks on the *body-with-no-profile* and *no-body (answer-only)* cases — the device must be a first-class field.
- **Auto-generate `index.md` from the tree**: unnecessary for 2–3 profiles; hand-authored is simpler and validation is against the filesystem anyway. (Deferred, not rejected forever.)
- **Bake the operating profile into the literal system-prompt string**: the per-call `context=` feeding is proven and already stable-for-the-run; re-plumbing is needless scope.

---

## Relationship to ADR-002 and ADR-005

Builds on both. [ADR-002](2026-07-15-device-interface.md) gives the swappable bodies (`Device` + `Capabilities`); ADR-006 lets the agent *choose* which body to inhabit and derives it from the pick via `_ROOT_DEVICE`. [ADR-005](2026-07-16-structured-output-standard.md) provides the mechanism the pick + the answerer use (`response_format json_schema`, our Pydantic validation, model fallback).

**Deferred (same bucket as "prove one loop first"):** mid-run profile re-selection (`switch_profile`) and mid-run device switching; device-availability probing/fallback; a `WindowsDevice`; the `device=None` path being used to *deliver* a reply through an app (that is a normal embodied task, not answer-only).

---

**Full context**: [High Wizard plan](../../plans/2026-07-17-bryes-agent-self-select-embodiment.md)
