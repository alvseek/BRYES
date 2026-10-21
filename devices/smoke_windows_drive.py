"""BRYES — LIVE smoke for the host body. This one MOVES THE REAL MOUSE AND CLICKS.

Manual only: it is the only test in this repo that can click on your desk. It obeys both rules
learned on 2026-10-21:

1. It acts ONLY on a window belonging to the process it starts itself (`--launch`), addressed by
   handle. A title substring once matched the largest window containing "Notepad", which was the
   user's open document.
2. It kills ONLY that process, and only if it started it.

    $env:BRYES_ALLOW_HOST = "1"
    python devices/smoke_windows_drive.py --yes `
        --launch "python artifacts/probe_target.py" `
        --goal "Click inside the text field and type the word hello"

What it proves that the unit tests cannot: synthetic input reaches a real application at all
(UIPI refuses silently into an elevated window), the foreground guard keeps the target in front,
and a click lands where the screenshot said it would.
"""
import argparse
import os
import shlex
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.loop import run                       # noqa: E402
from devices.windows import (                    # noqa: E402
    WindowsDevice, host_allowed, top_window_of_pid, window_title,
)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Drive the REAL desktop, against a target it starts.")
    ap.add_argument("--goal", required=True, help="what the agent should try to do")
    ap.add_argument("--launch", required=True,
                    help="command that starts the target window, e.g. 'python artifacts/probe_target.py'")
    ap.add_argument("--steps", type=int, default=3, help="max steps (default 3)")
    ap.add_argument("--yes", action="store_true", help="required: this moves your real mouse")
    args = ap.parse_args(argv)

    if not args.yes:
        print("FAIL: refusing to drive the real desktop without --yes")
        return 2
    if not host_allowed():
        print("FAIL: set BRYES_ALLOW_HOST=1 first (a screenshot-only run does not need it)")
        return 2

    target = subprocess.Popen(shlex.split(args.launch, posix=False))
    device = None
    before = None
    try:
        found = None
        for _ in range(40):
            found = top_window_of_pid(target.pid)
            if found:
                break
            time.sleep(0.25)
        if not found:
            print(f"FAIL: no window appeared for pid {target.pid}")
            return 1
        hwnd, title, _rect = found
        print(f"target pid={target.pid} hwnd={hwnd} title={title!r}")

        device = WindowsDevice(hwnd=hwnd)
        before = device.pointer()
        print(f"body: {device.caps.name} {device.caps.width}x{device.caps.height} pointer={before}")
        print(f"goal: {args.goal}\n")

        result = run(args.goal, device=device, max_steps=args.steps, verbose=True, tag="host-smoke")
        print(f"\nstatus: {result.get('status')}  steps: {result.get('steps')}")
        print(f"target title now: {window_title(hwnd)!r}")
        return 0 if result.get("status") in ("done", "fail") else 1
    finally:
        if device is not None and before is not None:
            device._get_input()._py.moveTo(*before, duration=0)
            print(f"pointer restored to {before}")
        target.terminate()                      # rule 2: only the process we started
        try:
            target.wait(timeout=3)
        except subprocess.TimeoutExpired:
            target.kill()
        print("target closed")


if __name__ == "__main__":
    sys.exit(main())
