# ADR-008: Task-Invocation API — async HTTP task service over `run()`

**Date**: 2026-07-19

**Status**: Accepted

---

## Problem

Today the ONLY way to give BRYES a task is to write or edit a Python script that imports `run()` from [agent/loop.py](../../agent/loop.py) and calls it (or run a test file with a hardcoded goal). The only non-test entry point in the repo is the container's *body* API ([screen/server/app.py](../../screen/server/app.py)) — there is no *task* entry point: no CLI, no task API. That blocks the whole intended direction: letting another process, another AI agent (via a future MCP adapter), or a chat front-end hand BRYES a goal. We need a programmatic way to invoke a whole task. A task is also **long-running** (minutes, 12+ steps), which shapes the interface.

---

## Decision

**We decided to**: expose the existing `run(goal)` loop as an **async HTTP task service** — a thin host-side `api/` package — with an **API-first** posture (MCP as a later thin adapter).

The service is two endpoints over a Flask app bound to localhost: `POST /tasks {goal, device?, profile?, max_steps?}` starts a task and returns a `task_id` immediately; `GET /tasks/{task_id}` polls `{status, steps, result}`. Each task runs the unchanged native loop (`run()`) in a background **daemon thread**, so the multi-minute run never blocks the HTTP layer. A `JobManager` owns an in-memory job store and enforces **global single-flight** (one task at a time — BRYES drives one device per run — a second request returns `409`). The task `result` includes the loop's **CONFIRMED FINDINGS ledger**, so `GET` returns the task's banked conclusions, not just a transcript. This is the coarse "hand off a whole goal" path (native brain drives); it is step 0 of the loop-as-a-service target ([modularity-target.mmd](../modularity-target.mmd)).

**Why we chose this:**
- **Async matches a long task.** A whole task is minutes; a blocking call would time out clients and give no progress. `start -> poll` is non-blocking and robust.
- **Not throwaway.** The `start_task -> poll` skeleton is exactly what the later pluggable-external-brain seam (`start_task -> next(decision)`) extends — the foundation, not a detour.
- **API-first is the universal substrate.** HTTP is callable by curl, scripts, services, AND a thin MCP adapter; MCP can wrap an API but is idiomatically a thin layer over one. (MCP -> REST is only lossy if MCP-specific primitives like sampling/resources are used, which a task tool does not.)

---

## What to Build (Requirements)

**Core Requirements:**
- A host-side `api/` package (distinct from `screen/server/`, the container's *body* API): `api/jobs.py` (`JobManager` + `Job` + `BusyError`), `api/server.py` (Flask app), model-free tests.
- `POST /tasks {goal, device?, profile?, max_steps?}` -> `202 {task_id}` (or `409` when busy, `400` on missing goal); `GET /tasks/{task_id}` -> `200 {status, steps, result}` (or `404`); `GET /health`.
- Background daemon thread per task; global single-flight lock; in-memory job store; bind `127.0.0.1` only, no auth.
- Device/profile string params mapped to the loop's bodies (`_ROOT_DEVICE` keys `android`/`linux`), or omitted -> ADR-006 embodiment auto-select.
- Additive `run()` change: return the `findings` ledger in the `done`/`fail`/`step_limit` results.

**Success Criteria:**
- A task can be started and its result polled over HTTP without editing any Python.
- The API stays responsive (serves polls) while a multi-minute task runs.
- A second concurrent task is rejected with `409`.
- Lifecycle + routes are covered by model-free tests (stubbed runner — no live model/device).

---

## Alternatives Rejected

- **CLI wrapper** (`python -m bryes "goal"`): still a process invocation — blocking, no concurrent status, not callable by a running service or agent.
- **Synchronous HTTP** (`POST /run` blocks until done): simplest server, but a multi-minute blocking call causes client timeouts, gives no progress, and ties up the connection.
- **MCP-first** (native MCP server now): a multi-minute blocking tool fights the MCP interaction model, and HTTP is the more universal substrate an MCP adapter can wrap later.
- **Fine-grained body tools** (expose Eyes+Hands for an external brain to compose): more freedom but requires extracting the operating knowledge and re-owning orchestration externally; superseded near-term by the loop-as-a-service cut (the external brain supplies only `decide()`; the server serves it the system prompt).
- **FastAPI / stdlib `http.server`**: FastAPI's async is wasted on a synchronous workload (`run()` runs in a thread regardless) and costs 2 deps; stdlib `http.server` means hand-rolling routing/JSON/status boilerplate, a bad trade against Flask (already a project dep in the container).

---

**Full context**: [High Wizard plan](../../plans/2026-07-19-BRYES-task-invocation-api.md)

---

*This document serves as a SPECIFICATION that tells implementation agents WHAT to build. The implementation protocol (High Wizard/Quick Wizard) will figure out HOW to build it.*
