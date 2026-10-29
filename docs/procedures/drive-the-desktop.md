# Drive the Windows desktop with BRYES

Use this procedure when you are the agent deciding what to do and need to see or operate a
real Windows application. The [Windows Bridge](../../api/README-Bridge.md) exposes screenshots,
pointer input, keyboard input, and optional visual target location over loopback HTTP.
You observe, decide, act, and verify; the Bridge does not run a Brain or a task loop.

Prefer an application's own API or command interface when it can perform the requested task
reliably. Use visual driving when that channel is unavailable or when the visible interface
is what you need to verify. The channel ordering is recorded in
[ADR-001](../adr/2026-07-15-effector-hierarchy.md).

## 1. Establish scope and safety

This operates on the user's actual desktop, not an isolated sandbox. Before sending input:

- Identify the application and the changes the user authorized. Do not save, delete, publish,
  or close unrelated work as a side effect of driving.
- Prefer a target you launched. If the task concerns an already-open application, confirm its
  identity and select its exact window handle; never choose solely by a vague title match.
- Close or save unrelated work before a risky run. A dedicated Windows session is the stronger
  isolation boundary, but this procedure does not create one.
- Kill only a process you created and know is disposable. A launcher pid does not prove you
  own the resulting application: a single-instance editor can reuse the user's existing process.
- Do not fight the user for the mouse or keyboard. Stop when concurrent interaction makes the
  observed state unreliable.

The body checks focus and pointer bounds, but it does not prove process ownership, understand
which document is open, or judge whether a requested operation is safe. Its gates are defense
in depth, not permission to act. See [ADR-009](../adr/2026-10-21-host-body-and-gates.md).

## 2. Start or connect to the Bridge

Use Windows with Python and the project dependencies installed. Commands below run from the
BRYES clone directory:

```powershell
pip install -r requirements.txt
$env:BRYES_ALLOW_HOST = "1"
python api/bridge-windows.py
```

The server stays in that terminal at `http://127.0.0.1:8110`. Use another terminal or an HTTP
client for requests. If a Bridge is already running, check `/health` and `/windows` rather than
starting another process. Health only confirms the HTTP service answers, not that a target
is usable or its input gate is enabled.

`BRYES_ALLOW_HOST=1` must be set in the **server process's environment** for input. Screenshot
capture is not gated. `OPENROUTER_API_KEY` is needed only if you call `/locate`; reading images
yourself and sending input do not require model calls. The Bridge has **no shell endpoint**,
so `BRYES_ALLOW_HOST_SHELL` is not needed for this workflow.

The server has no authentication. Keep it on loopback and do not expose or tunnel it to an
untrusted network. POST operations require `application/json`; that rejects ordinary browser
form posts but is not authentication or protection against an untrusted local process. The
server serializes device operations, not whole workflows; use one desktop driver at a time.

## 3. Select a window and load its vocabulary

```text
GET /windows
GET /profiles?path=windows
GET /profiles?path=windows/unreal-editor
```

`/windows` returns a `windows` list. Each entry includes:

- `id`: a hexadecimal window handle, such as `0x1a`. Use the actual returned string as `window`
  on subsequent requests; do not invent a handle or reuse one from an old session.
- `title` and `foreground`: clues for identifying the correct window, not proof of ownership.
- `rect`: the window rectangle in absolute Windows screen coordinates.
- `frame.origin` and `frame.size`: the monitor origin and dimensions used for its screenshots.
- `image_rect`: the window rectangle expressed in that screenshot's coordinates.

Minimized and untitled windows are omitted. Restore a minimized application before selecting
it. A dialog or another editor window may need its own handle; refresh `/windows` whenever
the task changes windows or the selected one closes.

Profiles return `visual` and `operating` text. Read the relevant vocabulary before driving;
the app-specific profile includes inherited desktop guidance. The Bridge does not automatically
feed this text into `/locate` or make decisions from it.

## 4. Observe and map coordinates

All screenshot requests require `window=<id>` and return PNG bytes directly in the HTTP
response body (`Content-Type: image/png`), not a path or JSON image. Save or display the bytes
with an image-capable tool and inspect the result before choosing an action.

| Request | Use |
|---|---|
| `GET /screenshot?window=<id>` | Full-resolution image of the monitor holding the target |
| `GET /downscaleshot?window=<id>&scale=0.5` | Smaller whole-monitor overview; scale range `0.05` to `1`, default `0.5` |
| `GET /upscaleshot?window=<id>&x1=100&y1=200&x2=300&y2=400&scale=2` | Fresh capture, then crop and enlarge; scale range `1` to `4`, default `2` |
| `GET /pointer?window=<id>` | Pointer in absolute screen and image coordinates, with `inside_frame` and `inside_window` flags |

A screenshot does **not** bring the window to the foreground. It records what is visible on
that monitor, including other windows covering the target. Do not aim at a control you cannot
see. Each screenshot endpoint makes a fresh capture; an overview and a later crop are not
guaranteed to show the same moment.

Input coordinates use the **original monitor image**, whose top-left is `(0,0)`, not absolute
Windows screen coordinates. Crop bounds also use that original frame. Scaled responses carry:

```text
X-Bryes-Scale: scale factor
X-Bryes-Origin: crop x,y in the original frame (0,0 for a downscaled overview)
X-Bryes-Frame: original frame width,height

frame_x = origin_x + returned_x / scale
frame_y = origin_y + returned_y / scale
```

Use the response headers, not remembered scaling settings. For example, on a crop starting at
`(100,200)` enlarged by `2`, returned pixel `(40,60)` maps to frame pixel `(120,230)`.
If your image viewer resizes the returned image again, undo that additional resize before
applying the formula. Round the final frame coordinates to integer pixels for input.

The plain `/screenshot` response is already 1:1 and does not carry those mapping headers.
Do not add the monitor's Windows origin when sending `/act`: the body does that translation.
Re-observe after moving the target between monitors, resizing it, or changing display layout.

## 5. Send one action, then verify

`POST /act` takes JSON containing the selected `window`, a `type`, and its fields:

| Type | Fields | Effect |
|---|---|---|
| `click`, `double_click`, `right_click`, `hover` | `x`, `y` | Click or move at a frame pixel |
| `scroll` | `x`, `y`, `direction` (`up` or `down`) | Scroll at a frame pixel |
| `drag` | `x`, `y`, `x2`, `y2` | Press, move, and release between frame pixels |
| `type` | `text` | Type into the currently focused control; does not focus or clear it |
| `key` | `key` | Tap a key or chord, such as `enter`, `escape`, or `ctrl+a` |
| `key_hold` | `key`, `seconds` | Hold then release; duration is clamped to `0.1` through `5` seconds |

[api/bridge_client.py](../../api/bridge_client.py) wraps all of this in one line per step, and its
`--from <shot>` converts a crop's pixels for you. With plain HTTP, for example, with `$window` set to
an id returned by `/windows` and `$x`, `$y` measured from the image:

```powershell
$payload = @{ window = $window; type = "click"; x = $x; y = $y } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8110/act `
    -ContentType application/json -Body $payload
```

Before input, the body restores an out-of-frame pointer and attempts to foreground the target.
A menu owned by the target counts as its focus, so the next keystroke need not dismiss it.
Pointer actions are refused outside the target window's rectangle; both endpoints of a drag
must be inside it. These checks do not guarantee that a coordinate hits the intended control.

After each meaningful action, capture again and inspect the expected effect. `ok:true` means
the input call completed, not that the application accepted it or the task succeeded. For a
drag, verify the connection or object at its destination, not merely the pointer's position.
Do not repeatedly replay input after a timeout: first check whether it already took effect.

### Optional: locate a named target

`POST /locate` accepts `{window, instruction}` and returns `{x,y,instruction}`. It captures a
fresh frame and calls the Eyes' grounding model, but does not click. It requires the model API
key and currently has no crop or profile-context parameter. Treat the coordinate as a proposed
target and verify it against the image before acting, especially for small controls.

On the recorded Unreal run, a misplaced drag moved a node rather than connecting its pin,
without an execution error. Use enlarged crops for pins and other small targets, map back to
frame coordinates, and confirm the resulting wire visually. Enlargement helps inspection;
it does not recover detail absent from the original capture.

## 6. Handle refusals and finish deliberately

- **HTTP 400:** inspect the JSON description for a missing window, invalid crop or scale, or
  unsupported action. `/act` also checks whether the body supports the verb.
- **HTTP 415:** send POST bodies as `application/json`.
- **HTTP 409 from `/act`:** read the body refusal, such as a disabled host gate, focus failure,
  or out-of-window point. Recheck the window, frame, and current image before retrying.
- **HTTP 502 from `/locate`:** the model call failed. Inspect the cause or choose coordinates
  yourself from a screenshot; do not pretend a failed location produced a target.
- **Input completes but nothing changes:** check control focus and whether the target runs at
  a higher Windows integrity level than Python. Windows can refuse synthetic input across that
  boundary. Do not treat an unchanged screenshot as proof that retrying is safe.

Record what visibly changed and what was verified on disk, separately. A successful compile
does not prove an asset was saved, and closing a settings window does not establish persistence.
Save only when authorized, then verify through the application's state or the resulting file.
Stop only Bridge or application processes you started and own; leave shared processes running.

## Alternative: delegate a whole goal

Use these paths only when you want BRYES's own Brain to decide and run the loop, rather than
driving individual operations yourself:

- **Python:** construct `WindowsDevice(hwnd=<verified handle>)`, then pass it to
  `agent.loop.run(goal, device=device, ...)`. This keeps the exact handle you selected.
- **Task API:** start `python api/server.py` on port `8100` and submit a goal to `/tasks`.
  Its `window` parameter is a title substring, not a handle; use it only when the target is
  unambiguous. See the [Task API README](../../api/README.md) for submission and polling.

Both alternatives need `OPENROUTER_API_KEY` and `BRYES_ALLOW_HOST=1`. If you authorize shell
execution through those paths, also set `BRYES_ALLOW_HOST_SHELL=1` in their environment.
The same ownership, targeting, and verification rules still apply. Loop transcripts are kept
under `artifacts/runs/`; direct Bridge requests do not automatically create that loop transcript.

For model-free checks of the Bridge contract, run `python api/test_bridge.py`. This does not
drive a live desktop or prove an application's behavior.
