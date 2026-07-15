# High Wizard Plan

## **PROJECT INFO**
- **Project**: BRYES
- **Date**: 2026-07-15
- **Agent**: claude-software-architect
- **Theme**: Add a shell/command effector channel — the Brain runs commands inside the sandboxed Screen container (Tier 2), using direct commands instead of vision for OS/CLI tasks; framed within an effector-hierarchy architecture (Tier 1 API/MCP, Tier 2 shell, Tier 3 vision) captured as an ADR.
- **Source Protocol**: `/high-wizard` — [Procedure](//@agent-memory/control-files/procedures/high-wizard.md)

*CRITICAL INSTRUCTION: To continue this plan: load the source protocol above, then inspect which sections below are filled vs unfilled to infer your current step.*

---

## **OBJECTIVES**
Give BRYES a **shell/command effector channel** so the Brain can run **non-interactive** commands inside the sandboxed Screen container and get `stdout`/`stderr`/exit-code back — reaching for **direct commands (Tier 2)** instead of vision for OS / file / CLI / network tasks. Frame it within an **effector-hierarchy architecture** (Tier 1 API/MCP [future], Tier 2 shell, Tier 3 vision-fallback) and capture that architecture as an **ADR**, since future channels (http, mcp, email, phone) will inherit the pattern. This matures BRYES from "a vision agent" into "a tool-using agent whose tools *include* vision."

### **Related Documents**
- [architecture-overview.md](../docs/architecture-overview.md) - BRYES 4-piece architecture + load-bearing facts (to be updated with the new channel)
- [agent-loop-flow.md](../docs/agent-loop-flow.md) - data-flow view of the loop (to be updated with the shell action path)
- ADR (effector-hierarchy) — created by this plan (Section G)

### **SUCCESS CRITERIA**
- [ ] Brain can issue a `shell` action; `POST /exec` runs it in the container and returns `{ok, exit_code, stdout, stderr}`.
- [ ] The shell result (exit + truncated stdout/stderr) threads into HISTORY so the Brain sees the output on the next step.
- [ ] Liveness: default 30s timeout, Brain-settable `timeout` clamped [1s, 300s]; output truncated ~4 KB — a hung command cannot freeze the loop.
- [ ] The Brain prompt teaches tier-routing (prefer shell for OS/CLI; vision for GUI-only) + non-interactive discipline (flags/pipes/heredocs; no REPLs via `/exec`).
- [ ] Deterministic `test_shell.py` passes (echo → stdout + exit 0; failing cmd → non-zero exit; a hang is killed at the timeout).
- [ ] An ADR captures the effector-hierarchy so future channels inherit it.
- [ ] Sandbox boundary preserved (container-only; no host mounts/socket; host exec out of scope).
- [ ] Localized docs updated (architecture-overview, agent-loop-flow).

---

## **SCOPE**

### In Scope
- New `POST /exec` endpoint in the Screen server (`shell=True`, container-only) with timeout + output truncation; response `{ok, exit_code, stdout, stderr}`.
- Optional `stdin` field on `/exec` (Level 2) — pre-feed *predictable* input without vision.
- `shell` action in the Brain vocabulary (`VALID_ACTIONS` + JSON schema + prompt guidance).
- Loop dispatch for `shell`; thread the result (exit + truncated stdout/stderr) into HISTORY.
- Tier-routing rule + non-interactive discipline in `SYSTEM_PROMPT`.
- Deterministic `screen/test_shell.py` (mirrors `test_hands.py` — a test *mechanism*, not a QA standard).
- **ADR**: the effector-hierarchy architecture (Tier 1/2/3, vision-as-fallback, sandbox boundary, future channels inherit).
- Update localized docs (architecture-overview.md, agent-loop-flow.md).

### Out of Scope
- **Async/background `/exec` + polling** — deferred; its payoff is gated behind loop concurrency BRYES doesn't have (single sequential loop). Design `/exec` so `background:true` + a poll endpoint is a clean *additive* upgrade later.
- **Level 3 interactive PTY session** (REPLs, ssh, unpredictable prompts) — use **vision-driving xterm** instead (already possible; the container ships xterm).
- **Host-level command execution** — the sandbox boundary is deliberate; host exec, if ever, gets its own guardrails as a separate decision.
- **Tier 1 API/MCP channels** — future; this ADR names the pattern, doesn't build them.
- **Per-surface persona routing logic** (e.g. "use WhatsApp like a human") — lands with the persona surface that needs it.
- **Command allow/deny list** — Docker isolation is the boundary; an allowlist adds friction + false safety here.

---

## **CONFIRMED DECISIONS**
*These decisions were collected during investigation — both **asked-and-confirmed** by [USER-NAME] AND **written-through** (Zone A/B decisions made by the agent with reasoning, per [What to Surface](../procedures/wait-options.md#what-to-surface)). The reasons serve as the analysis record.*

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| 1 | Endpoint shape | **New `POST /exec`** (separate from `/action`) | `/action` injects GUI input at the display; `/exec` runs a process — different tiers. Separation keeps the effector model clean. |
| 2 | Command execution model | **Full shell** (`subprocess.run(cmd, shell=True)`) | The point is terminal-like usage (pipes, `&&`, redirects, globs). Safety comes from the container boundary, not from crippling the command. |
| 3 | Safety boundary | **Container-only, Docker isolation, no allowlist**; host exec out of scope | The server runs only inside a disposable container with no volume mounts, no docker socket, and no API key (host-side) → worst case a shell breaks its own container. Docker IS the guardrail. |
| 4 | How the shell result reaches the Brain | **Thread exit + truncated stdout/stderr into HISTORY** | A GUI action's feedback is the next screenshot; a shell command's output is invisible on screen, so it must be fed back as text. HISTORY is the existing "what happened" channel — reuse it. |
| 5 | Interactivity model | **Level 1 one-shot non-interactive + optional `stdin` (Level 2)**; interactive → vision-xterm (Level 3, not built); async deferred | Most interactivity is avoidable via flags/pipes/heredocs; genuinely-interactive terminal work already has an effector (vision-driving xterm). Full PTY session is high-cost for a case vision covers. |
| 6 | Timeout / liveness | **Default 30s; Brain-settable `timeout` clamped [1s, 300s]; +~4 KB output truncation** | Timeout is the exec channel's ONLY recovery valve — a blocking synchronous call freezes the whole loop with the Brain locked out; the timeout converts an unrecoverable freeze into a visible error. Brain extends it for installs; the clamp bounds worst-case freeze. Truncation bounds output *size* (orthogonal to time). |
| 7 | Routing intelligence now | **Concise tier rule + non-interactive discipline in the prompt**; defer persona logic | No persona surface exists yet (YAGNI). The tier rule makes the Brain reach for shell first; persona logic lands with the surface that needs it. |
| 8 | `stdin` pre-feed field (Level 2) | **Include** (optional `stdin` on `/exec`) | ~5 lines; lets the Brain answer *predictable* prompts without falling back to vision. Small, real payoff. *(Flagged in Early Review — veto if you'd rather omit.)* |
| 9 | Async `/exec` | **Defer**; design for a clean additive upgrade | Async's payoff (stay in control during a wait) is gated behind loop concurrency BRYES lacks — a single sequential loop just polls instead of blocks for the same wall-clock. Revisit when the loop goes concurrent or long jobs get frequent. |

---

## **SOLUTION**

### Architecture Overview

BRYES gains a second **effector channel** alongside vision. The Brain (decider) now routes each intent to the highest-available tier:

- **Tier 1 — API / MCP** (future): structured, deterministic, lossless. Named by the ADR, not built here.
- **Tier 2 — Shell / CLI** (this plan): the Brain issues a `shell` action → the loop POSTs to a new `/exec` endpoint → the command runs **inside the sandboxed Screen container** → `{ok, exit_code, stdout, stderr}` returns → the loop threads the result into HISTORY so the Brain reads it next step.
- **Tier 3 — Vision (Eyes + Hands)** (existing): lossy, expensive fallback for GUI-only surfaces, and the effector for genuinely-interactive terminals (vision-driving `xterm`).

**Routing rule** (Brain prompt): use the highest tier available — shell for OS/file/CLI/network, vision for GUI-only. The three code touchpoints mirror last session's `wait`/`screenshot` addition — a Screen endpoint, a loop dispatch branch, a Brain vocabulary entry — added in lockstep.

### Component 1: Screen server — `/exec` endpoint
- **Purpose**: run a non-interactive shell command inside the container and return structured output, with a liveness timeout + output truncation so a hung/long command can't freeze the caller.
- **Key Files**: [screen/server/app.py](../screen/server/app.py) — new `POST /exec`

### Component 2: Brain — `shell` vocabulary + tier routing
- **Purpose**: teach the Brain the `shell` action (schema + `VALID_ACTIONS`), the tier-routing rule (prefer shell over vision for OS/CLI), and non-interactive discipline (flags/pipes/heredocs; no REPLs; background long jobs).
- **Key Files**: [brain/client.py](../brain/client.py) — `SYSTEM_PROMPT` + `VALID_ACTIONS` + JSON schema

### Component 3: Loop — `shell` dispatch + history feedback
- **Purpose**: when the Brain returns `{action:"shell", command, timeout?, stdin?}`, POST to `/exec`, then append the result (exit + truncated stdout/stderr) to HISTORY as the step's `did` string — the shell channel's feedback path (vision uses the screenshot; shell uses HISTORY).
- **Key Files**: [agent/loop.py](../agent/loop.py) — new `shell` branch + a small `exec_cmd()` helper

### Component 4: Regression test
- **Purpose**: deterministic, model-free verification of the `/exec` channel (a test *mechanism*, not a QA standard).
- **Key Files**: `screen/test_shell.py` (new) — mirrors [screen/test_hands.py](../screen/test_hands.py)

<!-- OPTIONAL SECTION B: Include when changing data/process flow, API changes -->
### System Flow Diagrams

**Current State (a vision action — feedback is the next screenshot):**
```mermaid
sequenceDiagram
    participant Brain
    participant Loop
    participant Eyes
    participant Screen
    Loop->>Screen: GET /screenshot
    Loop->>Eyes: describe(shot)
    Loop->>Brain: decide(goal, observation, history)
    Brain-->>Loop: {action: click, target}
    Loop->>Eyes: locate(target)
    Eyes-->>Loop: (x, y)
    Loop->>Screen: POST /action {click, x, y}
    Note over Loop: feedback arrives as the NEXT screenshot
```

**End Result (a shell action — feedback threads through HISTORY, no Eyes):**
```mermaid
sequenceDiagram
    participant Brain
    participant Loop
    participant Screen
    Loop->>Screen: GET /screenshot
    Loop->>Brain: decide(goal, observation, history)
    Brain-->>Loop: {action: shell, command, timeout?}
    Loop->>Screen: POST /exec {command, timeout}
    Screen->>Screen: subprocess.run(shell=True, timeout)
    Screen-->>Loop: {ok, exit_code, stdout, stderr}
    Loop->>Loop: history.append("ran 'cmd' -> exit 0; out: ...")
    Note over Loop,Brain: feedback is HISTORY (not the screenshot)
```

<!-- OPTIONAL SECTION C: Include when significant technical constraints exist -->
### Technical Considerations
- **Liveness is the exec channel's defining constraint**: a synchronous command blocks the whole loop with the Brain locked out (no re-decide until it returns). The timeout is the ONLY recovery valve — it converts an unrecoverable freeze into a `timed_out` result the Brain reads next step. Default 30s; Brain-settable clamped [1s, 300s]; the clamp bounds the worst-case freeze.
- **Sandbox boundary (verified)**: the Screen container has no volume mounts, no docker socket, and the OpenRouter key is host-side (brain/eyes run on the host). A shell inside `/exec` can, at worst, disrupt its own disposable container — it cannot read host files, secrets, or escape. This is what makes `shell=True` + no-allowlist safe here. Host-level exec would break this → out of scope.
- **Non-interactive discipline**: `/exec` runs to completion and cannot answer a mid-run prompt. The Brain uses non-interactive flags (`-y`, `DEBIAN_FRONTEND=noninteractive`), pipes/heredocs, and the optional `stdin` field for *predictable* input — and falls back to vision-driving `xterm` for genuinely-interactive terminals (REPLs, ssh).
- **Output truncation** (~4 KB per stream, head+tail): unbounded stdout would blow the Brain's context and cost. Orthogonal to the timeout (bounds size, not time).
- **Async-ready shape**: `/exec` is synchronous now but structured so a future `background:true` → `job_id` + `GET /exec/{job_id}` poll is an *additive* branch, not a rewrite.
- **DISPLAY env**: shell commands don't need the X display; `/exec` runs in the container's normal env (the `$DISPLAY` wiring stays specific to `/action`/`/screenshot`).

<!-- OPTIONAL SECTION F: Include for brainstorming/decision tasks, multiple viable approaches -->
### Solution Options & Evaluation

#### Solution Options

| # | Solution | Description |
|---|----------|-------------|
| 1 | Vision-only (status quo) | Drive everything through screenshots + clicks, including a terminal GUI, for all tasks. |
| 2 | **Tiered effectors + shell channel** *(chosen)* | Brain routes to a direct shell channel for OS/CLI, vision as fallback. |
| 3 | API/MCP-only direct tools | Give the Brain function-calling tools for services; no general shell. |
| 4 | Full MCP tool-use rewrite | Rebuild the loop as an MCP client where every capability (incl. vision) is an MCP tool. |
| 5 | **Shell via new `/exec`** *(chosen shape)* | Dedicated endpoint for command execution, separate from `/action`. |
| 6 | Shell as a `type` in `/action` | Fold shell into the existing GUI-input endpoint. |
| 7 | **Sync `/exec` + timeout** *(chosen)* | Block until done/timeout; simplest liveness model. |
| 8 | Async/background `/exec` + poll | Non-blocking job model; richer but needs loop concurrency to pay off. |

#### Evaluation

| Solution | Pros | Cons |
|----------|------|------|
| Tiered effectors + shell (chosen) | Direct/deterministic for OS-CLI; vision reserved for GUI-only; extends the proven "harness > model" thesis; incremental (one channel now, pattern for more) | Brain must learn routing; adds a second effector surface |
| Vision-only (status quo) | No new code; one uniform effector | Lossy/expensive/fragile where a clean CLI exists; the self-imposed harness limit the whole project is trying to escape |
| API/MCP-only | Most structured & lossless | Doesn't cover general OS/file/CLI work; many tasks have no API; bigger lift than shell |
| Full MCP rewrite | Clean long-term tool-use model | Large rewrite; over-scoped for adding one channel now |
| Async `/exec` | Never freezes; unifies durations | Job machinery + poll overhead; payoff gated behind loop concurrency BRYES lacks |

#### Selected Approach
- **Chosen**: Tiered effectors with a synchronous, container-scoped `/exec` shell channel (options 2 + 5 + 7); vision remains the Tier-3 fallback.
- **Rationale**: the smallest step that reframes BRYES as a tool-using agent (vision = one tool), delivering immediate deterministic capability for OS/CLI tasks, keeping the sandbox as the safety boundary, and setting the inheritable pattern for future channels — without the over-scope of an MCP rewrite or the premature complexity of async (which needs loop concurrency BRYES doesn't have).

<!-- OPTIONAL SECTION G: Include when task produces an architecture decision record -->
### ADR Output
*When this section is confirmed, the procedure creates a separate ADR file using the [ADR Template](../templates/adr-template.md).*

- **ADR File**: [docs/adr/2026-07-15-effector-hierarchy.md](../docs/adr/2026-07-15-effector-hierarchy.md)
- **Decision Summary**: BRYES adopts a tiered effector model — the Brain routes each intent to the highest-available channel (Tier 1 API/MCP → Tier 2 shell → Tier 3 vision), demoting vision from the only effector to the GUI-only/interactive fallback; the shell channel is the first Tier-2 instance and future channels (http/mcp/email/phone) inherit the pattern.

---

## **IMPLEMENTATION PHASES**

### Phase 1: Screen server — `/exec` endpoint + regression test
- [ ] **Step 1.1**: Add `POST /exec` to the Screen server
  - **Action**: implement the Tier-2 shell channel endpoint.
  - **Implementation**: in [screen/server/app.py](../screen/server/app.py), add `POST /exec`. Parse JSON `{command (str, required), timeout (optional int), stdin (optional str)}`; 400 if no `command`. Clamp `t = max(1, min(int(timeout or 30), 300))`. Run `subprocess.run(command, shell=True, capture_output=True, text=True, timeout=t, input=stdin)`. Truncate `stdout`/`stderr` to ~4 KB each (head+tail with an elision marker via a small `_clip()` helper). Return `{ok: rc==0, exit_code: rc, stdout, stderr}` (200). On `subprocess.TimeoutExpired`: return `{ok: false, exit_code: null, stdout: "", stderr: "timed out after {t}s", timed_out: true}` (200 — a handled result, not a 500). Do not force `$DISPLAY` (shell runs in the container's normal env).
  - **Testing**: `cd screen && docker compose up -d --build` (container must pick up the new code), then curl: `echo hello` → `{ok:true, exit_code:0, stdout:"hello\n"}`; `sh -c 'exit 3'` → `exit_code:3, ok:false`; `sleep 5` with `timeout:1` → `timed_out:true` in ~1s; body without `command` → 400.
  - **Success Criteria**: all four curls behave; endpoint returns structured JSON; a hang is killed at the timeout.

- [ ] **Step 1.2**: Deterministic `screen/test_shell.py`
  - **Action**: model-free regression test for `/exec` (a test *mechanism*, mirroring `test_hands.py`).
  - **Implementation**: create [screen/test_shell.py](../screen/test_shell.py) with checks: echo → stdout + exit 0; `sh -c 'exit 3'` → exit 3 + `ok:false`; missing `command` → 400; hang (`sleep 5`, `timeout:1`) → `timed_out:true` within ~2s; `stdin` pre-feed (`cat`, `stdin:"hi"`) → stdout `"hi"`; truncation (emit >20 KB) → stdout capped ~4 KB. ASCII markers only (`PASS:`/`FAIL:` — no emoji, cp1252). Exit non-zero on any failure.
  - **Testing**: `python screen/test_shell.py` against the running container — all green.
  - **Success Criteria**: every check prints `PASS:`; script exits 0.

### Phase 2: Brain — `shell` vocabulary + tier routing
- [ ] **Step 2.1**: Extend `SYSTEM_PROMPT` + `VALID_ACTIONS` + JSON schema
  - **Action**: teach the Brain the `shell` action, the tier-routing rule, and non-interactive discipline.
  - **Implementation**: in [brain/client.py](../brain/client.py): add `"shell"` to `VALID_ACTIONS`; add it to the action union in the JSON schema plus `command` and `timeout` fields (and note optional `stdin`). Add a prompt block: **EFFECTOR TIERS** — prefer `shell` for OS/file/CLI/network tasks; use vision (click/type/…) only for GUI-only surfaces; a genuinely-interactive terminal (REPL/ssh/prompt) → open `xterm` and drive it with vision. **NON-INTERACTIVE DISCIPLINE** — `shell` runs to completion and can't answer a mid-run prompt: use non-interactive flags (`-y`, `DEBIAN_FRONTEND=noninteractive`), pipes/heredocs, or the optional `stdin` field for predictable input; for a slow-but-finite command (install/download) set `timeout` up to 300; background a very-long job with `&` and poll with `wait`.
  - **Testing**: one `decide()` probe — goal "What is the Linux kernel version of this machine?" returns `{action:"shell", command:"uname -r"}` (or equivalent), not a vision action; schema validates.
  - **Success Criteria**: the Brain emits a valid `shell` action for a CLI-appropriate goal.

### Phase 3: Loop — `shell` dispatch + history feedback
- [ ] **Step 3.1**: Add `exec_cmd()` + the `shell` branch
  - **Action**: wire the shell action into the loop, threading output back through HISTORY.
  - **Implementation**: in [agent/loop.py](../agent/loop.py): add an `exec_cmd(payload)` helper (POST `/exec`, like `hands()`, returns parsed JSON). Add `elif act == "shell":` — build `{command, timeout?, stdin?}` from the action, call `exec_cmd`, then set `did = "ran '<cmd>' -> exit <code>; out: <stdout>"` (append `; err: <stderr>` when non-zero or timed out), and `history.append(did)` so the Brain reads the output next step. `runlog.record` the exec.
  - **Testing**: covered live in Phase 4.
  - **Success Criteria**: the loop dispatches `shell`, and the result string (with output) appears in HISTORY and the transcript.

### Phase 4: Live end-to-end verification
- [ ] **Step 4.1**: Run shell-routed goals through the loop
  - **Action**: prove the Brain routes to shell and consumes the output — no vision.
  - **Implementation**: `run("Report the Linux kernel version of this computer.", tag="shell-kernel")` — expect the Brain to issue `shell uname -r`, the loop to exec it, the result to thread into HISTORY, and the Brain to read it and `done` with the version. Then a two-step one: `run("How many .py files are under /root?", tag="shell-count")` (→ `find … | wc -l`). Inspect transcripts under `artifacts/runs/`.
  - **Testing**: observe both runs — shell action fired, exit 0, output captured + consumed, `done` with the right answer.
  - **Success Criteria**: both goals complete via the shell channel with output correctly fed back; no vision fallback needed.

### Phase 5: Docs update
- [ ] **Step 5.1**: Refresh the localized docs
  - **Action**: reflect the new channel + tier model in the docs.
  - **Implementation**: [docs/architecture-overview.md](../docs/architecture-overview.md) — add the effector-tier model, the `/exec` endpoint, the `shell` action, and a link to the ADR. [docs/agent-loop-flow.md](../docs/agent-loop-flow.md) — add the `shell` action path and the "feedback via HISTORY, not the screenshot" note. [screen/README.md](../screen/README.md) — add `POST /exec` to the API list (alongside `/screenshot`, `/action`, `/pointer`).
  - **Testing**: re-read for accuracy; links resolve.
  - **Success Criteria**: all three docs describe the shell channel; the ADR is linked. *(Orientation-map indexing of the new ADR is handled by `/map-orientation` at wrap-up.)*

---

## **EXECUTION LOG**
**Execution Protocol for AI**:
I have to use this document as my **ONLY** source of truth to execute and track the plan steps iteratively. I should **NOT** use additional tools like ToDos because it lacks the context of what should I do. Everytime I want to implement a step I have to check the reference to the original step plan above. Everytime a step has been finished I need to go back to this document to log what was done.
*In other words*:
- I have to make this document as the source of truth for the implementation phase on what I have worked on and what I will be working
- The original plan must be fully in my context, therefore, I have to make sure I loaded the **Plan File** before executing any task and read carefully the reference to the original step
- I have to do the implementation by doing it in order per step THEN, I ALWAYS have to fill the step log rightly after

**Definition of Done (applies to ALL steps)**:
- ✅ **Code Quality**: Code compiles/runs without errors
- ✅ **Testing**: Tests written and passing
- ✅ **Logged**: Implementation and testing logged below
- 🚫 **Blocked**: Get input from [USER-NAME] before assuming

### Phase 1:
- [x] **Step 1.1**: Add `POST /exec` to the Screen server
  - **Implementation Log**: In `screen/server/app.py`: updated the module docstring (added `/exec`); added `_MAX_OUT=4096` + a `_clip()` head+tail truncation helper; added `POST /exec` — validates non-empty `command` (400 else), clamps `timeout` to [1,300] (default 30), runs `subprocess.run(command, shell=True, capture_output=True, text=True, timeout=t, input=stdin)`, truncates stdout/stderr via `_clip`, returns `{ok, exit_code, stdout, stderr}` (200); `TimeoutExpired` → `{ok:false, exit_code:null, stdout:"", stderr:"timed out after Ns", timed_out:true}` (200). No forced `$DISPLAY` (plain container env).
  - **Testing Log**: `docker compose up -d --build` (container picked up new code), health OK, then 4 curls: (1) `echo hello` → `{ok:true, exit_code:0, stdout:"hello\n"}` ✓; (2) `sh -c 'exit 3'` → `{exit_code:3, ok:false}` ✓; (3) `sleep 5` w/ `timeout:1` → `{timed_out:true, stderr:"timed out after 1s"}` in **1.06s** ✓; (4) `{}` (no command) → **HTTP 400** ✓.
  - **Success Criteria**: PASS — all four curls behave; structured JSON; hang killed at the timeout.
  - **Tech Debts**: None.
  - **Result**: Endpoint live and verified against the running container.

- [x] **Step 1.2**: Deterministic `screen/test_shell.py`
  - **Implementation Log**: Created `screen/test_shell.py` (stdlib urllib, mirrors `test_hands.py`): a `_exec()` POST helper + a `check()` reporter (ASCII `PASS:`/`FAIL:`, no emoji), 6 model-free checks — echo (stdout+exit0), non-zero exit, missing-command→400, hang killed at timeout (<3s), stdin pre-feed via `cat`, oversized-stdout clipped (`yes x | head -c 20000` → stdout < 8000 chars). Exits non-zero on any failure.
  - **Testing Log**: `python screen/test_shell.py` against the running container → all 6 `PASS:`, final "PASS: all shell-channel checks green", exit=0.
  - **Success Criteria**: PASS — every check prints `PASS:`; script exits 0.
  - **Tech Debts**: None. (App-level command *behavior* is covered by the live Phase-4 run; this test asserts the channel contract deterministically.)
  - **Result**: The `/exec` channel now has a deterministic regression gate.

### Phase 2:
- [x] **Step 2.1**: Extend `SYSTEM_PROMPT` + `VALID_ACTIONS` + JSON schema
  - **Implementation Log**: In `brain/client.py`: (1) rewrote the intro so the Brain has two channels (SHELL + VISION) and picks the most direct; (2) added a `CHOOSE THE RIGHT CHANNEL (shell vs vision)` rule (prefer shell for files/system/networking/text/counting/installs; vision for GUI-only; interactive terminals → vision-drive xterm); (3) added a `SHELL runs a NON-INTERACTIVE command...` rule (flags/pipes/heredocs/`stdin`; `timeout` up to 300 for finite-long; background very-long with `&`); (4) added `"shell"` to the PICK-THE-RIGHT-ACTION list, the JSON-schema action union, and `VALID_ACTIONS`; (5) added `command`/`timeout`/`stdin` to the JSON schema.
  - **Testing Log**: live `decide("What is the Linux kernel version of this machine?", "A Linux desktop with a web browser open. No terminal window is visible.", [])` → `{"action":"shell","command":"uname -r"}` with a thought explicitly reasoning "most direct way… use shell directly without needing to open a GUI terminal." Schema validated (action ∈ VALID_ACTIONS).
  - **Success Criteria**: PASS — the Brain emits a valid `shell` action for a CLI-appropriate goal and routes away from vision.
  - **Tech Debts**: None.
  - **Result**: Brain vocabulary + tier routing in place and behaving.

### Phase 3:
- [x] **Step 3.1**: Add `exec_cmd()` + the `shell` branch
  - **Implementation Log**: In `agent/loop.py`: added `exec_cmd(payload)` (POST `/exec`, `runlog.record("exec", ...)`, returns parsed `{ok, exit_code, stdout, stderr, timed_out?}`); extended the console `detail` line to include `action.get("command")`; added `elif act == "shell":` — builds `{command, timeout?, stdin?}` from the action, calls `exec_cmd`, sets `did = "ran shell '<cmd>' -> exit <code>; out: <stdout|(empty)>"`, appends `; err: <stderr>` on failure and `[TIMED OUT]` on timeout, then `history.append(did)` (existing line) so the Brain reads the output next step.
  - **Testing Log**: `python -m py_compile agent/loop.py brain/client.py screen/server/app.py` → all compile OK. Runtime behavior verified live in Step 4.1.
  - **Success Criteria**: PASS (compile) — runtime confirmed in Phase 4.
  - **Tech Debts**: None.
  - **Result**: Loop dispatches `shell` and threads the result into HISTORY.

- [x] **Step 4.1**: Run shell-routed goals through the loop
  - **Implementation Log**: Ran two live goals through `agent.loop.run` against the running container + real Brain/Eyes.
  - **Testing Log**:
    - `run("Report the Linux kernel version of this computer.", tag="shell-kernel")` → **done in 2 steps**. Step 1: Brain chose `shell uname -r` (explicitly ignored the on-screen browser as irrelevant); loop threaded `ran shell 'uname -r' -> exit 0; out: 6.6.87.2-microsoft-standard-WSL2` into HISTORY; Step 2: Brain read HISTORY and `done` with the version. Transcript: `artifacts/runs/20260715-102633-shell-kernel`.
    - `run("How many .py files are under /root?", tag="shell-count")` → **done in 2 steps**. Brain issued `shell find /root -name "*.py" | wc -l` (**a pipe** — confirms `shell=True`); result `... -> exit 0; out: 0` threaded into HISTORY; Brain read `0` and `done`. Transcript: `artifacts/runs/20260715-102721-shell-count`.
  - **Success Criteria**: PASS — both goals completed via the shell channel, output correctly fed back through HISTORY and consumed; no vision fallback needed.
  - **Tech Debts**: None.
  - **Result**: End-to-end shell effector proven live, including a piped command.

### Phase 5:
- [x] **Step 5.1**: Refresh the localized docs
  - **Implementation Log**: (1) `docs/architecture-overview.md` — rewrote the now-false "Vision-first — no shell channel" fact into an **Effector tiers** bullet (Tier 1 API/MCP future · Tier 2 shell `/exec` · Tier 3 vision), added `shell` to the Brain action set, `/exec`+`test_shell.py` to the repo layout, "shell" to the Screen row + intro, ADR-001 link, tags/date. (2) `docs/agent-loop-flow.md` — added `command?`/`timeout?` to the decide schema, a new feed-table row 6 (`exec_cmd` → `/exec`), `shell` to the one-step narration, and a "**Shell is the exception to Seam B**" note (its history carries real exit+stdout, not an unverified attempt); tags/date. (3) `screen/README.md` — added `/exec` to the API table + a curl example, `test_shell.py` to the test list, intro + Flask-API + heading tweaks.
  - **Testing Log**: re-read all three; the false "no shell channel" claim is gone; links (`adr/2026-07-15-effector-hierarchy.md`) resolve; content matches the shipped code.
  - **Success Criteria**: PASS — all three docs describe the shell channel; the ADR is linked. (Orientation-map ADR indexing deferred to `/map-orientation` at wrap-up.)
  - **Tech Debts**: None.
  - **Result**: Docs are consistent with the implemented effector-tier reality.

---

## **QUALITY REVIEW**
*Filled by procedure Step 16 (delegated to `/analyze-code-quality` in embedded mode) after all execution phases are complete. **Static** review — answers "is the code clean?".*

- **Scope**: `screen/server/app.py`, `brain/client.py`, `agent/loop.py`, `screen/test_shell.py` (code); docs (`architecture-overview.md`, `agent-loop-flow.md`, `screen/README.md`, `docs/adr/2026-07-15-effector-hierarchy.md`). Reconciled against `git status --short` — matches the Execution Log exactly; no stray/user files.
- **Quality Standard**: no `quality-standard.md` in BRYES → freeform review (correctness, robustness, error-handling, security, consistency).
- **Findings**: 1 minor (robustness) — `/exec` ran `subprocess.run(..., text=True)` without `errors=`, so non-UTF-8 output (e.g. `cat` a binary) would raise `UnicodeDecodeError` → unhandled HTTP 500. Everything else clean (`shell=True` by-design/sandboxed; timeout clamp, truncation, stdin correct; loop branch + `exec_cmd` consistent with existing style; test mirrors `test_hands.py`).
- **Fixed**: Added `errors="replace"` to the `subprocess.run` call. Verified: rebuilt container, `head -c 200 /dev/urandom` via `/exec` → **HTTP 200** (no crash); `test_shell.py` → all 6 checks green, exit 0.

---

## **FINAL INTEGRATION TEST**
*Filled by procedure Step 17 after Quality Review is resolved. **Runtime** verification through the qa/ instrument — answers "does it actually work end-to-end?".*

- **Scope**: Screen server (`/exec`), Brain vocab, loop `shell` dispatch.
- **qa/ Status**: Missing by design — BRYES uses **deterministic test scripts + live loop runs** as its runtime mechanism (Alvi declined a formal qa/ instrument for this project on 2026-07-14). So `/setup-qa-instrument` is intentionally NOT offered; runtime was verified inline this session.
- **Playbooks Run**: N/A — no qa/ playbooks. Equivalent runtime coverage below.
- **R/I/A/O Results**: Runtime verification performed inline and green:
  - **Endpoint**: 4 curl checks (echo/exit-3/timeout/400) + binary-output check (HTTP 200, no crash) — all pass.
  - **Deterministic gate**: `screen/test_shell.py` — 6 model-free checks, all `PASS:`, exit 0.
  - **Live end-to-end**: 2 loop runs (`uname -r`; `find /root -name "*.py" | wc -l`) — both `done` in 2 steps via the shell channel, output threaded through HISTORY, no vision fallback.
- **Findings**: No runtime failures — the shell channel works end-to-end.
- **Fixed**: N/A (the one static finding was fixed under Quality Review and re-verified).

---

## **POST-COMPLETION**
After all phases are executed, logged, and both **Quality Review** + **Final Integration Test** are filled, move this plan to `plans/completed/`:
`mkdir -p ./plans/completed && mv ./plans/[this-file].md ./plans/completed/[this-file].md`
