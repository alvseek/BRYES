"""BRYES - snapshot grounding tester.

One frame, a list of named targets with boxes, one `eyes.locate()` call per target: did the
point land inside the box? Aggregates per kind into the report shape the Unreal-driving
council declared (`contracts/measurement-report.schema.json`, C-1).

Why a frame and not a live run: `locate()` returns a pixel whether or not it is right, so a
miss is silent in a run. Scoring the same call against a box a human drew turns that into a
rate, and the rate is what decides whether a step should go by eye or through an app's API.

Usage:
    python grounding.py --frame <png> --labels <labels.json> [--out <report.json>]

Labels file (boxes are pixels, x1,y1,x2,y2, in the frame's own coordinate space):
    {
      "project": "lsgi",
      "frame": "artifacts/grounding/lsgi-2026-10-28/editor-monitor-01.png",
      "targets": [
        {"kind": "node_header", "instruction": "the header of the node Print String",
         "box": [1200, 340, 1420, 372]},
        {"kind": "pin", "instruction": "the exec pin on the left of Event BeginPlay",
         "box": [1096, 402, 1118, 420]},
        {"kind": "empty_canvas", "instruction": "an empty spot in the graph, away from any node",
         "box": [1500, 700, 1700, 900]}
      ]
    }

A hit is a point inside the target's box. An empty-canvas target's box is the blank region
itself, so the same rule scores it: a point on a node is a miss, and that is the honest
reading, because the caller asked for empty space.
"""
import argparse
import io
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eyes.client import GROUND_MODEL, locate  # noqa: E402

KINDS = ("node_header", "pin", "empty_canvas", "asset_tile")
INK = (255, 64, 64)


def load_labels(path):
    """(project, frame_path, targets) from a labels JSON file, validated."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    project = str(data.get("project") or "").strip()
    frame = str(data.get("frame") or "").strip()
    targets = data.get("targets") or []
    if not project:
        raise ValueError("labels: 'project' is required")
    if not frame:
        raise ValueError("labels: 'frame' is required")
    if not targets:
        raise ValueError("labels: 'targets' must hold at least one target")
    for i, t in enumerate(targets):
        kind = t.get("kind")
        if kind not in KINDS:
            raise ValueError(f"target {i}: kind must be one of {KINDS}, got {kind!r}")
        if not str(t.get("instruction") or "").strip():
            raise ValueError(f"target {i}: 'instruction' is required")
        box = t.get("box")
        if not (isinstance(box, list) and len(box) == 4 and all(isinstance(v, int) for v in box)):
            raise ValueError(f"target {i}: 'box' must be four integers")
        if not (box[0] < box[2] and box[1] < box[3]):
            raise ValueError(f"target {i}: box must be (x1 < x2, y1 < y2), got {box}")
    return project, frame, targets


def inside(box, x, y):
    """True when (x, y) falls in the box. The edge counts as inside: a click there lands."""
    x1, y1, x2, y2 = box
    return x1 <= x <= x2 and y1 <= y <= y2


def distance(box, x, y):
    """Pixels from (x, y) to the box: 0 when inside, else to the nearest edge or corner."""
    if inside(box, x, y):
        return 0.0
    x1, y1, x2, y2 = box
    dx = max(x1 - x, 0, x - x2)
    dy = max(y1 - y, 0, y - y2)
    return (dx * dx + dy * dy) ** 0.5


def score(targets, points):
    """The C-1 probe list plus per-target detail. `points` is [(x, y)] in target order."""
    if len(points) != len(targets):
        raise ValueError("score: one point per target")
    per_kind = {}
    detail = []
    for t, (x, y) in zip(targets, points):
        hit = inside(t["box"], x, y)
        d = distance(t["box"], x, y)
        detail.append({"instruction": t["instruction"], "kind": t["kind"],
                       "point": [x, y], "hit": hit, "error_px": round(d, 1)})
        per_kind.setdefault(t["kind"], []).append(d if not hit else 0.0)
    probes = []
    for kind in KINDS:
        errs = per_kind.get(kind)
        if not errs:
            continue
        attempts = len(errs)
        hits = sum(1 for e in errs if e == 0.0)
        probes.append({"kind": kind, "attempts": attempts, "hits": hits,
                       "rate": round(hits / attempts, 4),
                       "median_error_px": round(statistics.median(errs), 1)})
    return probes, detail


def render(frame_bytes, targets, points, out_path):
    """Draw each box and its returned point onto a copy, so a wrong answer key is visible."""
    im = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
    draw = ImageDraw.Draw(im)
    for t, (x, y) in zip(targets, points):
        x1, y1, x2, y2 = t["box"]
        draw.rectangle([x1, y1, x2, y2], outline=INK, width=2)
        draw.line([x - 6, y, x + 6, y], fill=INK, width=2)
        draw.line([x, y - 6, x, y + 6], fill=INK, width=2)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, "PNG")
    return out_path


def build_report(project, frame_rel, targets, points):
    """The C-1 report object. `verdict` is authored by the caller, not invented here."""
    probes, detail = score(targets, points)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"project": project, "frames": [frame_rel],
                   "ground_model": GROUND_MODEL},
        "probes": probes,
        "targets": detail,
    }, detail


def run(frame_path, labels_path, out_path, locator=None):
    """Score every target on one frame; write the report and the overlay; return the report."""
    locator = locator or locate
    project, frame_rel, targets = load_labels(labels_path)
    frame = Path(frame_path)
    frame_bytes = frame.read_bytes()
    points = []
    for t in targets:
        found = locator(frame_bytes, t["instruction"])
        points.append((int(found["x"]), int(found["y"])))
    report, detail = build_report(project, frame_rel, targets, points)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    render(frame_bytes, targets, points, out.with_name(out.stem + "-overlay.png"))
    for d in detail:
        mark = "hit" if d["hit"] else f"miss {d['error_px']}px"
        print(f"  {d['kind']:<13} {mark:<14} {d['instruction'][:60]}")
    for p in report["probes"]:
        print(f"PASS: {p['kind']} {p['hits']}/{p['attempts']} = {p['rate']:.0%}"
              f" (median error {p['median_error_px']}px)")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score eyes.locate() against a labelled frame.")
    ap.add_argument("--frame", required=True, help="the snapshot to test on")
    ap.add_argument("--labels", required=True, help="the answer key (JSON)")
    ap.add_argument("--out", default="", help="report path (default: beside the labels)")
    ap.add_argument("--check-labels", action="store_true",
                    help="only draw the boxes and exit, so a wrong key is caught before spending calls")
    args = ap.parse_args(argv)
    out = args.out or str(Path(args.labels).with_name(Path(args.labels).stem + "-report.json"))
    if args.check_labels:
        _project, _frame_rel, targets = load_labels(args.labels)
        frame_bytes = Path(args.frame).read_bytes()
        centres = [((b["box"][0] + b["box"][2]) // 2, (b["box"][1] + b["box"][3]) // 2)
                   for b in targets]
        dest = render(frame_bytes, targets, centres, str(Path(out).with_name(
            Path(args.labels).stem + "-boxes.png")))
        print(f"PASS: {len(targets)} boxes drawn, no model call made")
        print(f"boxes -> {dest}")
        for t in targets:
            print(f"  {t['kind']:<13} {t['box']}  {t['instruction'][:60]}")
        return 0
    try:
        run(args.frame, args.labels, out)
    except RuntimeError as e:                 # a model/network failure is not a data problem
        print(f"FAIL: {e}")
        return 1
    print(f"report -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
