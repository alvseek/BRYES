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
python api/bridge_client.py act --from pins --json '{"type":"drag","x":600,"y":260,"x2":900,"y2":300}'
python api/bridge_client.py act --json '{"type":"type","text":"Event BeginPlay"}'
python api/bridge_client.py locate "the Compile button"
python api/bridge_client.py profiles windows/unreal-editor
python api/bridge_client.py act --json '{"type":"key_hold","key":"w","seconds":1.5}'
```

Select a window with `--window`, `BRIDGE_WINDOW`, or `--title`. An explicit `--window` wins,
then `BRIDGE_WINDOW`, then `--title`; the server resolves the title and requires exactly one
match. Profiles and windows do not require a selector. Start the updated server before using
the updated client; there is no fallback to older server behavior. The server defaults to `http://127.0.0.1:8110`;
set `BRIDGE_URL` to use another address.

`act --json` accepts the same action object or `{"actions":[...]}` batch as the server's
[`/act` endpoint](README-Bridge.md#endpoints). Put the target in `--window`, `BRIDGE_WINDOW`, or
`--title`, not inside the JSON. The client adds that selector; the server validates verbs,
required fields and batch execution. New server verbs and fields need no matching CLI flags.
The old positional verb/coordinate syntax and `--key`, `--text`, `--dir`, and `--seconds` flags
are no longer accepted; those values belong in the JSON.

For example, press Enter, wait one second, then type:

```powershell
python api/bridge_client.py act --json '{"actions":[{"type":"key","key":"enter"},{"type":"delay","miliseconds":1000},{"type":"type","text":"abc"}]}'
```

Each saved image has a JSON mapping file beside it. `act --from <shot>` converts `x,y` and
`x2,y2` from that image back to original frame pixels, for either one action or every action
in a batch. All points in that request must use the same saved image; other fields, including
delay durations, pass through unchanged. Without `--from`, coordinates are already frame pixels.
The mapping does not verify that the screen or window has stayed in the same place since the
capture, so observe again when geometry changes.

`--raise` sends one focused capture request to the server, which hovers where the pointer already
is when inside the window, or at the window's centre otherwise. It requires the server's host-input
gate. `act` returns after the server response without an automatic settling delay; `--settle`
has been removed. Use explicit `{"type":"delay","miliseconds":1000}` actions when a pause is
needed. Delays hold the server's batch lock and do not verify UI readiness. The client's HTTP
timeout is 60 seconds, so keep the complete request within that limit; a timeout does not cancel
server execution and is not permission to retry input. The Windows body clamps key-hold durations
to 0.1–5 seconds; omit the JSON `seconds` field to use its default.
