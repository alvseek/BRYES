# Windows Bridge Client

[bridge_client.py](bridge_client.py) is a command-line client for the separate
[Windows Bridge server](README-Bridge.md). It sends HTTP requests; it does not control the
desktop directly. Start the server first and enable its host-input gate when actions are needed.

Run from the BRYES root:

```powershell
$env:BRIDGE_WINDOW = "0x1402aa"                                # an id from `windows`
python api/bridge_client.py windows
python api/bridge_client.py shot overview --raise              # bring the window forward first
python api/bridge_client.py crop pins 1500 700 2580 1000 --scale 2
python api/bridge_client.py act drag 600 260 900 300 --from pins   # crop pixels -> frame pixels
python api/bridge_client.py act type --text "Event BeginPlay"
python api/bridge_client.py locate "the Compile button"
python api/bridge_client.py profiles windows/unreal-editor
python api/bridge_client.py act key_hold --key w --seconds 1.5
```

Select a window with `--window`, `BRIDGE_WINDOW`, or `--title`. An explicit `--window` wins,
then `BRIDGE_WINDOW`, then `--title`; the server resolves the title and requires exactly one
match. Profiles and windows do not require a selector. Start the updated server before using
the updated client; there is no fallback to older server behavior. The server defaults to `http://127.0.0.1:8110`;
set `BRIDGE_URL` to use another address.

Each saved image has a JSON mapping file beside it. Pass its name to `act --from` to convert
image coordinates back to the original frame. The mapping does not verify that the screen or
window has stayed in the same place since the capture, so observe again when geometry changes.

`--raise` sends one focused capture request to the server, which hovers where the pointer already
is when inside the window, or at the window's centre otherwise. It requires the server's host-input
gate. `act` waits `--settle` seconds (default 0.4) after input. The Windows body
clamps key-hold durations to 0.1–5 seconds; omit `--seconds` to use its default.
