"""BRYES — app/OS profiles: contextual knowledge fed to the Eyes (visual) and Brain (operating).

Small perception/reasoning models don't carry reliable per-app priors, so we SUPPLY the knowledge
as context (no fine-tuning). A profile lives at `profiles/<os>/[<env>/]<app>/profile.md` and
INHERITS every profile.md up its path (OS base -> ... -> app leaf), so shared conventions live once
at the top. Each profile.md has up to three sections:

  ## Terms & Vocab   shared glossary of UI elements (fed to BOTH the Eyes and the Brain, so the
                     Brain's `target` names line up with what the Eyes are told to recognize)
  ## Visual          how to READ the screen  -> the Eyes (describe)
  ## Operating       how to OPERATE the app   -> the Brain (decide)

load_profiles(["android/whatsapp"]) returns {"visual": ..., "operating": ...} where each half is
the shared UI-ELEMENTS glossary (merged Terms & Vocab) + a PER-PROFILE labelled section — e.g.
"HOW ANDROID WORKS" then "HOW WHATSAPP WORKS" (operating) / "HOW ANDROID LOOKS" then "HOW WHATSAPP
LOOKS" (visual) — so the Brain and Eyes see which knowledge is the OS's and which is the app's.
"""
import re
from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
INDEX_FILE = PROFILES_DIR / "index.md"    # the catalog fed to the Brain's embodiment pick


def _parse_sections(text):
    """Split a profile.md into {section_title: body} by its `## ` headers."""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf).strip()
    return out


def _iter_profile_files(path):
    """Yield each existing profile.md down `path` (OS base first, leaf last).
    Missing segments are skipped silently, so a partial path still yields what exists."""
    parts = [p for p in str(path or "").strip("/").split("/") if p]
    accum = PROFILES_DIR
    for part in parts:
        accum = accum / part
        f = accum / "profile.md"
        if f.exists():
            yield f


def load_profiles(paths):
    """Load AND MERGE several profile paths into one {"visual": str, "operating": str}, with the
    Visual/Operating halves LABELLED PER PROFILE so the Brain and Eyes see which knowledge is the
    OS's and which is the app's — e.g. "HOW ANDROID WORKS" then "HOW WHATSAPP WORKS" (operating),
    "HOW ANDROID LOOKS" then "HOW WHATSAPP LOOKS" (visual). The label is the profile's own folder
    name (profiles/android/whatsapp/profile.md -> WHATSAPP).

    Each path contributes its own inheritance chain (OS base -> ... -> leaf); across ALL paths
    every profile.md is included exactly ONCE, in order — so a shared ancestor (the OS base) is a
    single labelled section, not one per path. The `Terms & Vocab` glossaries merge into one shared
    "UI ELEMENTS" head. Either half may be "" if nothing fills it; `load_profile` is the single-path
    special case."""
    seen, files = set(), []
    for path in paths or []:
        for f in _iter_profile_files(path):
            if f not in seen:
                seen.add(f)
                files.append(f)

    terms = []                            # list of (LABEL, body) — labelled PER SOURCE (ADR-007)
    visual, operating = [], []            # each: list of (LABEL, body)
    for f in files:
        label = f.parent.name.upper()     # profiles/android/whatsapp/profile.md -> "WHATSAPP"
        secs = _parse_sections(f.read_text(encoding="utf-8"))
        if secs.get("Terms & Vocab"):
            terms.append((label, secs["Terms & Vocab"]))
        if secs.get("Visual"):
            visual.append((label, secs["Visual"]))
        if secs.get("Operating"):
            operating.append((label, secs["Operating"]))

    def _join(labelled, verb):
        # Glossary labelled PER SOURCE ("ANDROID UI ELEMENTS:" / "WHATSAPP UI ELEMENTS:") so the
        # Brain + Eyes see which app each element belongs to — disambiguating collisions like
        # WhatsApp's "Search bar" vs Tokopedia's "Search box" (ADR-007).
        head = ""
        if terms:
            head = "\n\n".join(f"{label} UI ELEMENTS:\n{body}" for label, body in terms) + "\n\n"
        blocks = "\n\n".join(f"HOW {label} {verb}:\n{body}" for label, body in labelled)
        return (head + blocks).strip()

    return {"visual": _join(visual, "LOOKS"), "operating": _join(operating, "WORKS")}


def load_profile(path):
    """Back-compat single-path loader: profiles/<path>/profile.md AND every ancestor
    (OS base first, leaf last). Delegates to load_profiles([path])."""
    return load_profiles([path] if path else [])


def read_catalog():
    """The catalog text (profiles/index.md) fed to the Brain's embodiment pick, or "" if
    the catalog file is missing."""
    return INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else ""


def profile_exists(path):
    """True if profiles/<path>/profile.md exists — used to validate a picked profile path."""
    parts = [p for p in str(path or "").strip("/").split("/") if p]
    return bool(parts) and (PROFILES_DIR.joinpath(*parts) / "profile.md").exists()
