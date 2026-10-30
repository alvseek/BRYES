"""Command-line client for the Windows Bridge (api/bridge-windows.py).

One short line per step instead of hand-built JSON and curl. Every image it saves carries a mapping
sidecar, so a pixel read off an enlarged crop can be sent back as an action without doing the
`origin + x / scale` arithmetic by hand.

    python api/bridge_client.py windows
    python api/bridge_client.py shot overview [--scale 0.5] [--raise]
    python api/bridge_client.py crop pins 1500 700 2580 1000 [--scale 2]
    python api/bridge_client.py act click 1700 900
    python api/bridge_client.py act drag 600 260 900 300 --from pins     # crop pixels -> frame pixels
    python api/bridge_client.py act key --key ctrl+a
    python api/bridge_client.py act type --text "Event BeginPlay"
    python api/bridge_client.py act scroll 1150 530 --dir up

Target window: --window <id>, or BRIDGE_WINDOW, or --title <substring> (must match exactly one
window). Server: BRIDGE_URL (default http://127.0.0.1:8110). Images go to --out (default
artifacts/bridge-shots), each as <name>.png beside <name>.json holding its mapping.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_URL = "http://127.0.0.1:8110"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "artifacts" / "bridge-shots"
POINTER_VERBS = {"click", "double_click", "right_click", "hover", "scroll"}


class BridgeError(RuntimeError):
    """The Bridge answered with an HTTP error; the message carries its status and body."""


# ---- pure helpers (tested model-free) -------------------------------------------------------

def mapping_from_headers(headers):
    """The frame mapping of a scaled image, from its X-Bryes-* headers. A plain 1:1 screenshot
    carries no headers and maps as scale 1, origin (0,0)."""
    h = {k.lower(): v for k, v in headers.items()}
    scale = float(h.get("x-bryes-scale", "1"))
    ox, oy = (int(v) for v in h.get("x-bryes-origin", "0,0").split(","))
    frame = h.get("x-bryes-frame")
    fw, fh = (int(v) for v in frame.split(",")) if frame else (None, None)
    return {"scale": scale, "origin": [ox, oy], "frame": [fw, fh]}


def to_frame(mapping, x, y):
    """A pixel of a saved image -> the frame pixel /act expects (frame = origin + px / scale)."""
    ox, oy = mapping["origin"]
    s = mapping["scale"]
    return round(ox + x / s), round(oy + y / s)


def build_action(window, kind, coords=(), key=None, text=None, direction=None, mapping=None,
                 seconds=None):
    """The /act payload. With a mapping, every coordinate pair is converted to frame pixels."""
    payload = {"window": window, "type": kind}
    pts = list(coords)
    if len(pts) % 2:
        raise ValueError("coordinates come in x y pairs")
    if mapping:
        conv = []
        for i in range(0, len(pts), 2):
            conv.extend(to_frame(mapping, pts[i], pts[i + 1]))
        pts = conv
    if kind == "drag":
        if len(pts) != 4:
            raise ValueError("drag needs x y x2 y2")
        payload.update(x=pts[0], y=pts[1], x2=pts[2], y2=pts[3])
    elif kind in POINTER_VERBS:
        if len(pts) != 2:
            raise ValueError(f"{kind} needs x y")
        payload.update(x=pts[0], y=pts[1])
    if kind == "scroll":
        payload["direction"] = direction or "down"
    if kind in ("key", "key_hold"):
        if not key:
            raise ValueError(f"{kind} needs --key")
        payload["key"] = key
    if seconds is not None:
        if kind != "key_hold":
            raise ValueError("--seconds is only valid for key_hold")
        payload["seconds"] = seconds
    if kind == "type":
        if text is None:
            raise ValueError("type needs --text")
        payload["text"] = text
    return payload


# ---- HTTP -------------------------------------------------------------------------------------

class BridgeClient:
    def __init__(self, base=None, out=None):
        self.base = (base or os.environ.get("BRIDGE_URL") or DEFAULT_URL).rstrip("/")
        self.out = Path(out) if out else DEFAULT_OUT

    def _open(self, req):
        try:
            return urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError as e:
            raise BridgeError(f"HTTP {e.code}: {e.read().decode(errors='replace')}") from None

    def get_json(self, path):
        with self._open(self.base + path) as r:
            return json.loads(r.read().decode())

    def windows(self):
        return self.get_json("/windows")["windows"]

    def act(self, payload):
        req = urllib.request.Request(self.base + "/act", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with self._open(req) as r:
            return json.loads(r.read().decode())

    def locate(self, window, instruction):
        selector = window if isinstance(window, dict) else {"window": window}
        req = urllib.request.Request(
            self.base + "/locate", data=json.dumps({**selector, "instruction": instruction}).encode(),
            headers={"Content-Type": "application/json"})
        with self._open(req) as r:
            return json.loads(r.read().decode())

    def profiles(self, path):
        return self.get_json("/profiles?" + urllib.parse.urlencode({"path": path}))

    def save_image(self, path, name, body=None):
        """GET an image endpoint; write <name>.png and its mapping as <name>.json."""
        req = self.base + path if body is None else urllib.request.Request(
            self.base + path, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        with self._open(req) as r:
            data = r.read()
            mapping = mapping_from_headers(dict(r.headers.items()))
        self.out.mkdir(parents=True, exist_ok=True)
        png = self.out / f"{name}.png"
        png.write_bytes(data)
        (self.out / f"{name}.json").write_text(json.dumps(mapping), encoding="utf-8")
        return png, mapping

    def load_mapping(self, name):
        sidecar = self.out / f"{name}.json"
        if not sidecar.exists():
            raise BridgeError(f"no mapping for '{name}' in {self.out}; take that shot first")
        return json.loads(sidecar.read_text(encoding="utf-8"))


# ---- CLI ----------------------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(description="Windows Bridge client")
    p.add_argument("--window", default=os.environ.get("BRIDGE_WINDOW"))
    p.add_argument("--title", help="pick the window by title substring (exactly one match)")
    p.add_argument("--out", help=f"image folder (default {DEFAULT_OUT})")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("windows", help="list targetable windows")

    loc = sub.add_parser("locate", help="locate an element by description")
    loc.add_argument("instruction")

    prof = sub.add_parser("profiles", help="read a profile's visual and operating vocabulary")
    prof.add_argument("path")

    s = sub.add_parser("shot", help="downscaled overview of the target's monitor")
    s.add_argument("name")
    s.add_argument("--scale", default="0.5")
    s.add_argument("--raise", dest="raise_", action="store_true", help="bring the window forward first")

    c = sub.add_parser("crop", help="enlarged crop, in frame pixels")
    c.add_argument("name")
    c.add_argument("box", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"))
    c.add_argument("--scale", default="2")
    c.add_argument("--raise", dest="raise_", action="store_true")

    a = sub.add_parser("act", help="one action")
    a.add_argument("kind")
    a.add_argument("coords", nargs="*", type=int)
    a.add_argument("--key")
    a.add_argument("--text")
    a.add_argument("--dir", dest="direction")
    a.add_argument("--seconds", type=float, help="duration for key_hold (body clamps to 0.1-5 seconds)")
    a.add_argument("--from", dest="from_shot", help="coords are pixels of this saved shot")
    a.add_argument("--settle", type=float, default=0.4, help="seconds to wait after acting")

    args = p.parse_args(argv)
    client = BridgeClient(out=args.out)
    try:
        if args.cmd == "windows":
            for w in client.windows():
                mark = "*" if w.get("foreground") else " "
                print(f"{mark} {w['id']:>10}  {w['title'][:70]}  image_rect={w['image_rect']}")
            return 0
        if args.cmd == "profiles":
            print(json.dumps(client.profiles(args.path), ensure_ascii=False))
            return 0
        selector = {"window": args.window} if args.window else {"title": args.title} if args.title else None
        if not selector:
            raise BridgeError("no target: pass --window, --title, or set BRIDGE_WINDOW")
        if args.cmd == "locate":
            print(json.dumps(client.locate(selector, args.instruction), ensure_ascii=False))
        elif args.cmd == "shot":
            params = {**selector, "scale": args.scale}
            path = "/downscaleshot"
            png, m = client.save_image(path if args.raise_ else path + "?" + urllib.parse.urlencode(params),
                                       args.name, {**params, "raise": True} if args.raise_ else None)
            print(f"{png}  scale={m['scale']} origin={m['origin']} frame={m['frame']}")
        elif args.cmd == "crop":
            x1, y1, x2, y2 = args.box
            params = {**selector, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "scale": args.scale}
            path = "/upscaleshot"
            png, m = client.save_image(path if args.raise_ else path + "?" + urllib.parse.urlencode(params),
                                       args.name, {**params, "raise": True} if args.raise_ else None)
            print(f"{png}  scale={m['scale']} origin={m['origin']} frame={m['frame']}")
        elif args.cmd == "act":
            mapping = client.load_mapping(args.from_shot) if args.from_shot else None
            payload = build_action(selector.get("window"), args.kind, args.coords, args.key, args.text,
                                   args.direction, mapping, args.seconds)
            payload.pop("window")
            payload.update(selector)
            print(json.dumps(client.act(payload)))
            time.sleep(args.settle)
        return 0
    except (BridgeError, ValueError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
