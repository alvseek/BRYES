# Drive the desktop with BRYES

How another agent or a person drives a real Windows application through BRYES's host body.
Everything here was run on 2026-10-21; the numbers are measured, not estimated.

## Read this first: is vision the right effector?

[ADR-001](adr/2026-07-15-effector-hierarchy.md) puts channels in order: **API, then shell, then
vision**. Unreal Editor ships a Python plugin and a Remote Control API; an application that
publishes one should be driven through it. This body exists for the case where no channel exists,
or where the screen is the thing you must trust. Do not reach for pixels to do what an API does
faster and exactly.

---

## Preconditions

- Windows, with the repository's dependencies installed (`pip install -r requirements.txt`).
- `OPENROUTER_API_KEY` in `.env` (the Eyes and the Brain both need it).
- `BRYES_ALLOW_HOST=1` in the environment. Without it the body captures but refuses to act, and
  `device="windows"` refuses before a body is even built.
- `BRYES_ALLOW_HOST_SHELL=1` too, if the run may use the `shell` action.

```powershell
$env:BRYES_ALLOW_HOST = "1"
$env:BRYES_ALLOW_HOST_SHELL = "1"    # only if shell is wanted
```

## Entry point A: Python, targeting a window handle (recommended)

A **handle** pins the run to one window. That matters: a title substring matched the largest
matching window on 2026-10-21 and drove the wrong document.

```python
from devices.windows import WindowsDevice, find_window
from agent.loop import run

found = find_window("Unreal Editor")        # (hwnd, title, rect), or None
if not found:
    raise SystemExit("open the editor first, or launch it below")
hwnd, title, rect = found

device = WindowsDevice(hwnd=hwnd)           # pins focus, clicks and the rect guard to this handle
result = run("open the World Settings panel and report what it shows",
             device=device, max_steps=5, verbose=True, tag="unreal")
print(result["status"], result.get("steps"))
```

To launch the application yourself and drive only what you launched:

```python
import subprocess, sys, time
from devices.windows import WindowsDevice, top_window_of_pid
from agent.loop import run

proc = subprocess.Popen([r"<path-to-UnrealEditor.exe>", r"<path-to-your.uproject>"])
hwnd = None
for _ in range(120):                        # editors take a while to show a window
    found = top_window_of_pid(proc.pid)
    if found:
        hwnd = found[0]
        break
    time.sleep(0.5)
run("...", device=WindowsDevice(hwnd=hwnd), max_steps=5)
proc.terminate()                            # only a process you started
```

Note that a launcher may own a different pid than the editor it spawns. If the window does not
appear under the launcher's pid, launch the editor directly, or target the open window's handle.

## Entry point B: the task API

```powershell
python api/server.py        # http://127.0.0.1:8100, localhost only, no auth

curl -X POST http://127.0.0.1:8100/tasks -H "Content-Type: application/json" -d '{
  "goal": "open the World Settings panel and report what it shows",
  "device": "windows",
  "window": "Unreal Editor",
  "max_steps": 5
}'
```

The API takes a **title**, not a handle, because JSON has no hwnd. It is fine when exactly one
window can match, and wrong when two can. For anything destructive, use entry point A.

## The three harness rules

They are in the code, not just good advice, and each one exists because it was violated.

1. **Target a window you started, by handle.** `WindowsDevice(hwnd=...)` or `top_window_of_pid`.
   A title substring once selected the user's own Notepad and typed into it.
2. **Kill only a process you created.** `proc.terminate()` on your own `Popen`, never a pid you
   found. That same accident closed a shared single-instance editor with someone's work in it.
3. **Act only inside the target's rect.** The body refuses any pointer action outside the target
   window's rectangle: `refusing to act at (x,y): outside the target window`. The step fails; it
   does not click beside it.

## What a run costs

Measured on this machine, whole-desktop frames of 2560×1440:

| Phase | Time |
|---|---|
| screenshot | 0.2–0.4 s |
| describe (the Eyes) | 3.7 s typical, 10.6 s on a dense desktop |
| decide (the Brain) | 15–31 s |
| action | 0.1–0.3 s |

So a three-step run is roughly two minutes and a few cents, and the Brain dominates. If a task
needs twenty steps, this is the wrong instrument; use the application's own API.

## Failure modes worth recognising

- **Clicks do nothing and the run looks successful.** UIPI: synthetic input cannot reach a window
  running at a higher integrity level than Python. If the editor runs as administrator, run the
  harness the same way, or expect silence.
- **`could not bring the target window to the foreground after 3 attempts`.** Something keeps
  stealing focus; the body refuses rather than clicking into whatever is on top.
- **`no visible window matching ...`.** The window closed, or the title changed beyond the
  substring (Unreal's title carries the open level).
- **`refusing to act at (x,y): outside the target window`.** The Eyes pointed outside the handle.
  The step fails rather than acting elsewhere; give the Brain a `visual_focus` or a clearer goal.
- **Typed text arrives without accents or symbols.** Anything non-ASCII goes through the
  clipboard; if the clipboard is unavailable to the target, it will not arrive.

## What this body cannot do

- **No element addressing.** There is no UI Automation path yet, so a run cannot say "invoke the
  button named Compile"; it clicks pixels. Unreal's Slate UI is unmeasured for a tree.
- **No browser of the accessibility tree**, so a moved control means a re-grounding.
- **Layer 3 (`request_diff`) and the `screenshot` action still work**, and the transcript under
  `artifacts/runs/<timestamp>-<tag>/` holds every frame and every prompt.

## Use it on your own machine without hurting yourself

The two gates are a stopgap. They exist because BRYES runs as the same Windows user who owns the
documents on this desktop. The structural fix is environment isolation: a dedicated user session
where the desktop holds only what the task created. Until that exists, treat a host run as
production: close or save your work, and prefer a target you launched.

## Worked example

`devices/smoke_windows_drive.py` is the shortest complete one:

```powershell
$env:BRYES_ALLOW_HOST = "1"
python devices/smoke_windows_drive.py --yes `
    --launch "python artifacts/probe_target.py" `
    --goal "Click inside the text field and type the word hello"
```

It launches a throwaway window, drives it by handle, verifies by reading the window title, and
prints the transcript path.
