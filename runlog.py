"""BRYES — per-run transcript logger.

Preserves the COMPLETE record of a loop run: every prompt sent to the Eyes/Brain and
every raw reply, plus the per-step screenshot. Written under
`artifacts/runs/<timestamp>-<tag>/` (gitignored via artifacts/).

Inactive by default: start() opens a transcript, stop() closes it, and record()/
save_image() no-op while inactive — so importing this in the model clients is free and
the standalone phase tests write nothing.

    import runlog
    runlog.start(goal, static={"brain.SYSTEM_PROMPT": ...})
    runlog.set_step(1)
    runlog.save_image("step-01.png", png_bytes)
    runlog.record("describe", request, response, focus="...")
    ...
    runlog.stop()
"""
import json
from datetime import datetime
from pathlib import Path

from paths import ARTIFACTS

_dir = None
_tx = None
_step = 0


def _text(x):
    if isinstance(x, (dict, list)):
        return json.dumps(x, indent=2, ensure_ascii=False, default=str)
    return str(x)


def start(goal, static=None, tag="run"):
    """Open a new transcript folder + file. Returns the run directory path."""
    global _dir, _tx, _step
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    _dir = ARTIFACTS / "runs" / f"{ts}-{tag}"
    _dir.mkdir(parents=True, exist_ok=True)
    _tx = open(_dir / "transcript.md", "w", encoding="utf-8")
    _step = 0
    _tx.write(f"# BRYES run transcript\n\n- when: `{ts}`\n- goal: {goal}\n")
    if static:
        _tx.write("\n## Static prompts (sent every step, shown once)\n")
        for name, text in static.items():
            _tx.write(f"\n### {name}\n\n```\n{text}\n```\n")
    _tx.write("\n---\n")
    _tx.flush()
    return str(_dir)


def set_step(n):
    """Mark the current step; subsequent records file under it."""
    global _step
    _step = n
    if _tx:
        _tx.write(f"\n# Step {n}\n")
        _tx.flush()


def save_image(name, data):
    """Persist a screenshot into the run folder and reference it in the transcript."""
    if _dir is None:
        return None
    path = _dir / name
    with open(path, "wb") as f:
        f.write(data)
    if _tx:
        _tx.write(f"\n![{name}]({name})  `{name}`\n")
        _tx.flush()
    return str(path)


def record(phase, request, response, **meta):
    """Append one request/response pair (a describe/decide/locate/action) to the log."""
    if _tx is None:
        return
    _tx.write(f"\n## {phase}\n")
    if meta:
        _tx.write(f"\nmeta: `{json.dumps(meta, ensure_ascii=False, default=str)}`\n")
    _tx.write(f"\n**request**\n\n```\n{_text(request)}\n```\n")
    _tx.write(f"\n**response**\n\n```\n{_text(response)}\n```\n")
    _tx.flush()


def note(text):
    """Append a lightweight one-line note (e.g. per-step timing) to the transcript."""
    if _tx is None:
        return
    _tx.write(f"\n_{text}_\n")
    _tx.flush()


def stop():
    """Close the current transcript (safe to call when inactive)."""
    global _tx, _dir
    if _tx:
        _tx.write("\n---\n_end of transcript_\n")
        _tx.close()
    _tx = None
    _dir = None
