"""BRYES — app/OS profiles: contextual knowledge fed to the Eyes (visual) and Brain (operating).

Small perception/reasoning models don't carry reliable per-app priors, so we SUPPLY the knowledge
as context (no fine-tuning). A profile lives at `profiles/<os>/[<env>/]<app>/profile.md` and
INHERITS every profile.md up its path (OS base -> ... -> app leaf), so shared conventions live once
at the top. Each profile.md has up to three sections:

  ## Terms & Vocab   shared glossary of UI elements (fed to BOTH the Eyes and the Brain, so the
                     Brain's `target` names line up with what the Eyes are told to recognize)
  ## Visual          how to READ the screen  -> the Eyes (describe)
  ## Operating       how to OPERATE the app   -> the Brain (decide)

load_profile("android/whatsapp") returns {"visual": ..., "operating": ...} where
  visual    = Terms & Vocab + every Visual section down the chain
  operating = Terms & Vocab + every Operating section down the chain
"""
import re
from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parent / "profiles"


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


def load_profile(path):
    """Load profiles/<path>/profile.md AND every ancestor profile.md (OS base first, leaf last).
    Returns {"visual": str, "operating": str}; either may be "" if the chain has nothing for it.
    Unknown/missing segments are skipped silently, so a partial path still loads what exists."""
    parts = [p for p in str(path or "").strip("/").split("/") if p]
    terms, visual, operating = [], [], []
    accum = PROFILES_DIR
    for part in parts:
        accum = accum / part
        f = accum / "profile.md"
        if not f.exists():
            continue
        secs = _parse_sections(f.read_text(encoding="utf-8"))
        for key, bucket in (("Terms & Vocab", terms), ("Visual", visual), ("Operating", operating)):
            if secs.get(key):
                bucket.append(secs[key])

    def _join(sections):
        head = ("UI ELEMENTS:\n" + "\n".join(terms) + "\n\n") if terms else ""
        return (head + "\n\n".join(sections)).strip()

    return {"visual": _join(visual), "operating": _join(operating)}
