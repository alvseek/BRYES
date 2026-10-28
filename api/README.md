# api/ — BRYES Task-Invocation API (ADR-008)

Give BRYES a task over HTTP instead of editing and running a Python script. A thin
**host-side** wrapper over the native `run()` loop ([agent/loop.py](../agent/loop.py)) —
the coarse "hand off a whole goal" path where BRYES's own brain drives. Step 0 toward
the MCP / loop-as-a-service direction ([docs/modularity-target.mmd](../docs/modularity-target.mmd));
an MCP adapter wraps this API later.

Distinct from [screen/server/](../screen/server/) — that's the *container's body API*
(screenshot / action / exec); this is the *host-side task API*.

## Run

```
python api/server.py        # -> http://127.0.0.1:8100  (localhost only, no auth)
```

## Endpoints

- `POST /tasks {goal, device?, profile?, max_steps?}` -> `202 {task_id, status:"pending"}`
  - `device`: a body name (`android` / `linux`), or omit -> ADR-006 embodiment auto-select
  - `profile`: a profile path or list (e.g. `android/whatsapp`)
  - `409 {error:"busy", active_task_id}` if a task is already running (single-flight)
  - `400` if `goal` is missing / empty
- `GET /tasks/<task_id>` -> `200 {task_id, status, steps, result, error}` (or `404`)
  - `status`: `pending` -> `running` -> `done` | `failed`
  - `result` includes the run's CONFIRMED FINDINGS ledger (the task's banked conclusions)
- `GET /health` -> `200 {ok:true}`

## Design (ADR-008)

- **Async** — each task runs `run()` in a background daemon thread, so `POST` returns
  immediately and the caller polls `GET`. A whole task is minutes.
- **Single-flight** — one task at a time (BRYES drives one device per run); the
  `JobManager` enforces it with a lock (a 2nd submit -> `409`).
- **In-memory** job store — a running task's live device session dies with the process anyway.
- The `JobManager`'s `runner` is **injectable** (defaults to `run`), so the tests verify the
  lifecycle + routes **model-free** with a stub.

## Files

- `jobs.py` — `JobManager`, `Job`, `BusyError`
- `server.py` — Flask app factory (`create_app`) + the 3 routes
- `test_jobs.py` — model-free JobManager lifecycle test
- `test_server.py` — model-free Flask route test (`test_client` + stub runner)

## The other surface: `bridge.py`

The task API above hands over a whole goal and lets BRYES's brain drive. `bridge.py` is the
layer below it, for a caller that already knows what to do and only needs eyes and hands:
no goal, no loop, no decision. It runs on `http://127.0.0.1:8110`.

```
GET  /windows                            every targetable window: id, title, rect,
                                         image_rect (in the frame's own pixels), foreground
GET  /pointer?window=<id>                where the pointer is, in screen and image space, and
                                         whether it is inside the frame and inside the window
GET  /screenshot?window=<id>              PNG of the target's monitor, 1:1
GET  /downscaleshot?window=&scale=0.5     the frame scaled down (default 0.5, as the Eyes'
                                          own overview does)
GET  /upscaleshot?window=&x1=&y1=&x2=&y2=&scale=2   one crop, enlarged
POST /act      {window, type, x, y, ...}  one verb at the caller's pixels
POST /locate   {window, instruction}      one pixel from the Eyes (UI-TARS) on a fresh frame
GET  /profiles?path=windows/unreal-editor the vocabulary both sides read
```

- **Mapping rule for the two scaled shots:** `frame_px = origin + returned_px / scale`, with
  `X-Bryes-Scale`, `X-Bryes-Origin` and `X-Bryes-Frame` returned as headers on every image.
- **No auth, loopback only**, by [USER-NAME]'s call; the standing guard is that a body must be
  `application/json`, which keeps a cross-origin form post out.
- **One action at a time** — a lock, the same intent as the task API's single-flight.
- Every dependency (device factory, locator, window lister, frame) is injectable, so the whole
  surface is tested model-free in `test_bridge.py`.

Measured 2026-10-28 through this surface, with the caller outside BRYES: a `Print String` node
created by right-click and typed name, three execution wires landed in `BP_CombatBody_Enemy`,
and a clean compile, without saving.
