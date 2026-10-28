"""Model-free regression tests for grounding.py (no network, no Eyes).

    python test_grounding.py

The live number needs a real frame and a paid locate() call; everything that could be wrong
in the harness is checked here instead: the hit rule, the distance, the aggregation, label
validation, and the end-to-end write with a fake locator.
"""
import json
import tempfile
from pathlib import Path

from PIL import Image

import grounding


def test_inside_and_distance():
    box = (10, 20, 30, 40)
    assert grounding.inside(box, 10, 20)                  # top-left edge
    assert grounding.inside(box, 30, 40)                  # bottom-right edge
    assert not grounding.inside(box, 9, 30)
    assert grounding.distance(box, 20, 30) == 0.0
    assert grounding.distance(box, 5, 30) == 5.0          # left of the box
    assert grounding.distance(box, 20, 45) == 5.0         # below the box
    assert round(grounding.distance(box, 0, 0), 3) == round((10**2 + 20**2) ** 0.5, 3)
    print("PASS: hit rule counts the edge, and distance measures to the box")


def test_score_aggregates_per_kind():
    targets = [
        {"kind": "node_header", "instruction": "a", "box": [0, 0, 10, 10]},
        {"kind": "node_header", "instruction": "b", "box": [0, 0, 10, 10]},
        {"kind": "pin", "instruction": "c", "box": [0, 0, 10, 10]},
    ]
    probes, detail = grounding.score(targets, [(5, 5), (50, 50), (0, 0)])
    by_kind = {p["kind"]: p for p in probes}
    assert by_kind["node_header"]["hits"] == 1
    assert by_kind["node_header"]["attempts"] == 2
    assert by_kind["node_header"]["rate"] == 0.5
    assert by_kind["pin"]["rate"] == 1.0
    assert "empty_canvas" not in by_kind               # a kind with no probes is absent
    assert detail[1]["hit"] is False
    assert detail[1]["error_px"] > 0
    print("PASS: per-kind rate, absent kinds skipped, and miss distance recorded")


def test_labels_validation():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bad.json"
        p.write_text(json.dumps({"project": "x", "frame": "f", "targets": []}), encoding="utf-8")
        try:
            grounding.load_labels(p)
        except ValueError as e:
            assert "at least one target" in str(e)
        else:
            raise AssertionError("an empty target list must be refused")

        p.write_text(json.dumps({"project": "x", "frame": "f", "targets": [
            {"kind": "pin", "instruction": "i", "box": [10, 10, 5, 5]}]}), encoding="utf-8")
        try:
            grounding.load_labels(p)
        except ValueError as e:
            assert "x1 < x2" in str(e)
        else:
            raise AssertionError("an inverted box must be refused")
    print("PASS: label validation refuses an empty set and an inverted box")


def test_end_to_end_with_fake_locator():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        frame = d / "frame.png"
        Image.new("RGB", (100, 100), (30, 30, 30)).save(frame, "PNG")
        labels = d / "labels.json"
        labels.write_text(json.dumps({
            "project": "lsgi",
            "frame": str(frame),
            "targets": [
                {"kind": "node_header", "instruction": "the node header", "box": [10, 10, 40, 30]},
                {"kind": "pin", "instruction": "the exec pin", "box": [60, 60, 70, 70]},
            ],
        }), encoding="utf-8")

        def fake_locator(_frame_bytes, instruction):
            return {"x": 20, "y": 20} if "header" in instruction else {"x": 90, "y": 90}

        out = d / "report.json"
        report = grounding.run(frame, labels, out, locator=fake_locator)
        assert out.exists() and (d / "report-overlay.png").exists()
        assert report["source"]["project"] == "lsgi"
        assert report["source"]["ground_model"] == grounding.GROUND_MODEL
        by_kind = {p["kind"]: p for p in report["probes"]}
        assert by_kind["node_header"]["rate"] == 1.0
        assert by_kind["pin"]["rate"] == 0.0
        assert by_kind["pin"]["median_error_px"] > 0
        assert len(report["targets"]) == 2
    print("PASS: end to end with a fake locator writes the report and the overlay")


if __name__ == "__main__":
    test_inside_and_distance()
    test_score_aggregates_per_kind()
    test_labels_validation()
    test_end_to_end_with_fake_locator()
    print("PASS: all grounding harness tests green")
