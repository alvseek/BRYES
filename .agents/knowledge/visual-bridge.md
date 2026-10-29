# The visual bridge — primitives for a caller that is its own brain

How an agent outside BRYES drives this machine, and the three things the host body needed before
it could. Written after the first real run (2026-10-28) put a `Print String` node and three wires
into `BP_CombatBody_Enemy`.

## What the bridge is

`api/bridge-windows.py`, Flask on `http://127.0.0.1:8110`, no Brain and no goal: a caller that already
knows what to do asks for a window list, a picture, a point, or an action. Distinct from
`api/server.py` on `:8100`, which takes a goal and lets BRYES decide.

The filename is Windows-specific as of 2026-10-29; tests load it by file path because a hyphen
cannot appear in a normal Python import. Run it with `python api/bridge-windows.py`.
The separate service under `screen/` controls only its Docker Linux desktop on port 8000;
it is not in the Windows Bridge path. The calling agent owns decisions, while `/locate`
optionally calls the Eyes. Direct screenshots and input need no model API key.

The operator workflow is [drive-the-desktop.md](../../docs/procedures/drive-the-desktop.md),
rewritten around the Bridge on 2026-10-29. API reference lives in
[README-Bridge.md](../../api/README-Bridge.md), separately from the task API README.

| Route | Returns |
|---|---|
| `GET /windows` | every targetable window: `id` (handle), `title`, `rect` (screen), `image_rect` (frame), `frame{origin,size}`, `foreground` |
| `GET /pointer?window=` | pointer in screen and image space, `inside_frame`, `inside_window` |
| `GET /screenshot?window=` | the target's monitor, 1:1 |
| `GET /downscaleshot?window=&scale=0.5` | the frame scaled down (0.5 is the Eyes' own overview factor) |
| `GET /upscaleshot?window=&x1=&y1=&x2=&y2=&scale=2` | one crop, enlarged |
| `POST /act {window,type,...}` | one verb at the caller's pixels |
| `POST /locate {window,instruction}` | one pixel from the Eyes on a fresh frame |
| `GET /profiles?path=` | the merged vocabulary text both sides read |

**Mapping rule for the two scaled shots:** `frame_px = origin + returned_px / scale`, with
`X-Bryes-Scale`, `X-Bryes-Origin` and `X-Bryes-Frame` as headers. A PNG cannot carry its own
mapping, so the headers are the contract.

**Auth:** none, by Alvi's choice; loopback only. POST bodies must be `application/json`, which
rejects ordinary browser form posts but is not authentication or local-process isolation.
Input needs `BRYES_ALLOW_HOST=1` in the server process. There is no Bridge shell endpoint.
Actions serialize on a lock, not a workflow-wide reservation.

Screenshots do not raise the window; they capture what is visible on the selected monitor.
Each scaled request captures afresh. Only the scaled routes carry mapping headers, not the
plain screenshot route. A viewer may resize the returned image again; undo that resizing
before applying the Bridge mapping. Input success is not proof of application success.

## Finding the current implementation and memory

On 2026-10-29 the main checkout lacked the whole Bridge and its newer local memory because
the work was still on `sp4-sp6-visual-bridge`. Alvi recalled the scaled routes and the live
Unreal wiring correctly while the older main checkout's newest note still said no live run.
`git worktree list` exposed the missing branch. It was fast-forwarded into main at `ec44d49`,
pushed, and both clean, merged additional worktrees were removed; their branches were kept.
When a recalled feature is missing, inspect worktrees and branch history before concluding
it was never built. Central Munnin/Hermod reads do not contain these localized worktree files.

## The three body fixes this needed

1. **A menu the target owns counts as focus.** While a context menu is open the foreground window
   is an untitled `UnrealWindow` owned by the blueprint window, whose own owner is the main editor.
   Comparing handles for equality refused every action, and raising the editor dismissed the menu.
   `foreground_is_target` now walks the GW_OWNER chain.
2. **A background process can be allowed to raise a window.** `SetForegroundWindow` is refused to a
   process that does not hold focus; `AttachThreadInput` to the current foreground thread for the
   length of the call is the documented way round it, and it leaves nothing attached.
3. **The pointer can be outside the frame.** A pointer parked on another display makes the next
   press land on whatever is under it. Before every action the body reads the pointer and moves it
   to the target's centre when it is outside, logging the move.

## What driving Unreal by hand and eye costs

- **A pin is 10 to 14 px.** Press 17 px to its right and Unreal MOVES the node instead of wiring
  it, with no error. Measure the pin on a 6x crop, then confirm the wire appeared.
- **The context menu takes typing.** Right-click opens it with the search box already focused;
  typing filters; Enter creates the highlighted item. It only worked once fix 1 above landed.
- **A combo needs its centre.** Clicking the empty space left of a Details dropdown does nothing.
  The list opens under the field with its own search box.
- **Compile reads from the tooltip**: `Good to go`, then `Dirty, needs to be recompiled` after the
  next change. `Ctrl+Z` names what it undid in a toast, which is how an accidental move is caught.
- **Project Settings is its own window** with its own tab, and its header names the ini file the
  values live in. Nothing is written to disk by closing it.

## Where the vocabulary lives

`profiles/windows/profile.md` (base desktop) and `profiles/windows/unreal-editor/profile.md`,
listed in `profiles/index.md`. The catalog lists them only because `_make_device` refuses a host
run that names no window, so a bare goal cannot reach the real desktop.
