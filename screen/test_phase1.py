"""BRYES Phase 1 proof — stdlib only, runs on the host.

Verifies the roadmap's "Done when":
  1) trigger a screenshot and get back a PNG, AND
  2) send a click and see the screen change afterward.

Usage:  python test_phase1.py
Saves:  shot_before.png, shot_after.png  (eyeball them — that's the real proof)
"""
import json
import sys
import time
import urllib.request

BASE = "http://localhost:8000"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _get(path):
    return urllib.request.urlopen(BASE + path, timeout=15)


def _post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=15)


def _screenshot(name):
    body = _get("/screenshot").read()
    assert body[:8] == PNG_MAGIC, f"not a PNG (got {body[:8]!r})"
    with open(name, "wb") as f:
        f.write(body)
    print(f"   saved {name} ({len(body):,} bytes)")
    return body


def main():
    # 1. wait for the display + API to come up
    for _ in range(90):
        try:
            if _get("/health").status == 200:
                print("health: OK")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print("FAIL: control API never became healthy on :8000")
        return 1

    # 2. screenshot -> PNG
    print("1) screenshot -> PNG")
    before = _screenshot("shot_before.png")

    # 3. a click that reliably changes the screen: right-click the desktop
    #    root summons the fluxbox menu (layout-independent visible change).
    print("2) right-click desktop (640,750) -> screen should change")
    _post("/action", {"type": "click", "button": 3, "x": 640, "y": 750})
    time.sleep(0.6)
    after = _screenshot("shot_after.png")
    _post("/action", {"type": "key", "key": "Escape"})  # dismiss the menu

    if before == after:
        print("WARN: screenshots identical — the click produced no visible change.")
        return 2

    print("\nPASS ✅  screenshot works and a click visibly changed the screen.")
    print("Phase 1 proven. Open http://localhost:6080/vnc.html to watch it live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
