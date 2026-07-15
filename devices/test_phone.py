"""BRYES — deterministic PhoneDevice smoke (model-free), mirroring test_hands/test_shell.

Verifies the phone body is reachable and its Device primitives work — no Eyes/Brain, no
API cost. Prereq: a phone connected via USB with debugging authorized (`adb devices` ->
'<serial>\tdevice').  Run:  python devices/test_phone.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402
from devices import PhoneDevice, Device  # noqa: E402


def main():
    d = PhoneDevice()
    assert isinstance(d, Device), "PhoneDevice does not satisfy the Device Protocol"
    print(f"PASS: connected {d.caps.name} {d.caps.width}x{d.caps.height} "
          f"(shell={d.caps.shell_flavor})")

    # Capabilities are touchscreen-shaped, not desktop-flattened.
    assert "right_click" not in d.caps.verbs and "hover" not in d.caps.verbs, d.caps.verbs
    assert "Back" in d.caps.keys and "Home" in d.caps.keys, d.caps.keys
    print("PASS: caps are touchscreen-shaped (no right_click/hover; Back/Home present)")

    # screencap -> a real PNG whose size matches the advertised coordinate space.
    png = d.screenshot()
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "screenshot is not a PNG"
    w, h = Image.open(io.BytesIO(png)).size
    assert (w, h) == (d.caps.width, d.caps.height), \
        f"png {w}x{h} != caps {d.caps.width}x{d.caps.height}"
    print(f"PASS: screencap -> valid PNG {w}x{h} ({len(png)} bytes)")

    # shell (Tier-2) round-trips.
    r = d.shell("echo bryes-phone-ok")
    assert r["ok"] and "bryes-phone-ok" in r["stdout"], r
    print("PASS: adb shell round-trips (echo -> stdout, exit 0)")

    # act executes without error. A touchscreen has no queryable pointer to assert on, so
    # this checks the transport (harmless wake key — idempotent, changes nothing lasting).
    d.act({"type": "key", "key": "KEYCODE_WAKEUP"})
    print("PASS: act(key) executes (KEYCODE_WAKEUP)")

    print("\nPASS: all PhoneDevice smoke checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
