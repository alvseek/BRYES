"""BRYES — labelled screenshot capture for lessons (the RECORDING half).

Alvi drives the app; this records the moment. It never clicks, types or moves anything:
the body it uses advertises no pointer verbs.

    python capture.py --lesson battle-loop-01 --step 3 --phase before \
        --window Unreal --note "Content Browser, right-click menu open"

Saves `lessons/<lesson>/shots/step-003-before.png` and appends one JSON line to
`lessons/<lesson>/capture-log.jsonl`: when, which window was actually captured, the image
size, the PNG bytes, and the note. The log is the provenance a lesson builder reads, so a
step that cites a shot which is missing (or older than the lesson) can be refused instead
of rendered.

    python capture.py --list-windows        # what is capturable right now

The lesson lives wherever `--out` says. Default is `lessons/` at the repo root; point it
at the project being taught (e.g. LSGI's `docs/lessons/`) when the lesson belongs there.
"""
import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

from devices import WindowsDevice

ROOT = Path(__file__).resolve().parent
PHASES = ("before", "after", "result")


def _safe(text):
    """A window title can contain anything; a cp1252 console cannot (AGENTS.md: no crash on print)."""
    enc = sys.stdout.encoding or "utf-8"
    return str(text).encode(enc, "replace").decode(enc, "replace")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Capture a labelled screenshot for a lesson.")
    ap.add_argument("--lesson", help="lesson id, e.g. battle-loop-01")
    ap.add_argument("--step", type=int, help="step number in the lesson")
    ap.add_argument("--phase", default="after", choices=PHASES,
                    help="which moment this is (default: after)")
    ap.add_argument("--note", default="", help="what this shot shows / why it was taken")
    ap.add_argument("--window", default=None,
                    help="title substring to capture (default: the whole desktop)")
    ap.add_argument("--no-raise", action="store_true",
                    help="do not bring the window to the foreground before grabbing")
    ap.add_argument("--out", default=str(ROOT / "lessons"),
                    help="lessons directory (default: <repo>/lessons)")
    ap.add_argument("--list-windows", action="store_true",
                    help="print the visible titled windows and exit")
    args = ap.parse_args(argv)

    if args.list_windows:
        rows = [r for r in _list_visible()]
        if not rows:
            print("WARN: no visible titled windows found")
            return 1
        for title, (left, top, right, bottom) in rows:
            print(f"{right - left:5d}x{bottom - top:<5d}  {_safe(title)}")
        return 0

    if not args.lesson or not args.step:
        ap.error("--lesson and --step are required (or use --list-windows)")

    device = WindowsDevice(window=args.window, raise_window=not args.no_raise)
    png = device.screenshot()

    shot_dir = Path(args.out) / args.lesson / "shots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    shot = shot_dir / f"step-{args.step:03d}-{args.phase}.png"
    shot.write_bytes(png)

    with Image.open(io.BytesIO(png)) as im:
        width, height = im.size

    entry = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "lesson": args.lesson,
        "step": args.step,
        "phase": args.phase,
        "note": args.note,
        "window_request": args.window,
        "shot": shot.relative_to(Path(args.out)).as_posix(),
        "bytes": len(png),
        "width": width,
        "height": height,
    }
    log = Path(args.out) / args.lesson / "capture-log.jsonl"
    with log.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"PASS: saved {shot.as_posix()}  {width}x{height} ({len(png)} bytes)")
    return 0


def _list_visible():
    from devices.windows import list_windows
    for title, rect in list_windows():
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w >= 200 and h >= 200:
            yield title, rect


if __name__ == "__main__":
    sys.exit(main())
