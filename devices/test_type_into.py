"""BRYES — model-free tests for the type_into gesture (default_type_into / device.type_into).

No container, no phone, no LLM: a fake device records the atomic act()/clear_field() calls,
so we assert the click? -> clear? -> type -> Enter? SEQUENCE deterministically. Guards the
one-gesture contract (and the container's ctrl+a+Delete clear) against a refactor.

Run:  python devices/test_type_into.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devices.base import default_type_into  # noqa: E402
from devices.container import ContainerDevice  # noqa: E402
from devices.phone import PhoneDevice  # noqa: E402


class RecordingDevice:
    """Minimal Device stand-in: records every atomic call, in order."""

    def __init__(self):
        self.calls = []

    def act(self, action):
        self.calls.append(action)

    def clear_field(self):
        self.calls.append({"type": "clear_field"})


def _types(calls):
    return [c["type"] for c in calls]


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return cond


def main():
    ok = True

    # 1. type only -> types into the already-focused field (no click)
    d = RecordingDevice()
    default_type_into(d, "hello")
    ok &= check("type only -> [type]", _types(d.calls) == ["type"])
    ok &= check("type only carries text", d.calls[0].get("text") == "hello")

    # 2. click then type
    d = RecordingDevice()
    default_type_into(d, "hi", click_xy=(10, 20))
    ok &= check("click+type -> [click, type]", _types(d.calls) == ["click", "type"])
    ok &= check("click uses grounded coords", (d.calls[0]["x"], d.calls[0]["y"]) == (10, 20))

    # 3. type then enter
    d = RecordingDevice()
    default_type_into(d, "go", press_enter=True)
    ok &= check("type+enter -> [type, key]", _types(d.calls) == ["type", "key"])
    ok &= check("enter is the Enter key", d.calls[-1].get("key") == "Enter")

    # 4. clear then type
    d = RecordingDevice()
    default_type_into(d, "new", clear_first=True)
    ok &= check("clear+type -> [clear_field, type]", _types(d.calls) == ["clear_field", "type"])

    # 5. the full replace-and-submit: click -> clear -> type -> enter
    d = RecordingDevice()
    default_type_into(d, "DDR5", click_xy=(5, 5), clear_first=True, press_enter=True)
    ok &= check("full combo order == click,clear,type,key",
                _types(d.calls) == ["click", "clear_field", "type", "key"])

    # 6. ContainerDevice.clear_field expands to ctrl+a then Delete (patch act, no HTTP)
    c = ContainerDevice()
    rec = []
    c.act = lambda a: rec.append(a)
    c.clear_field()
    ok &= check("container clear_field -> ctrl+a, Delete",
                [a.get("key") for a in rec] == ["ctrl+a", "Delete"])

    # 7. ContainerDevice.type_into delegates through the shared gesture (clear = 2 keys)
    c = ContainerDevice()
    rec = []
    c.act = lambda a: rec.append(a)
    c.type_into("x", click_xy=(1, 2), clear_first=True, press_enter=True)
    ok &= check("container type_into order == click,ctrl+a,Delete,type,Enter",
                _types(rec) == ["click", "key", "key", "type", "key"])

    # 8. PhoneDevice.clear_field is an honest NotImplementedError (Android clear deferred)
    try:
        PhoneDevice.clear_field(object())          # unbound; body raises before touching self
        ok &= check("phone clear_field raises", False)
    except NotImplementedError:
        ok &= check("phone clear_field raises NotImplementedError", True)

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
