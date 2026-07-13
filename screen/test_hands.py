"""BRYES — Hands regression test (deterministic, $0, no models).

Verifies the /action primitives — especially the newer ones (hover, double_click,
right_click, scroll, drag) — with model-free assertions, so it can gate a change:

  - smoke:        every primitive is accepted and runs -> {ok:true}
  - bad payloads: a point action with no x/y, a drag with no x2/y2 -> 400
  - point lands:  hover/click/double_click/scroll move the pointer to their (x,y),
                  asserted via GET /pointer (xdotool getmouselocation)
  - drag ends:    a drag leaves the pointer at its destination, via /pointer
  - right_click:  right-clicking the desktop opens the fluxbox menu (screenshot changes)

The pointer assertions cover the MOVE of every point action deterministically. App-level
BEHAVIOR (scroll actually scrolls a page, double_click selects) still needs a real app —
watch that live at http://localhost:6080/vnc.html.

Usage:  python test_hands.py         (needs the Screen container running on :8000)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import artifact  # noqa: E402

BASE = "http://localhost:8000"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PT = (640, 400)          # a neutral desktop point (no app under it)


def _get(path):
    return urllib.request.urlopen(BASE + path, timeout=15)


def _action(payload):
    """POST /action -> parsed JSON; raise if the result isn't ok."""
    req = urllib.request.Request(
        BASE + "/action", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    body = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if not body.get("ok"):
        raise AssertionError(f"{payload.get('type')} returned not-ok: {body}")
    return body


def _pointer():
    loc = json.loads(_get("/pointer").read())
    return (loc["x"], loc["y"])


def _screenshot(name=None):
    body = _get("/screenshot").read()
    assert body[:8] == PNG_MAGIC, f"not a PNG (got {body[:8]!r})"
    if name:
        with open(name, "wb") as f:
            f.write(body)
    return body


def _reset():
    """Dismiss any open menu so a check doesn't inherit prior state."""
    _action({"type": "key", "key": "Escape"})
    time.sleep(0.2)


# --- checks: each returns (name, passed, note) -------------------------------

def t_smoke():
    """Every primitive is accepted and runs -> {ok:true}."""
    _reset()
    for p in (
        {"type": "hover",        "x": PT[0], "y": PT[1]},
        {"type": "click",        "x": PT[0], "y": PT[1]},
        {"type": "double_click", "x": PT[0], "y": PT[1]},
        {"type": "right_click",  "x": PT[0], "y": PT[1]},
        {"type": "scroll",       "x": PT[0], "y": PT[1], "direction": "down", "amount": 2},
        {"type": "scroll",       "x": PT[0], "y": PT[1], "direction": "up",   "amount": 2},
        {"type": "drag",         "x": PT[0], "y": PT[1], "x2": PT[0] + 40, "y2": PT[1] + 40},
        {"type": "type",         "text": ""},
        {"type": "key",          "key": "Escape"},
    ):
        _action(p)
    return ("smoke: all primitives execute -> ok", True, "")


def t_bad_payloads():
    """A point action with no x/y, and a drag with no x2/y2, must 400."""
    def _is_400(payload):
        req = urllib.request.Request(
            BASE + "/action", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=15)
            return False
        except urllib.error.HTTPError as e:
            return e.code == 400
    ok = _is_400({"type": "click"}) and _is_400({"type": "drag", "x": 1, "y": 1})
    return ("bad payloads rejected (400)", ok, "" if ok else "expected HTTP 400")


def t_point_lands():
    """hover/click/double_click/scroll move the pointer to their (x,y) — via /pointer."""
    cases = [
        ("hover",        {"type": "hover",        "x": 320, "y": 240}),
        ("click",        {"type": "click",        "x": 500, "y": 360}),
        ("double_click", {"type": "double_click", "x": 240, "y": 500}),
        ("scroll",       {"type": "scroll", "x": 700, "y": 300, "direction": "down", "amount": 1}),
    ]
    bad = []
    for name, p in cases:
        _reset()
        _action(p)
        got = _pointer()
        if got != (p["x"], p["y"]):
            bad.append(f"{name}->{got}!=({p['x']},{p['y']})")
    return ("point actions land the pointer (/pointer)", not bad, "; ".join(bad))


def t_drag_ends():
    """A drag leaves the pointer at its destination — via /pointer."""
    _reset()
    a, b = (300, 300), (600, 480)
    _action({"type": "drag", "x": a[0], "y": a[1], "x2": b[0], "y2": b[1]})
    got = _pointer()
    return ("drag ends at destination (/pointer)", got == b,
            "" if got == b else f"pointer at {got}, expected {b}")


def t_right_click_menu():
    """right_click the desktop root -> fluxbox menu -> screenshot changes."""
    _reset()
    before = _screenshot(artifact("hands_menu_before.png"))
    _action({"type": "right_click", "x": PT[0], "y": PT[1]})
    time.sleep(0.5)
    after = _screenshot(artifact("hands_menu_after.png"))
    _reset()
    changed = before != after
    return ("right_click -> menu (screenshot changed)", changed,
            "" if changed else "no change — is fluxbox up?")


TESTS = [t_smoke, t_bad_payloads, t_point_lands, t_drag_ends, t_right_click_menu]


def main():
    for _ in range(90):                       # wait for the display + API
        try:
            if _get("/health").status == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print("FAIL: control API never became healthy on :8000")
        return 1

    failed = 0
    for t in TESTS:
        try:
            name, passed, note = t()
        except Exception as e:
            name, passed, note = (t.__name__, False, repr(e))
        print(("PASS:" if passed else "FAIL:") + f" {name}" + (f"  ({note})" if note else ""))
        failed += not passed

    print()
    if failed:
        print(f"FAIL: {failed}/{len(TESTS)} Hands checks failed.")
        return 1
    print(f"PASS: all {len(TESTS)} Hands checks passed. (App-level behavior (scroll a "
          "page, double_click selects): watch live at http://localhost:6080/vnc.html.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
