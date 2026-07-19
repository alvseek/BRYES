---
doc_type: 7q-readme
project: BRYES
title: BRYES — Project README
updated: 2026-07-19
---

# BRYES — Brain-Eyes Vision Computer-Use Agent

## Table of Contents

- [What Is This?](#what-is-this)
- [How Do I Set It Up?](#how-do-i-set-it-up)
- [How Do I Use It?](#how-do-i-use-it)
- [How Does It Work Inside?](#how-does-it-work-inside)
- [How Is It Deployed?](#how-is-it-deployed)
- [What Decisions Were Made?](#what-decisions-were-made)
- [What's Broken / Known Debts?](#whats-broken--known-debts)

---

## What Is This?

**BRYES = Brain-Eyes.** A **computer-use agent**: it screenshots a screen and acts on it —
clicking and typing through vision, or running a command **directly via a shell channel** when
the task suits the command line. One reasoning mind drives **swappable bodies**: a disposable
Ubuntu desktop in a container, or a **real Android phone over USB**. It rents its vision + reasoning
models from OpenRouter and was built phase-by-phase from [roadmap.md](roadmap.md).

Two rules from the roadmap shape everything: **rent everything until it hurts** (a local GPU is a
last resort), and **prove one real task end-to-end before generalizing**.

### Architecture

The whole system is coupled by **one orchestrator**: `run(goal)` in [agent/loop.py](agent/loop.py).
The modules never call each other — only the loop calls each of them, one at a time. This is the
**current** module-coupling picture (source of truth: [docs/modularity.mmd](docs/modularity.mmd); the
action→module detail is in [docs/loop-dispatch.mmd](docs/loop-dispatch.mmd)):

```
                 goal (task)
                     |
                     v
   +--------------------------------------------+
   |  ORCHESTRATION — agent/loop.py  run(goal)  |   the ONLY coupler
   |  embodiment select · findings ledger       |
   |  current-condition · verify routing        |
   |  repeat/failure guards                      |
   +--------------------------------------------+
        |               |                |
        | screenshot    | describe       | decide
        | act/shell     | locate/box     | (+select_embodiment
        v               v                v   /answer)
   +---------+     +-----------+     +-----------------+
   |  BODY   |     |   EYES    |     |     BRAIN       |
   | Device  |     | eyes/     |     | brain/client.py |
   | (ADR-2) |     | client.py |     | + structured.py |
   |  ┌────┐ |     | describe  |     | decide/select/  |
   | Container|    | locate    |     | answer          |
   | Phone   |     | box/diff  |     | (Pydantic-valid)|
   +---------+     +-----------+     +-----------------+
                        |    \            |
                        |     \  visual   |  operating
        KNOWLEDGE ──────+──────\ context  |  context
        profiles.py (app/OS manuals) + _BASE_PROMPT (operating know-how)
                        |                 |
                        v                 v
              +--------------------------------------+
              | OpenRouter — UI-TARS / qwen-VL /      |
              |             deepseek / gemini         |
              +--------------------------------------+
           runlog.py records every step (cross-cutting transcript)
```

The four pieces all talk **over HTTP or adb; none runs inside another**. Each has its own module
README with internals:

- **Screen + Hands** — the disposable Ubuntu desktop container (screenshots, `xdotool` input, a
  sandboxed `/exec` shell). See [screen/README.md](screen/README.md).
- **Eyes** — rented VLMs that *describe* / *locate* / *box* a frame. See [eyes/README.md](eyes/README.md).
- **Brain** — a rented reasoning model that turns state into the next action. See [brain/README.md](brain/README.md).
- **Loop** — the orchestrator that chains them. See [agent/README.md](agent/README.md).

The **body** is an abstraction, not a hard-wire: Screen + Hands + shell sit behind a swappable
`Device` interface ([ADR-002](docs/adr/2026-07-15-device-interface.md)) — `ContainerDevice` (the
desktop) and `PhoneDevice` (a real Android over adb) are two bodies; the loop, Eyes, and Brain are
body-agnostic. Full structural detail: [docs/architecture-overview.md](docs/architecture-overview.md).

### Tech Stack

- **Language**: Python 3 — developed on CPython 3.14 (host-side loop/Eyes/Brain — stdlib HTTP client + a few libs; no hard minimum is declared)
- **Host libs** ([requirements.txt](requirements.txt)): `pydantic` (structured-output guard),
  `Pillow` (screenshot decode / downscale / crop), `flask` (the host task API — [ADR-008](docs/adr/2026-07-19-task-invocation-api.md))
- **Screen container**: Docker Desktop (WSL2) — Xvfb + fluxbox + xdotool + scrot + a Flask control API + noVNC
- **Phone body**: `adb` over USB (bundled in [tools/platform-tools/](tools/platform-tools/))
- **Models** (rented, OpenRouter — one API key covers all): UI-TARS-1.5-7B (grounding),
  qwen3-vl-30b-a3b + qwen2.5-vl-72b (describe / box), deepseek-v4-flash (Brain, default) +
  gemini-2.5-flash-lite (backup)

---

## How Do I Set It Up?

### Prerequisites

- **Python 3** (`python --version`) — developed on CPython 3.14; the host runs the loop/Eyes/Brain
- **Docker Desktop** with the WSL2 backend (`docker --version`) — hosts the Screen container body
- **An OpenRouter API key** — get one at https://openrouter.ai/keys (covers both Eyes + Brain)
- *(Optional, for the phone body)* an Android phone with USB debugging on; `adb` is bundled in
  [tools/platform-tools/](tools/platform-tools/)

### Setup

1. Clone and install the host deps:
   ```sh
   git clone https://github.com/alvseek/BRYES.git
   cd BRYES
   pip install -r requirements.txt
   ```

2. Configure the API key:
   ```sh
   cp .env.example .env
   # Edit .env — paste your key after OPENROUTER_API_KEY=
   ```

3. Start the Screen (the default container body):
   ```sh
   cd screen
   docker compose up -d
   ```

4. Verify it works:
   ```sh
   curl http://localhost:8000/health
   # Expected: {"status":"ok","display":":99"}  (HTTP 200)
   # Live view of the desktop: open http://localhost:6080/vnc.html
   ```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | The one key for Eyes + Brain. Lives in the gitignored `.env`. **Never commit it.** | `sk-or-v1-...` |
| `SCREEN_RESOLUTION` | Screen container resolution override (in `screen/docker-compose.yml`). | `2560x1600x24` (default `1280x800x24`) |
| `CHROME_START_URL` | URL Chrome auto-boots to in the container. | `https://www.tokopedia.com` (default `google.com`) |

---

## How Do I Use It?

Two ways to give BRYES a task: the **HTTP task API** (callable from anything) or **`run(goal)` from
Python** (the entry point in [agent/loop.py](agent/loop.py)).

### Task API (HTTP) — [ADR-008](docs/adr/2026-07-19-task-invocation-api.md)

Start the host task API (localhost only), then POST a goal and poll for the result. The task runs
`run()` in a background thread, so `POST` returns immediately:

```sh
python api/server.py     # -> http://127.0.0.1:8100

# start a task (native brain drives; body auto-selected from the goal)
curl -s -X POST http://127.0.0.1:8100/tasks \
  -H 'Content-Type: application/json' \
  -d '{"goal":"what is the capital of France?"}'
# -> {"task_id":"5448ee...","status":"pending"}

curl -s http://127.0.0.1:8100/tasks/5448ee...
# -> {"status":"done","result":{"status":"answered","answer":"Paris",...}}
```

`POST /tasks {goal, device?, profile?, max_steps?}` -> `202 {task_id}` (or `409` if a task is already
running — single-flight; `400` on a bad `goal`/`device`/`max_steps`). `GET /tasks/<id>` ->
`{status, steps, result}`, where `result` carries the run's CONFIRMED FINDINGS. `GET /health` -> `{"ok":true}`.
See [api/README.md](api/README.md). An MCP adapter over this API is the next step.

### Python (`run()`)

```python
from agent.loop import run

# Auto-select the body + app profiles from the goal (ADR-006):
result = run("search Tokopedia for 'DDR5 5600 SODIMM' and screenshot the results")

# Or pin the body / profile explicitly (the test path):
result = run("message Mas Vin on WhatsApp", device="android", profile="android/whatsapp")

# A pure-knowledge goal answers directly, no loop, no device:
result = run("what is the capital of France?")   # -> {"status": "answered", "answer": "Paris"}
```

`run()` returns a dict with `status` (`done` / `fail` / `step_limit` / `answered`), `steps`,
`history`, and the **CONFIRMED FINDINGS** ledger. Every step's prompts, replies, and screenshots are
saved to a transcript under `artifacts/runs/` (via [runlog.py](runlog.py)).

### Key `run()` parameters

| Param | Purpose |
|-------|---------|
| `goal` | The task, in natural language. |
| `device` | `"linux"` → `ContainerDevice`, `"android"` → `PhoneDevice`. Omit → the Brain **self-selects** ([ADR-006](docs/adr/2026-07-17-embodiment-selection.md)). |
| `profile` | App/OS profile path (e.g. `"android/whatsapp"`) → supplies Eyes + Brain knowledge. Omit → auto-selected. |
| `max_steps` | Step budget before `step_limit` (default 12). |
| `brain_model` | Override the Brain model slug (default `deepseek/deepseek-v4-flash`). |

### Commands

| Command | Description |
|---------|-------------|
| `cd screen && docker compose up -d` | Start the Screen container body (API `:8000`, noVNC `:6080`) |
| `cd screen && docker compose up -d --build` | Rebuild after editing the Screen server (see debts — stale-image caveat) |
| `python screen/test_hands.py` | Model-free Hands regression test |
| `python screen/test_shell.py` | Model-free shell-channel (`/exec`) test |
| `python devices/test_type_into.py` | Model-free `type_into` device-capability test |
| `python agent/test_condition_ledger.py` | Model-free loop findings-ledger / condition test |
| `python api/server.py` | Start the host **task API** ([ADR-008](docs/adr/2026-07-19-task-invocation-api.md)) on `127.0.0.1:8100` |
| `python api/test_jobs.py` / `python api/test_server.py` | Model-free task-API tests (JobManager + routes) |
| `ruff check .` | Lint (config in [ruff.toml](ruff.toml)) |

---

## How Does It Work Inside?

### Core flow: one autonomous step

Each step of the loop dispatches exactly **one** Brain action; the modules it touches depend on
which action (full map: [docs/loop-dispatch.mmd](docs/loop-dispatch.mmd); temporal per-step data flow:
[docs/agent-loop-flow.md](docs/agent-loop-flow.md)).

1. **Pre-loop, once** ([agent/loop.py](agent/loop.py))
   - The Brain reads the profile catalog and **self-selects** a body + profiles, or answers a
     pure-knowledge goal directly with no loop ([ADR-006](docs/adr/2026-07-17-embodiment-selection.md)).

2. **Perceive** (`device.screenshot()` → `eyes.describe()`)
   - Screenshot the active body; the Eyes describe it (two-mode foveal — overview gist, or a
     72B-boxed crop when focused, [ADR-004](docs/adr/2026-07-16-foveal-describe-trim.md)). The describe is
     **skipped when the last action left the screen unchanged** (shell / screenshot / failed action).

3. **Decide** (`brain.decide()`)
   - The Brain is fed priority-ordered blocks — GOAL / CURRENT CONDITION / **CONFIRMED FINDINGS**
     (an append-only, trusted ledger it banks facts into) / HISTORY / PROFILES / TODO
     ([ADR-007](docs/adr/2026-07-18-brain-prompt-restructure.md)) — and returns one structured action,
     validated by our schema ([structured.py](structured.py), [ADR-005](docs/adr/2026-07-16-structured-output-standard.md)).

4. **Act** (`eyes.locate()` → `device.act()` / `device.shell()`)
   - Pointer actions (`click`/`scroll`/`drag`/`type_into`) are grounded to a pixel by the Eyes, then
     executed by the body. `type`/`key`/`shell` skip the Eyes entirely (the Brain routes to the
     most direct channel — shell over vision, [ADR-001](docs/adr/2026-07-15-effector-hierarchy.md)).

5. **Verify** (next `describe(..., visual_expectation)`)
   - The Brain predicts a checkable expectation; the next describe **reports that thing's actual
     state** (the Eyes perceive, the Brain judges — [ADR-003](docs/adr/2026-07-16-change-feedback-verify-and-recover.md)).

Loop until the Brain says `done`/`fail` or the step budget runs out.

### External Integrations

| Service | Purpose | Protocol | Notes |
|---------|---------|----------|-------|
| **OpenRouter** | Eyes (VLMs) + Brain (LLM) inference | REST/HTTPS | One API key; `decide` retries + escapes to the backup model |
| **Screen container** | The default desktop body (screenshot / input / shell) | HTTP `:8000` | Local Docker; noVNC live view on `:6080` |
| **Android phone** | The real-phone body | `adb` over USB | `screencap` / `input` / `adb shell`; `tools/platform-tools/adb.exe` |

---

## How Is It Deployed?

**BRYES is a local research prototype — it is not deployed to any server.** It runs on the developer
host (Windows + Docker Desktop / WSL2):

- The **loop, Eyes, and Brain** run as a host-side Python process.
- The **Screen** is a disposable **local** Docker container (rebuilt on demand; holds no secrets —
  the API key stays on the host).
- The **phone body** is a physically-attached Android device over USB.

There is **no CI/CD, no cloud infrastructure, and no hosted endpoint** yet. Self-hosting a local
model (roadmap Phase 6) is deferred and only pursued "if forced." The host **task API**
([ADR-008](docs/adr/2026-07-19-task-invocation-api.md)) makes BRYES callable over HTTP, but binds
`127.0.0.1` only (Werkzeug dev server, no auth) — a network-reachable deployment (token auth + a real
WSGI server, or an MCP adapter) is the next step.

---

## What Decisions Were Made?

Full ADRs live in [docs/adr/](docs/adr/). In order:

| ADR | Decision |
|-----|----------|
| [ADR-001](docs/adr/2026-07-15-effector-hierarchy.md) | **Effector hierarchy** — the Brain routes each intent to the highest-available channel (Tier 1 API/MCP · Tier 2 shell · Tier 3 vision-fallback). Vision is one tool, not the only one. |
| [ADR-002](docs/adr/2026-07-15-device-interface.md) | **Device abstraction** — Screen+Hands+shell behind a swappable *vision-controllable body* with a `Capabilities` manifest. Proven by adding a real phone as body #2. |
| [ADR-003](docs/adr/2026-07-16-change-feedback-verify-and-recover.md) | **Verify-and-recover** — the Eyes *report* an action's effect, the Brain *judges* it (a VLM verdict proved noisy; a screen-wide pixel diff can't see small changes). |
| [ADR-004](docs/adr/2026-07-16-foveal-describe-trim.md) | **Two-mode foveal describe** — cut describe latency 5–16s → ~2s by attacking output length (overview gist / boxed-crop trim). Amendment 1 swapped the crop describer to a 30B MoE to fix a numeric-misread. |
| [ADR-005](docs/adr/2026-07-16-structured-output-standard.md) | **Structured output** — formats enforced by our Pydantic schema + forced tool-calling, never trusted to the AI. deepseek-v4-flash primary + gemini-2.5-flash-lite backup. |
| [ADR-006](docs/adr/2026-07-17-embodiment-selection.md) | **Embodiment selection** — the agent self-selects its body + profiles from a catalog before the loop, or answers a knowledge goal directly. |
| [ADR-007](docs/adr/2026-07-18-brain-prompt-restructure.md) | **Brain-prompt restructure** — priority-ordered blocks + an append-only, trusted CONFIRMED FINDINGS ledger, fixing a re-read/re-doubt non-convergence. |
| [ADR-008](docs/adr/2026-07-19-task-invocation-api.md) | **Task-invocation API** — expose `run()` as an async HTTP task service (`POST /tasks` → poll `GET /tasks/{id}`), single-flight, localhost. API-first; an MCP adapter over it is the next step. |

---

## What's Broken / Known Debts?

The living, finer-grained list is [docs/backlog.md](docs/backlog.md). Highlights:

### High Priority

- **Model-fallback unexercised live**: the `deepseek → gemini` last-attempt escape is wired +
  probe-verified (3/3) but has never actually *fired* in a run.
  *Why*: deepseek has carried every live task with zero failures; a forced-primary-failure shakeout is owed.

### Medium Priority

- **`decide` (the Brain) is now the dominant per-step latency** (~3–12s under high reasoning effort).
  *Why*: describe was solved (ADR-004, 5–16s → ~2s), moving the bottleneck onto the Brain. A box cache
  (~1.5s/step on stable focus) and a lighter `decide` config are the next levers.
- **WhatsApp on the real phone is unproven end-to-end**: the app-profile system + send-button flow
  exist but a locked phone / lock-screen blocks the run; `PhoneDevice.clear_field` is `NotImplementedError`.
  *Why*: the agent can't pass a lock screen, and the Android clear idiom is deferred.
- **Prose doc-sync lag**: `docs/architecture-overview.md` + `docs/agent-loop-flow.md` still use the old
  `focus`/`expect` names (renamed to `visual_focus`/`visual_expectation`), and some describe the 8B
  describer (now the 30B MoE).
  *Why*: index/backlog were synced first; the prose docs were deferred.

### Low Priority

- **Container image can go stale**: `docker compose up -d` reuses the existing image — edit the Screen
  server and you must `--build`, or the running container lags the on-disk code.
- **Broader ruff pass deferred**: new files are clean, but a handful of pre-existing issues remain.
- **Infinite-scroll has no stop-condition**: a "capture all of page 1" task on an infinite-scroll site
  needs an explicit bound (item count / target / N screenshots).
- **Task API — loop-task path not yet live-verified**: the live smoke exercised the *answer-only* path;
  a full device task over the API (returning `history` + the findings ledger) is covered model-free but
  not yet run live. The port (`8100`) is also hardcoded, not env-configurable.

### Known Limitations

- **Effector Tier 1 (API/MCP) is unbuilt** — only Tier 2 (shell) + Tier 3 (vision) exist.
- **The Brain is text-only** — it cannot see; it reasons over the Eyes' `describe` text (a lossy seam).
- **Validated on few tasks** — mostly browser search + a calculator; not yet the full calc suite or
  broad real-world coverage.
