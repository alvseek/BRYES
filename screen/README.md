# Screen: desktop control over HTTP

Screen is a standalone HTTP server and disposable Linux desktop packaged in a Docker
container. It captures screenshots, executes mouse and keyboard input, and runs shell
commands. Any HTTP client can use it; no model service or API key is required.

It controls the **desktop inside the container**, not the host computer's desktop.

## How it works

```text
HTTP client -> Flask control server -> scrot      -> desktop screenshot
                                   -> xdotool   -> mouse and keyboard input
                                   -> shell     -> command execution
```

The [control server](server/app.py) accepts individual operations over HTTP on port
`8000`. Clients receive PNG bytes for screenshots and JSON results for input and shell
operations. Clients own decisions, target selection, and sequencing; the server only
captures and executes what they request.

Screen currently serves **HTTP, not MCP**. No MCP screenshot tool is implemented here.

## Run it

Install Docker with Linux-container support. Run these commands from the directory
containing [docker-compose.yml](docker-compose.yml):

```bash
docker compose up --build -d
```

- **Control API:** <http://localhost:8000/health>
- **Live desktop:** <http://localhost:6080/vnc.html> (click *Connect*)

Chrome starts automatically at `https://www.google.com`. Calculator and xterm are
installed but not started; launch them when needed, for example:

```bash
docker exec -d bryes-screen gnome-calculator
docker exec -d bryes-screen xterm
```

[docker-compose.yml](docker-compose.yml) accepts `CHROME_START_URL` and
`SCREEN_RESOLUTION` from your environment. The display defaults to `1280x800x24`
(width, height, color depth); recreate the container after changing the resolution:

```bash
docker compose up -d --force-recreate
```

Chrome's startup window size is separately fixed at `1280x800` in
[scripts/entrypoint.sh](scripts/entrypoint.sh); a larger display does not automatically
make that window larger. Rebuild with `--build` after changing server or startup files,
because they are copied into the image rather than mounted live.

## HTTP contract

Requests use the base URL `http://localhost:8000`. POST bodies are JSON with
`Content-Type: application/json`.

| Method | Endpoint | Successful response |
|---|---|---|
| GET | `/health` | `{"status":"ok","display":":99"}`; HTTP 503 with `status:"no-display"` if the display check fails |
| GET | `/screenshot` | Raw PNG bytes with `Content-Type: image/png` |
| GET | `/pointer` | `{"x":120,"y":200}` for the current mouse position |
| POST | `/action` | `{"ok":true,"type":"click","stderr":""}` (type matches the requested action) |
| POST | `/exec` | `{"ok":true,"exit_code":0,"stdout":"...","stderr":""}` |

### Screenshots

`GET /screenshot` captures the current container desktop with `scrot` to a temporary
PNG file, then sends that file **directly in the response body**. The response is not
JSON, base64, a file path, or an image URL. A capture failure returns HTTP 500 with a
JSON error instead.

```bash
curl --fail http://localhost:8000/screenshot -o desktop.png
```

The client receives the image bytes and chooses whether to save, display, or process
them. The server does not forward the image to another service.

### Mouse and keyboard input

Coordinates are pixels in the container desktop, measured from its top-left corner.
Screen does not locate descriptions such as "the Save button"; the caller supplies
the coordinates. Each primitive performs only the named operation: typing does not
first click or clear a field.

| `type` | Payload fields besides `type` | Behavior |
|---|---|---|
| `click` | `x`, `y`, optional `button` (default `1`) | Move and click; `1` is left, `3` is right |
| `double_click` | `x`, `y` | Move and double-click the left button |
| `right_click` | `x`, `y` | Move and right-click |
| `hover` | `x`, `y` | Move without clicking |
| `scroll` | `x`, `y`, optional `direction` (default `down`), `amount` (default `3`) | Move and send wheel events; use `up` or `down` |
| `drag` | `x`, `y`, `x2`, `y2` | Press at the start, move, release at the destination |
| `type` | `text` | Type into the focused field |
| `key` | `key` | Tap an X keysym or chord, such as `Return`, `Escape`, or `ctrl+a` |
| `key_hold` | `key`, optional `seconds` (default `1`) | Hold down, wait, release; accepts `0.1` to `5` seconds |

```bash
curl --fail http://localhost:8000/action \
  -H "Content-Type: application/json" \
  -d '{"type":"click","x":120,"y":200}'

curl --fail http://localhost:8000/action \
  -H "Content-Type: application/json" \
  -d '{"type":"key_hold","key":"w","seconds":1.2}'
```

Use X key names such as `Return` for the Enter key.
The server refuses unknown actions, missing point coordinates, and invalid held-key
durations with HTTP 400; an input command that fails returns HTTP 500. Payload
validation is not comprehensive: some malformed numeric values can raise server errors.

For compound gestures, send the primitives in order: click to focus a field, send
`ctrl+a` to select its contents, then type the replacement text. The server does not
compose these operations automatically.

### Shell commands

`POST /exec` runs a non-interactive command inside the container, independently of
the display. It accepts `command`, optional `stdin`, and `timeout` in seconds (default
`30`, clamped to `1` through `300`).

```bash
curl --fail http://localhost:8000/exec \
  -H "Content-Type: application/json" \
  -d '{"command":"uname -r","timeout":30}'
```

A nonzero command exit still returns HTTP 200 with `ok:false`; a timeout returns
HTTP 200 with `ok:false`, `exit_code:null`, and `timed_out:true`. Check the JSON, not
only the HTTP status. A missing command returns HTTP 400. Each output stream longer
than 4,096 characters is clipped to its head and tail with an elision marker.

Clients must allow enough time in their HTTP request timeout for the requested command
to finish. Interactive prompts and terminal sessions
are not supported by `/exec`; drive xterm through input operations instead.

## What's inside

[Dockerfile](Dockerfile) builds Ubuntu 24.04 with Xvfb (`:99`), fluxbox, `xdotool`,
`scrot`, Chrome, gnome-calculator, and xterm. The startup script brings up the display,
window manager, D-Bus, Chrome, and the live viewer, then starts the Flask server.
`x11vnc` and noVNC provide the browser view. Flask is installed in an isolated Python
environment using [requirements.txt](requirements.txt).

## Verify and manage

From the directory containing this README, with host Python available:

```bash
python test_action_payloads.py    # mocked subprocess/transport; no Docker or display
python test_phase1.py             # live PNG + visible right-click change
python test_hands.py              # live input, pointer positions, held keys
python test_shell.py              # live shell output, errors, timeout, stdin, clipping
```

The model-free payload test needs Flask installed in the host Python environment;
the live tests use the running container on port `8000` and no models. The screenshot
proof prints the saved paths for `shot_before.png` and `shot_after.png`.
Pointer checks prove movement, not every application's response to an input;
inspect the live desktop for application-level behavior.

```bash
docker compose logs -f screen
docker compose down
```

There are no persistent volumes in the supplied Compose file. A stop/start retains
the container's writable layer, but removal or recreation discards its desktop state.

## Safety and known limits

**This is an unauthenticated development service, not a network-safe desktop gateway.**
The API can execute arbitrary shell commands as the container's root user, and the
live viewer has no password. The Flask server listens on `0.0.0.0` inside the container.
The supplied Compose mappings (`8000:8000`, `6080:6080`) do **not** restrict host access
to loopback; actual external reachability also depends on Docker and host firewall rules.
For local-only use, bind both published ports explicitly to `127.0.0.1` in Compose.
Do not expose either service to an untrusted network.

The supplied container has no host-directory or Docker-socket mounts, but it has network
access, and Chrome runs as root with `--no-sandbox`. Treat it as disposable, keep host
credentials out, and do not treat the container as protection against every hostile task.
The screenshot handler also leaves temporary PNG files behind; they accumulate until
cleaned up or the container is removed.
