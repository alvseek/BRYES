# Drive the Windows desktop with BRYES

Use the [Windows Bridge](../../api/README-Bridge.md) when you need to see or operate a
Windows application. You observe, decide, act and verify; the Bridge supplies eyes and
hands, not a Brain. [Prefer the application's API or command interface](../adr/2026-07-15-effector-hierarchy.md) when it can do the
job reliably, unless the visible interface is what you need to test.

This procedure uses the optional [command-line client](../../api/README-Bridge-Client.md).
Direct HTTP requests work too. Those references contain the full endpoint and field details.
Run the commands below from the BRYES clone.

## 1. Connect safely

This is the user's real desktop, not a sandbox ([host safety rules](../adr/2026-10-21-host-body-and-gates.md)).
Act only within the authorized task.
Prefer an application you launched; otherwise verify the existing window and document
before input. Never save, close or delete unrelated work, kill a process you do not own,
or compete with the user for the mouse and keyboard. A launcher can reuse an existing
process, so launching it does not by itself prove ownership.

Check `GET http://127.0.0.1:8110/health` for an existing Bridge. If none is running, start
it in a separate terminal with the project dependencies installed:

```powershell
$env:BRYES_ALLOW_HOST = "1"
python api/bridge-windows.py
```

The input gate must be enabled in the **server's** environment. Capture needs no gate;
`/locate` alone needs `OPENROUTER_API_KEY`. Keep the unauthenticated server on trusted
loopback, use one driver at a time, and do not restart or stop a shared process without
authorization. Health proves only that HTTP answers, not that input works.

## 2. Select the target

```powershell
python api/bridge_client.py windows
python api/bridge_client.py profiles windows/unreal-editor
```

Read the relevant profile's operating and visual guidance. Choose the verified window's
returned `id`, then set it for subsequent commands:

```powershell
$env:BRIDGE_WINDOW = "<id from windows>"
```

Alternatively, use `--title` for a unique title substring (unset `BRIDGE_WINDOW` first,
because it takes precedence). Prefer the verified handle for a target you launched.
Refresh the window list when switching to a dialog or another window; never reuse a
handle from an old session. Profiles guide you, but are not automatically fed to `/locate`.

## 3. Observe

```powershell
python api/bridge_client.py shot overview --raise
```

Open the saved image before acting. It shows the target's **whole monitor**, including
other windows, not just the selected application. `--raise` focuses before capture and
requires the input gate; omit it to capture without focusing. Never aim through an
obscuring window or assume focus means the application is ready.

For small controls, take a fresh enlarged crop:

```powershell
python api/bridge_client.py crop detail 100 200 300 400 --scale 2
```

Crop bounds are original full-resolution monitor-frame pixels, not points from the
smaller overview. Each capture is a new moment. Enlargement helps inspection but cannot
recover missing detail.

## 4. Act, then verify

Measure points on the saved image and use `--from` so the server maps them back to the
original monitor frame:

```powershell
python api/bridge_client.py act --from overview --json '{"type":"click","x":100,"y":50}'
python api/bridge_client.py act --json '{"type":"type","text":"hello"}'
python api/bridge_client.py act --json '{"type":"key","key":"enter"}'
```

Use your measured points, not the example coordinates. Account for any extra resizing
by your image viewer. Without `--from` or JSON `mapping`, points must already be original
frame pixels. Never convert them yourself **and** attach mapping. Do not add the Windows
monitor origin; the server handles it. The server must be updated for mapping support
before using `--from`; an older server could act at the wrong coordinates.

Send actions through `act --json`, using the [server's action fields](../../api/README-Bridge.md#endpoints).
Typing neither focuses nor clears a control. Both drag endpoints must be inside the
target window; when using `--from`, measure both on the same saved image.

Batch only a short sequence whose intermediate results do not need inspection:

```powershell
python api/bridge_client.py act --json '{"actions":[{"type":"key","key":"enter"},{"type":"delay","miliseconds":1000},{"type":"type","text":"hello"}]}'
```

There is no automatic settling delay. Use an explicit `delay` action when needed, with
`miliseconds` spelled exactly so. A delay waits; it does not check readiness. A batch holds
one Bridge lock, including delays, but does not block human input or other applications.
One mapping applies to every pointer action in a batch, so all its points must come from
the same image. If an earlier action changes the layout, capture again instead of batching
the next pointer action. Keep the full request within the client's 60-second timeout.

After each meaningful action or batch, capture again and inspect the expected result.
`ok:true` means the call completed, not that the application accepted it. For a drag,
check the resulting wire or object, not just the pointer. Re-observe after any layout or
monitor change; mapping cannot detect stale images.

If you need model-assisted location, `locate "<target description>"` proposes frame
coordinates from a fresh capture. Check them visually before acting, especially for small
controls. Those points are already frame coordinates: do not attach a screenshot mapping.

## 5. Handle failure and finish

Read the JSON error before retrying. Invalid fields return 400, missing targets 404,
ambiguous titles or refused input 409, and non-JSON POST bodies 415. Other failures are
listed in the [Bridge reference](../../api/README-Bridge.md#endpoints).

A batch stops at its first execution failure: `completed` lists the finished prefix,
`failed_index` is zero-based, and later actions do not run. The failed action may have
partially executed; nothing is rolled back. A timeout does not cancel server execution.
In either case, observe the desktop before deciding what remains. Never replay the entire
request blindly. If input completes without visible effect, check control focus and
whether the target runs at a higher Windows integrity level than Python.

Report visible results separately from persistence. Compile success does not prove an
asset was saved, and closing settings does not prove they persisted. Save only when
authorized and verify the application state or resulting file. Leave shared processes
running; stop only processes you started and know you own.

## Alternative: let BRYES decide

For whole-goal delegation instead of direct driving, use the separate
[Task API](../../api/README.md) or pass `WindowsDevice(hwnd=<verified handle>)` to
`agent.loop.run()`. These run BRYES's own Brain and need the model key as well as the
host-input gate. The Task API's `window` is a title substring, not a handle.
Shell execution through those paths needs its separate `BRYES_ALLOW_HOST_SHELL` gate;
the Bridge itself has no shell endpoint. The same authorization and verification rules apply.
