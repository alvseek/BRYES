"""BRYES — Shell channel (/exec) regression test (deterministic, $0, no models).

Verifies the Tier-2 shell effector with model-free assertions, so it can gate a change:

  - echo:        a simple command returns stdout + exit 0, ok:true
  - failure:     a non-zero exit is reported (exit_code + ok:false)
  - bad payload: a request with no command -> HTTP 400
  - timeout:     a hang is killed at the timeout (timed_out:true) and returns fast
  - stdin:       optional stdin is fed to the command (cat echoes it back)
  - truncation:  oversized stdout is clipped (~4 KB), not returned whole

Usage:  python test_shell.py        (needs the Screen container running on :8000)
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"

_fails = 0


def _exec(payload):
    """POST /exec -> (http_status, parsed_json_or_None)."""
    req = urllib.request.Request(
        BASE + "/exec", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def check(name, cond, detail=""):
    global _fails
    if cond:
        print(f"PASS: {name}")
    else:
        _fails += 1
        print(f"FAIL: {name} -- {detail}")


# 1) echo -> stdout + exit 0
st, r = _exec({"command": "echo hello"})
check("echo returns stdout + exit 0",
      st == 200 and r and r.get("ok") and r.get("exit_code") == 0
      and r.get("stdout", "").strip() == "hello",
      f"status={st} body={r}")

# 2) non-zero exit reported
st, r = _exec({"command": "sh -c 'exit 3'"})
check("non-zero exit reported",
      st == 200 and r and r.get("ok") is False and r.get("exit_code") == 3,
      f"status={st} body={r}")

# 3) missing command -> 400
st, r = _exec({})
check("missing command -> 400", st == 400, f"status={st}")

# 4) a hang is killed at the timeout and returns fast
t0 = time.time()
st, r = _exec({"command": "sleep 5", "timeout": 1})
elapsed = time.time() - t0
check("hang killed at timeout (fast)",
      st == 200 and r and r.get("timed_out") is True and elapsed < 3,
      f"status={st} body={r} elapsed={elapsed:.2f}s")

# 5) optional stdin is fed to the command
st, r = _exec({"command": "cat", "stdin": "piped-input"})
check("stdin fed to command",
      st == 200 and r and r.get("stdout", "").strip() == "piped-input",
      f"status={st} body={r}")

# 6) oversized stdout is clipped (~4 KB), not returned whole (20000 chars in)
st, r = _exec({"command": "yes x | head -c 20000"})
out_len = len(r.get("stdout", "")) if r else 0
check("oversized stdout clipped",
      st == 200 and r and r.get("ok") and 0 < out_len < 8000,
      f"status={st} stdout_len={out_len} (expected < 8000, well under 20000)")

print()
if _fails:
    print(f"FAIL: {_fails} check(s) failed")
    sys.exit(1)
print("PASS: all shell-channel checks green")
