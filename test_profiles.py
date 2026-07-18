"""BRYES — model-free tests for the profile system (profiles.py).

No LLM, no device: pure filesystem. Covers load_profiles (multi-path merge + dedup),
single-path back-compat parity, profile_exists, read_catalog, and a CATALOG DRIFT guard
(every profile path listed in profiles/index.md must resolve to a real profile.md on disk).

Run:  python test_profiles.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import profiles as p  # noqa: E402


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return cond


def _catalog_paths():
    """The profile paths listed as `- `<path>` — ...` items in the catalog."""
    return re.findall(r"^\s*-\s+`([^`]+)`", p.read_catalog(), re.MULTILINE)


def main():
    ok = True

    # 1. single-path load_profile == the multi-path special case
    ok &= check("load_profile('android/whatsapp') == load_profiles([...])",
                p.load_profile("android/whatsapp") == p.load_profiles(["android/whatsapp"]))

    # 2. a single path already merges its inheritance chain (base + leaf)
    wa = p.load_profiles(["android/whatsapp"])
    ok &= check("visual carries the UI ELEMENTS head", "UI ELEMENTS" in wa["visual"])
    ok &= check("visual carries the whatsapp leaf", "Send button" in wa["visual"])
    ok &= check("operating carries the android base", "go back one screen" in wa["operating"])

    # 2b. glossary is labelled PER SOURCE (ADR-007): each profile's Terms & Vocab gets its own
    #     "<LABEL> UI ELEMENTS:" head, in BOTH halves — never a single undifferentiated blob.
    ok &= check("visual has ANDROID + WHATSAPP UI ELEMENTS heads",
                "ANDROID UI ELEMENTS:" in wa["visual"] and "WHATSAPP UI ELEMENTS:" in wa["visual"])
    ok &= check("operating has ANDROID + WHATSAPP UI ELEMENTS heads",
                "ANDROID UI ELEMENTS:" in wa["operating"] and "WHATSAPP UI ELEMENTS:" in wa["operating"])
    ok &= check("no unlabelled 'UI ELEMENTS:' blob head",
                "\nUI ELEMENTS:" not in ("\n" + wa["visual"]) and not wa["visual"].startswith("UI ELEMENTS:"))

    # 3. dedup: android is already in whatsapp's chain, so adding it explicitly is a NO-OP
    #    (the shared base is merged once, not twice)
    merged = p.load_profiles(["android/whatsapp", "android"])
    ok &= check("adding an ancestor path is a no-op (base merged once)",
                merged == p.load_profiles(["android/whatsapp"]))
    ok &= check("android base 'go back one screen' appears once",
                merged["operating"].count("go back one screen") == 1)

    # 4. empty / None inputs are safe and empty
    ok &= check("load_profiles([]) is empty", p.load_profiles([]) == {"visual": "", "operating": ""})
    ok &= check("load_profile(None) is empty", p.load_profile(None) == {"visual": "", "operating": ""})

    # 5. profile_exists true / false
    ok &= check("profile_exists('android')", p.profile_exists("android"))
    ok &= check("profile_exists('android/whatsapp')", p.profile_exists("android/whatsapp"))
    ok &= check("profile_exists('linux')", p.profile_exists("linux"))
    ok &= check("not profile_exists('android/nope')", not p.profile_exists("android/nope"))
    ok &= check("not profile_exists('')", not p.profile_exists(""))

    # 6. catalog is present and lists real entries
    cat = p.read_catalog()
    ok &= check("read_catalog() non-empty", bool(cat))
    paths = _catalog_paths()
    ok &= check("catalog lists >= 3 profiles", len(paths) >= 3)

    # 7. DRIFT GUARD: every catalog path resolves to a real profile.md
    missing = [pa for pa in paths if not p.profile_exists(pa)]
    ok &= check(f"every catalog path resolves on disk (missing: {missing})", not missing)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
