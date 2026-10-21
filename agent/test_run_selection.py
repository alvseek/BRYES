"""BRYES — model-free tests for embodiment resolution + the answer-only run() path (ADR-006).

No phone, no container, no live model: resolve_embodiment gets an injected fake picker, and
run()'s answer-only branch is exercised with select_embodiment / answer / _make_device
monkeypatched. The full loop on a real body is validated live (Phase 4), not here.

Run:  python agent/test_run_selection.py
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agent.loop as L  # noqa: E402


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return cond


def _emb(device, profiles, reason="r"):
    return SimpleNamespace(device=device, profiles=profiles, reason=reason)


def _cat():
    return "CATALOG"


def _raises(fn, needle=""):
    """True when `fn` refuses with `needle` in the message. Catches both kinds the loop uses:
    RuntimeError for an unavailable body, ValueError for a contradictory argument."""
    try:
        fn()
        return False
    except (RuntimeError, ValueError) as e:
        return needle in str(e)


def main():
    ok = True

    # 1. resolve_embodiment -> answer mode (device None)
    r = L.resolve_embodiment("q", picker=lambda g, c: _emb(None, []), catalog_reader=_cat)
    ok &= check("resolve: device None -> answer mode", r == {"mode": "answer", "reason": "r"})

    # 2. resolve_embodiment -> loop mode (root + profiles)
    r = L.resolve_embodiment("g", picker=lambda g, c: _emb("android", ["android/whatsapp"]),
                             catalog_reader=_cat)
    ok &= check("resolve: loop mode root+profiles",
                r == {"mode": "loop", "root": "android",
                      "profiles": ["android/whatsapp"], "reason": "r"})

    # 3. unknown body raises ("macos" — "windows" became a known body, so it can no longer
    #    serve as the negative case; a negative fixture has to name something still absent)
    ok &= check("resolve: unknown body raises", _raises(
        lambda: L.resolve_embodiment("g", picker=lambda g, c: _emb("macos", []),
                                     catalog_reader=_cat), "unknown body"))

    # 4. mixed-root profiles raise (one body per run)
    ok &= check("resolve: mixed-root raises", _raises(
        lambda: L.resolve_embodiment(
            "g", picker=lambda g, c: _emb("android", ["android/whatsapp", "linux/x"]),
            catalog_reader=_cat), "not under body"))

    # 5. a profile with no profile.md on disk raises
    ok &= check("resolve: nonexistent profile raises", _raises(
        lambda: L.resolve_embodiment(
            "g", picker=lambda g, c: _emb("android", ["android/nope"]),
            catalog_reader=_cat), "no profiles/"))

    # 6. run() answer-only: returns {status: answered}, NEVER instantiates a device
    def fake_pick(g, c):
        return _emb(None, [], "pure question")

    def fake_answer(g):
        return "Paris"

    def boom(root):
        raise AssertionError("run() made a device in answer-only mode")

    L.select_embodiment = fake_pick
    L.answer = fake_answer
    real_make = L._make_device          # captured: the patch below must not leak into later checks
    L._make_device = boom
    res = L.run("capital of france?", verbose=False)
    L._make_device = real_make
    ok &= check("run answer-only -> status answered + answer",
                res.get("status") == "answered" and res.get("answer") == "Paris")

    # 7. run() forced-profile validation happens BEFORE any hardware
    ok &= check("run forced mixed profiles raises", _raises(
        lambda: L.run("g", profile=["android/whatsapp", "linux/x"], verbose=False),
        "one body per run"))
    ok &= check("run forced bogus profile raises", _raises(
        lambda: L.run("g", profile="android/nope", verbose=False), "no profiles/"))

    # 8. the host body refuses EARLY, before a body is built or a screenshot is taken
    saved = os.environ.pop("BRYES_ALLOW_HOST", None)
    try:
        ok &= check("host body refuses without BRYES_ALLOW_HOST", _raises(
            lambda: L._make_device("windows"), "BRYES_ALLOW_HOST"))
        ok &= check("run(device='windows') refuses before any body is built", _raises(
            lambda: L.run("g", device="windows", verbose=False), "BRYES_ALLOW_HOST"))
    finally:
        if saved is not None:
            os.environ["BRYES_ALLOW_HOST"] = saved

    # 9. with the gate open, a body name resolves and carries its window
    os.environ["BRYES_ALLOW_HOST"] = "1"
    try:
        dev = L._make_device("windows", window="Unreal")
        ok &= check("host body resolves with the gate open",
                    dev.caps.name == "windows-desktop" and getattr(dev, "_window", None) == "Unreal")
    finally:
        os.environ.pop("BRYES_ALLOW_HOST", None)

    # 9b. and the other bodies still resolve when a window is in play (regression: window=None
    #     was forwarded to every constructor and broke `device="linux"` outright)
    ok &= check("container body resolves with window=None",
                L._make_device("linux", window=None).caps.name == "docker-desktop")
    ok &= check("container body resolves with no kwargs",
                L._make_device("linux").caps.name == "docker-desktop")

    # 10. window means nothing on any other body: refuse, do not silently ignore
    ok &= check("window without device='windows' is refused",
                _raises(lambda: L.run("g", window="Unreal", verbose=False), "window names"))

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
