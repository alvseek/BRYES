"""BRYES — deterministic lesson-builder tests (model-free). No network, no Unreal.

Covers the only behaviour that matters for trust: a step whose screenshot is missing must
FAIL the build, an explicit `shot: none` must build, and annotation must actually write an
image the HTML can point at.

Run:  python test_lesson.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image  # noqa: E402

import lesson  # noqa: E402

FRONT = """---
title: Test lesson
project: LSGI
created: 2026-01-01
---

Intro paragraph.
"""

STEP_ONE = """
## Step 1: Look at the thing
shot: shots/one.png
callout: 0.1,0.1,0.5,0.5 | the thing
instruction:
  Do it.
why:
  Because.
expected:
  It is done.
"""

STEP_TWO = """
## Step 2: A step that needs no picture
shot: none
instruction:
  Press the key.
"""


def _shot(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (400, 300), (30, 30, 34)).save(path)


def test_happy_path():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "lsgi-01"
        d.mkdir()
        _shot(d / "shots" / "one.png")
        (d / "lesson.md").write_text(FRONT + STEP_ONE + STEP_TWO, encoding="utf-8")

        report = lesson.build(d)
        assert report["steps"] == 2, report
        assert report["shots"] == 1 and report["callouts"] == 1 and report["text_only"] == 1, report
        page = (d / "lesson.html").read_text(encoding="utf-8")
        assert "Test lesson" in page and "assets/step-001.callouts.png" in page, "html missing bits"
        assert "step-002.callouts.png" not in page, "text-only step got an image"
        assert (d / "assets" / "step-001.callouts.png").exists(), "annotated image not written"
        print("PASS: two-step lesson builds (1 screenshot, 1 callout, 1 text-only)")


def test_missing_shot_fails():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "broken"
        d.mkdir()
        (d / "lesson.md").write_text(FRONT + STEP_ONE, encoding="utf-8")   # shot never captured
        try:
            lesson.build(d)
        except lesson.LessonError as e:
            assert any("missing shot" in p for p in e.problems), e.problems
            assert not (d / "lesson.html").exists(), "wrote html despite a missing shot"
        else:
            raise AssertionError("build succeeded with a missing shot")
        print("PASS: a step citing a missing shot fails the build and writes nothing")


def test_missing_shot_declaration_fails():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "no-decl"
        d.mkdir()
        (d / "lesson.md").write_text(
            FRONT + "\n## Step 1: Undeclared\n\ninstruction:\n  Do it.\n", encoding="utf-8")
        try:
            lesson.build(d)
        except lesson.LessonError as e:
            assert any("no `shot:`" in p for p in e.problems), e.problems
        else:
            raise AssertionError("build succeeded without a shot declaration")
        print("PASS: an undeclared shot fails honestly instead of rendering a prose-only step")


def test_bad_callout_fails():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "bad-callout"
        d.mkdir()
        _shot(d / "shots" / "one.png")
        (d / "lesson.md").write_text(
            FRONT + STEP_ONE.replace("0.1,0.1,0.5,0.5", "0.5,0.1,0.1,0.5"), encoding="utf-8")
        try:
            lesson.build(d)
        except lesson.LessonError as e:
            assert any("0<=x1<x2<=1" in p for p in e.problems), e.problems
        else:
            raise AssertionError("build accepted an inverted callout box")
        print("PASS: an inverted callout box is refused, not drawn")


def main():
    test_happy_path()
    test_missing_shot_fails()
    test_missing_shot_declaration_fails()
    test_bad_callout_fails()
    print("\nPASS: all lesson-builder checks green")


if __name__ == "__main__":
    main()
