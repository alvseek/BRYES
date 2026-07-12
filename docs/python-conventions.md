---
project: BRYES
tags: [python, conventions, encoding, windows, console, cross-platform]
description: "Python coding conventions for BRYES — chiefly: keep console output ASCII-safe (no emoji) so scripts don't crash on Windows cp1252."
created: "2026-07-12"
updated: "2026-07-12"
---

# BRYES — Python Conventions

## **PURPOSE**
Cross-cutting rules for Python source in BRYES that every agent should follow.
BRYES runs on Windows + Docker; scripts are launched from a Windows console whose
default encoding is **cp1252**, which cannot encode emoji. This file captures the
conventions that keep the code portable across that environment.

## **QUICK REFERENCE**
- **No emoji in Python that reaches the console.** Anything printed (or that could end
  up in an exception/log rendered to the terminal) must be ASCII-safe.
- Use plain text status markers instead: **`PASS:` / `FAIL:` / `WARN:` / `OK` / `[step N]`**.
- **Em-dashes (`—`, U+2014) and cp1252-covered typography are fine** — they encode on
  Windows. It's specifically emoji / symbols outside cp1252 that crash.

## **DETAILS**

### Why: cp1252 can't encode emoji → UnicodeEncodeError
On Windows the console defaults to the `cp1252` code page. When Python's `print()`
tries to write a character outside cp1252 (e.g. `✅` = U+2705, and most emoji), it
raises `UnicodeEncodeError: 'charmap' codec can't encode character` and the script
**crashes at that print** — even if all the real work already succeeded. The failure
lands at the output line, so it's easy to mistake for a logic bug.

**Incident (2026-07-12):** `screen/test_phase1.py` did its full job correctly (saved
both screenshots, verified the click changed the screen) but crashed on its final
`print("\nPASS ✅ ...")`. The `✅` also carried a hidden variation selector (U+FE0F).
Fixed by replacing it with `PASS:`. All phase-test scripts were scanned; that was the
only emoji in a print.

### The convention: ASCII-safe source, not a runtime env fix
There is an env-level workaround — `PYTHONUTF8=1` (or `chcp 65001`) forces UTF-8 and
makes emoji print — but BRYES's convention is to **keep the source itself ASCII-safe**
rather than depend on every runner setting an env var. It's the more portable default
and removes a whole class of "works on my machine" crashes.

### Scope
Applies to every `.py` in the repo that prints, logs, or raises text a human will see
in the terminal (phase tests, `agent/loop.py`, clients, the Flask API). Markdown, docs,
and memory files are unaffected — emoji there are fine.

## **SOURCES**
- 2026-07-12 session: hit while verifying the `artifacts/` screenshot-storage refactor;
  running `screen/test_phase1.py` surfaced the crash. Alvi's call: strip emoji from
  prints and capture the rule as a project convention.
