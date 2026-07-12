"""BRYES Phase 2 proof.

Grabs a screenshot from the running Screen container, asks the Eyes to locate a
known element (the calculator's "7" button), and proves it two ways:
  1) draws a red crosshair on the predicted point -> eyes_located.png
  2) actually clicks the point; if the Eyes were right, the calculator shows "7"
     -> eyes_after_click.png

Run:  python eyes/test_phase2.py   (or from inside eyes/: python test_phase2.py)
"""
import io
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client import locate  # noqa: E402
from paths import artifact  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

SCREEN = "http://localhost:8000"
TARGET = "the number 7 button in the calculator"


def screenshot():
    return urllib.request.urlopen(SCREEN + "/screenshot", timeout=15).read()


def action(payload):
    req = urllib.request.Request(
        SCREEN + "/action", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req, timeout=15).read()


def main():
    print(f"target: {TARGET!r}")
    img = screenshot()

    res = locate(img, TARGET)
    print("model replied :", res["content"])
    print("raw coord     :", res["raw_model_coord"],
          "in resized", res["resized_dims_wh"], "of", res["original_dims_wh"])
    print("-> pixel      :", (res["x"], res["y"]))
    print("token usage   :", res["usage"])

    # 1) visual proof: crosshair on the predicted point
    im = Image.open(io.BytesIO(img)).convert("RGB")
    d = ImageDraw.Draw(im)
    x, y = res["x"], res["y"]
    d.line([(x - 22, y), (x + 22, y)], fill=(255, 0, 0), width=3)
    d.line([(x, y - 22), (x, y + 22)], fill=(255, 0, 0), width=3)
    d.ellipse([x - 15, y - 15, x + 15, y + 15], outline=(255, 0, 0), width=3)
    im.save(artifact("eyes_located.png"))
    print("saved eyes_located.png  (red crosshair = where the Eyes pointed)")

    # 2) behavioral proof: click it; a correct hit makes the calculator show 7
    action({"type": "click", "x": x, "y": y})
    time.sleep(0.5)
    with open(artifact("eyes_after_click.png"), "wb") as f:
        f.write(screenshot())
    print("saved eyes_after_click.png  (calculator after clicking that point)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
