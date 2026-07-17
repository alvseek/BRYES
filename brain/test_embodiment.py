"""BRYES — model-free tests for the embodiment picker + answerer (brain/client.py, ADR-006).

No network, no live model: `structured_call` and `_load_key` are monkeypatched, so we assert
select_embodiment / answer parse + return correctly and the model-fallback escape wiring holds.

Run:  python brain/test_embodiment.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import brain.client as bc  # noqa: E402


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return cond


def main():
    ok = True
    bc._load_key = lambda: "test-key"   # offline: no .env needed
    bc.runlog = None                    # no transcript recording in the test

    # 1. select_embodiment returns a parsed Embodiment; schema_name is "embodiment"
    seen = {}

    def fake_ok(model_cls, messages, **kw):
        seen["schema"] = kw.get("schema_name")
        return model_cls(device="android", profiles=["android/whatsapp"], reason="msg app"), {"tot": 1}

    bc.structured_call = fake_ok
    emb = bc.select_embodiment("message X on whatsapp", "CATALOG")
    ok &= check("select_embodiment -> device android", emb.device == "android")
    ok &= check("select_embodiment -> profiles list", emb.profiles == ["android/whatsapp"])
    ok &= check("select_embodiment schema_name = embodiment", seen["schema"] == "embodiment")

    # 2. answer-only pick: device=None, empty profiles
    bc.structured_call = lambda mc, m, **kw: (mc(device=None, profiles=[], reason="pure q"), None)
    emb2 = bc.select_embodiment("capital of france?", "CATALOG")
    ok &= check("select_embodiment -> device None + empty profiles",
                emb2.device is None and emb2.profiles == [])

    # 3. answer() returns the plain string from the Answer schema
    bc.structured_call = lambda mc, m, **kw: (mc(answer="Paris"), None)
    ok &= check("answer() returns the string", bc.answer("capital of france?") == "Paris")

    # 4. model-fallback: primary raises StructuredError on its attempts, the LAST attempt
    #    escapes to BACKUP_MODEL and succeeds
    seq = []

    def flaky(mc, m, *, model, **kw):
        seq.append(model)
        if model == bc.MODEL:
            raise bc.StructuredError("boom")
        return mc(device="linux", profiles=[], reason="ok"), None

    bc.structured_call = flaky
    emb3 = bc.select_embodiment("do a desktop thing", "CATALOG")
    ok &= check("fallback escaped to backup -> device linux", emb3.device == "linux")
    ok &= check("tried primary first", seq[0] == bc.MODEL)
    ok &= check("used backup model on the last attempt", seq[-1] == bc.BACKUP_MODEL)

    # 5. total exhaustion raises RuntimeError
    bc.structured_call = lambda *a, **k: (_ for _ in ()).throw(bc.StructuredError("always"))
    try:
        bc.select_embodiment("g", "c")
        raised = False
    except RuntimeError:
        raised = True
    ok &= check("all attempts fail -> RuntimeError", raised)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
