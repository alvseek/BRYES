"""BRYES — lesson builder: a markdown lesson plus real screenshots in, one HTML page out.

The recording half (`capture.py`) saves evidence. This half turns that evidence into
something a person can follow, and it refuses to build a step whose screenshot is missing.
That refusal is the whole point: without it a lesson is a plausible description of a screen
nobody ever captured.

A lesson is a folder:

    lessons/battle-loop-01/
      lesson.md                 # authored: body, steps, callouts, prose
      shots/step-001-before.png # evidence, written by capture.py
      lesson.html               # built by this file
      assets/*.callouts.png     # annotated copies the HTML references

Step syntax (see `lessons/battle-loop-01/lesson.md` for a worked example):

    ## Step 2: Close the floating Settings panel
    shot: shots/step-001-before.png
    callout: 0.55,0.82,0.69,0.97 | Settings
    instruction:
      Click the X in the panel's top-right corner.
    why:
      It covers the viewport center, so any screenshot you take now has it baked in.
    expected:
      The viewport is unobstructed again.

`shot: none` is an explicit opt-out for a step whose claim needs no screenshot (a keyboard
shortcut, a decision). It is counted and reported, so a lesson cannot quietly become all
prose.

    python lesson.py lessons/battle-loop-01
"""
import argparse
import html
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FIELD_RE = re.compile(r"^([a-z_]+):\s*(.*)$")
STEP_RE = re.compile(r"^##\s+Step\s+(\d+)\s*:\s*(.+?)\s*$", re.MULTILINE)
ACCENT = (255, 176, 32)          # amber: reads on Unreal's dark chrome and on screenshots
INK = (24, 24, 27)


class LessonError(Exception):
    """One or more problems that make the lesson unbuildable."""

    def __init__(self, problems):
        self.problems = problems
        super().__init__("; ".join(problems))


def parse_front_matter(text):
    """(meta dict, body) from a leading `---` fenced block of `key: value` lines."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
    return meta, text[end + 4:]


def parse_callouts(lines, problems, where):
    """[(x1, y1, x2, y2, label)] from `x1,y1,x2,y2 | Label` lines (fractions of the image)."""
    out = []
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        if "|" not in raw:
            problems.append(f"{where}: callout needs `x1,y1,x2,y2 | Label`, got {raw!r}")
            continue
        coords, _, label = raw.partition("|")
        try:
            x1, y1, x2, y2 = (float(p) for p in coords.split(","))
        except ValueError:
            problems.append(f"{where}: callout coords are not four numbers: {coords!r}")
            continue
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            problems.append(f"{where}: callout must satisfy 0<=x1<x2<=1 and 0<=y1<y2<=1: {coords!r}")
            continue
        out.append((x1, y1, x2, y2, label.strip()))
    return out


def parse_steps(body, problems):
    """[{n, title, fields}] from the `## Step N: title` blocks, plus the intro text."""
    marks = list(STEP_RE.finditer(body))
    intro = body[:marks[0].start()].strip() if marks else body.strip()
    steps = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        block = body[mark.end():end]
        fields = {}
        current = None
        for raw in block.splitlines():
            line = raw.rstrip()
            m = FIELD_RE.match(line)
            if m and not line.startswith((" ", "\t")):
                current = m.group(1)
                # A repeated key (one `callout:` line per box) accumulates rather than overwrites.
                fields.setdefault(current, []).append(m.group(2))
            elif current is not None:
                fields[current].append(line)
        where = f"step {mark.group(1)}"
        step = {"n": int(mark.group(1)), "title": mark.group(2).strip(), "where": where}
        step["fields"] = {k: "\n".join(v).strip() for k, v in fields.items()}
        shot = step["fields"].get("shot", "").strip()
        if not shot:
            problems.append(f"{where}: no `shot:` (use `shot: none` to say it needs no image)")
        elif shot != "none":
            step["_shot_rel"] = shot          # resolved against the lesson dir by build()
        step["shot"] = shot
        step["callouts"] = parse_callouts(
            step["fields"].get("callout", "").split("\n"), problems, where)
        steps.append(step)
    return intro, steps


def _font(size):
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def annotate(src, dest, callouts, max_width=1600):
    """Write an annotated copy of `src` to `dest` and return its pixel size."""
    img = Image.open(src).convert("RGB")
    if img.width > max_width:
        img = img.resize((max_width, round(img.height * max_width / img.width)), Image.LANCZOS)
    w, h = img.size
    draw = ImageDraw.Draw(img)
    stroke = max(2, round(w / 700))
    radius = max(3, round(w / 400))
    font = _font(max(13, round(w / 85)))
    for n, (x1, y1, x2, y2, _label) in enumerate(callouts, 1):
        box = (round(x1 * w), round(y1 * h), round(x2 * w), round(y2 * h))
        draw.rounded_rectangle(box, radius=radius, outline=ACCENT, width=stroke)
        # Badge straddles the box's top-RIGHT corner, and prefers to sit fully ABOVE the box:
        # panel titles sit at the top-left, and a toolbar is too short for a badge inside it.
        r = max(13, round(w / 75))
        cx = min(box[2], w - r - stroke)
        above = box[1] - r - stroke
        cy = above if above >= r else max(box[1], r + stroke)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ACCENT)
        text = str(n)
        tw = draw.textbbox((0, 0), text, font=font)
        draw.text((cx - (tw[2] - tw[0]) / 2, cy - (tw[3] - tw[1]) / 2 - tw[1]), text,
                  fill=INK, font=font)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")
    return img.size


def _inline(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)


def _blocks(text):
    """Paragraphs and `- ` bullet lists, which is all a lesson body needs."""
    out = []
    for chunk in re.split(r"\n\s*\n", text.strip()) if text.strip() else []:
        lines = [line for line in chunk.splitlines() if line.strip()]
        if lines and all(line.startswith("- ") for line in lines):
            out.append("<ul>" + "".join(
                f"<li>{_inline(line[2:].strip())}</li>" for line in lines) + "</ul>")
        else:
            out.append("<p>" + "<br>".join(_inline(line) for line in lines) + "</p>")
    return "\n".join(out)


CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 980px; padding: 40px 24px 80px;
  font: 16px/1.6 -apple-system, "Segoe UI", Roboto, sans-serif; color: #1b1b1f; background: #fff; }
header { border-bottom: 3px solid #1b1b1f; padding-bottom: 20px; margin-bottom: 32px; }
h1 { font-size: 30px; line-height: 1.2; margin: 0 0 8px; }
.meta { font-size: 13px; color: #666; letter-spacing: .02em; }
.intro { font-size: 17px; color: #333; }
.toc { background: #f6f6f4; border-left: 3px solid #ddd; padding: 14px 20px; margin: 24px 0 36px; }
.toc ol { margin: 6px 0 0; padding-left: 20px; }
.toc a { color: #1b1b1f; text-decoration: none; }
.step { margin: 0 0 48px; break-inside: avoid; }
.step h2 { font-size: 21px; margin: 0 0 4px; }
.step h2 .n { display: inline-block; min-width: 30px; margin-right: 10px; padding: 1px 7px;
  background: #1b1b1f; color: #fff; border-radius: 5px; font-size: 17px; text-align: center; }
figure { margin: 16px 0 10px; }
figure img { width: 100%; height: auto; display: block; border-radius: 6px;
  border: 1px solid #d8d8d4; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 10px 0 0; padding: 0; list-style: none;
  font-size: 13px; color: #555; }
.legend li { display: flex; gap: 6px; align-items: baseline; }
.legend b { display: inline-block; min-width: 20px; text-align: center; background: #ffb020;
  color: #18181b; border-radius: 10px; font-size: 12px; }
.prose { margin: 14px 0; }
details { margin: 12px 0 0; padding: 10px 14px; background: #f6f6f4; border-radius: 6px; }
summary { cursor: pointer; font-weight: 600; }
.expected { margin-top: 12px; padding-left: 12px; border-left: 3px solid #9ac48a; color: #2c4a22; }
code { background: #f0efec; padding: 1px 5px; border-radius: 4px; font-size: 14px; }
footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 13px; color: #777; }
@media print { body { max-width: none; padding: 0; } details { background: none; padding: 0; }
  details[open] summary { display: none; } .step { page-break-inside: avoid; } }
"""


def build(lesson_dir, max_width=1600):
    """Parse, validate, annotate and write lesson.html. Raises LessonError listing problems."""
    lesson_dir = Path(lesson_dir)
    src = lesson_dir / "lesson.md"
    if not src.exists():
        raise LessonError([f"no lesson.md in {lesson_dir}"])

    problems = []
    meta, body = parse_front_matter(src.read_text(encoding="utf-8"))
    intro, steps = parse_steps(body, problems)

    for step in steps:
        if step.get("_shot_rel"):
            path = lesson_dir / step["_shot_rel"]
            if not path.exists():
                problems.append(f"{step['where']}: cites a missing shot: {step['_shot_rel']}")
            else:
                step["_shot"] = path
    if not steps:
        problems.append("no `## Step N: title` blocks found")
    if problems:
        raise LessonError(problems)

    assets = lesson_dir / "assets"
    parts = [
        "<header>",
        f"<h1>{_inline(meta.get('title') or lesson_dir.name)}</h1>",
        f"<div class=\"meta\">{_inline(meta.get('project', ''))} "
        f"&middot; lesson {_inline(meta.get('lesson') or lesson_dir.name)} "
        f"&middot; {_inline(meta.get('created', ''))}"
        f"{' &middot; for ' + _inline(meta['target']) if meta.get('target') else ''}</div>",
        "</header>",
    ]
    if intro:
        parts.append(f"<div class=\"intro\">{_blocks(intro)}</div>")

    parts.append("<nav class=\"toc\"><strong>Steps</strong><ol>")
    for step in steps:
        parts.append(f"<li><a href=\"#step-{step['n']}\">{_inline(step['title'])}</a></li>")
    parts.append("</ol></nav>")

    counted = {"shots": 0, "callouts": 0, "text_only": 0}
    for step in steps:
        fields = step["fields"]
        parts.append(f"<section class=\"step\" id=\"step-{step['n']}\">")
        parts.append(f"<h2><span class=\"n\">{step['n']}</span>{_inline(step['title'])}</h2>")

        if step.get("_shot"):
            counted["shots"] += 1
            out = assets / f"step-{step['n']:03d}.callouts.png"
            annotate(step["_shot"], out, step["callouts"], max_width=max_width)
            rel = out.relative_to(lesson_dir).as_posix()
            parts.append(f"<figure><img src=\"{rel}\" alt=\"step {step['n']} screenshot\">")
            if step["callouts"]:
                counted["callouts"] += len(step["callouts"])
                parts.append("<ol class=\"legend\">")
                for n, (_a, _b, _c, _d, label) in enumerate(step["callouts"], 1):
                    parts.append(f"<li><b>{n}</b> {_inline(label)}</li>")
                parts.append("</ol>")
            parts.append("</figure>")
        else:
            counted["text_only"] += 1

        for key, cls in (("instruction", "prose"), ("expected", "expected")):
            if fields.get(key):
                parts.append(f"<div class=\"{cls}\">{_blocks(fields[key])}</div>")
        if fields.get("why"):
            parts.append(f"<details><summary>Why this matters</summary>"
                         f"{_blocks(fields['why'])}</details>")
        parts.append("</section>")

    parts.append("<footer>Built by BRYES from real screenshots. Every image in this lesson was "
                 "captured from the running application, not drawn or reconstructed.</footer>")

    page = (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{_inline(meta.get('title') or lesson_dir.name)}</title>"
            f"<style>{CSS}</style></head><body>" + "\n".join(parts) + "</body></html>")

    out_html = lesson_dir / "lesson.html"
    out_html.write_text(page, encoding="utf-8", newline="\n")
    return {"html": out_html, "steps": len(steps), **counted}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build one lesson folder into lesson.html.")
    ap.add_argument("lesson", help="lesson folder, e.g. lessons/battle-loop-01")
    ap.add_argument("--width", type=int, default=1600, help="max image width (default 1600)")
    args = ap.parse_args(argv)
    try:
        report = build(args.lesson, max_width=args.width)
    except LessonError as e:
        print(f"FAIL: {len(e.problems)} problem(s)")
        for problem in e.problems:
            print(f"  - {problem}")
        return 1
    rel = Path(report["html"]).as_posix()
    print(f"PASS: built {rel} ({report['steps']} steps, {report['shots']} screenshots, "
          f"{report['callouts']} callouts, {report['text_only']} text-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
