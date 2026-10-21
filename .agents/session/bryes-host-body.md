# BRYES — The Host Body

Driving the real Windows desktop instead of the disposable container: the body, the two gates,
the three harness rules an accident bought, and the live proof.

---

### [2026-10-21 11.50] (agent: software-architect) — THE HAND THAT CLICKS: A HOST BODY, A REAL ACCIDENT, AND THE RULES IT BOUGHT 🖱️🚧🧭

- **Context**: Alvi asked for the body BRYES never had: *"add bypass sandbox from docker feature, and directly operate on the working operating system. using QW or HW?"* Unreal lives outside the container, so the project's central capability had no surface where the actual work happens. Session ran the full arc: High Wizard plan, implementation, a live accident on his real desktop, the rewrite, and the operator doc.
- **Discussion**:
  - **The question I got wrong first.** I read QW/HW as input mechanisms and answered a question nobody asked. *"wait, something is wrong with your memory if you don't know QW and HW"* — they are **Quick Wizard** and **High Wizard**, terms from his own framework that were already in my loaded context. The correction cost one turn and produced the plan.
  - **The plan's four rounds**: reach (explicit `device="windows"` **and** `BRYES_ALLOW_HOST=1`, never in the catalog), capability (full verbs, `shell` behind its own switch), mechanism (`pyautogui`, after measuring it and `pynput` across both monitors), and capture (whole virtual desktop, so image space and screen space are one frame).
  - **He pushed back on my third harness rule** and was right: *"what the agent touches should be a sandbox instead, no other user, but killing a process that has not related to the task is a good rule (+ driving target a window the body started)"*. My rule was a per-probe promise standing in for a boundary that should be structural. Environment isolation is the real answer; the two ownership rules hold inside it too.
- **Key Interactions**: his `go` on each phase; the A/A and 1A/2C/B/A answers that closed every round; and the correction that turned three rules into two plus an architectural gap.
- **Issues Encountered**:
  - **The accident.** The first live probe targeted the largest window containing "Notepad" — which was **his own open document** — clicked into it, typed `bryes host body ok 12345` into it, copied its contents to the clipboard, and then killed the pid it had launched. Windows 11 Notepad is single-instance with tabs, so that pid *was* his editor: `-Force` skipped the save prompt and took at least two documents with it.
  - **Root causes, both now rules.** A title substring cannot tell two windows apart, and a pid from `Start-Process` on a single-instance app is not "my process". Neither was a code bug in the body; both were targeting and cleanup decided by a probe.
  - **Fixed by construction**: `WindowsDevice(hwnd=...)`, `windows_of_pid` / `top_window_of_pid` / `window_title`, a smoke that launches its own target, and a rect guard that refuses any pointer action outside the target window (`refusing to act at (x,y): outside the target window`).
  - **A second real defect found by quality review**: `_make_device` forwarded `window=None` to every constructor, so `run(device="linux")` and `POST /tasks {"device":"linux"}` were **broken**. No test saw it, because every test builds an instance or a fake. Fixed by dropping `None` kwargs, with regression checks.
  - **A third, found while preparing the live run**: `screenshot()` still cropped to the named window, so image coordinates were the window's, not the screen's — every click would have been off by the window offset. Driving now always captures the whole desktop; `grab_window()` is the cropped variant and `capture.py` calls it explicitly.
- **Outcomes**:
  - **Deliverables**: `devices/host_input.py` (the pyautogui adapter), `devices/windows.py` (verbs, live-origin translation, foreground guard, rect guard, two gates), `agent/loop.py` + task API (`device="windows"`, `window`), `devices/smoke_windows_drive.py`, four model-free suites, [ADR-009](../../docs/adr/2026-10-21-host-body-and-gates.md), the plan [2026-10-20-bryes-host-body.md](../../plans/2026-10-20-bryes-host-body.md), and the operator procedure [drive-the-desktop.md](../../docs/procedures/drive-the-desktop.md) served as `/drive-desktop`. Pushed as `634356b` and `fa53041`.
  - **Progress Made**: the body is live-proven three ways. A probe typed into a throwaway window and read the text back from its title; `run()` drove the same kind of target with a scripted brain (6 model calls avoided); the real-model smoke finished `status: done, steps: 2` with the target's title reading `bryes-probe-target|hello`. Measured: describe 10.6 s, decide 31.4 s, so the Brain dominates a host run.
  - **Tech Debts**:
    - **[new · the big one] Environment isolation is not built.** The gates are a stopgap while BRYES runs as Alvi's own user; a dedicated session is the structural fix, and it is priced in ADR-009 as a follow-up rather than claimed as done.
    - **[new] The real Unreal run has never happened.** A throwaway window stood in because the editor was closed. UIPI and Slate are both unmeasured on the actual target.
    - **[new] The API path targets a title**, so it is safe only when one window can match; the Python path with a handle is the safe one.
    - **[new] No element-level (UIA) path.** Unreal's tree is unmeasured; Aquazone's WinForms would benefit and is its own plan.
    - **[carry] No QA instrument in this repo**, so the plan ships with unit coverage and a manual smoke, no regression run.
    - **[carry] The 2026-08-23 set** (grid-form probe, Windows-MCP install, stale module READMEs, model-doc contradictions, runtime debts) is untouched.
  - **Next Steps**:
    - **The first real Unreal run**, which is the only claim in the procedure still unearned.
    - **Plan environment isolation**: a dedicated Windows user session, with the two gates kept as defence in depth.
    - **Ask Alvi whether the two Notepad documents came back**; the clipboard was overwritten and I have not touched Notepad since.
    - Hand the drive procedure to `agent-unreal`, or copy it into LSGI if that agent cannot read this repo.
- **Insights**:
  - **New Understanding**: the sandbox argument is not about safety alone. A desktop that holds only what the task created makes "did it click the right thing" a checkable question; under the current setup, every live step is production.
  - **Pattern Recognition**: `a3c7f8e2` (verify the reading) failed in its purest form. I did not silently auto-correct — I surfaced a *wrong* reading while the right one sat in loaded memory. A house term outranks an industry guess, and checking costs one grep.
  - **Improvement Areas**: I ran a live probe against the real desktop without pinning the target first. The rules that followed are correct, but the sequence was backwards: prove isolation, then act.
- **Promotions**:
  → Promoted to [ADR-009](../../docs/adr/2026-10-21-host-body-and-gates.md) — the decision, the gates, what they do not solve, and the three harness rules.
  → Promoted to [docs/procedures/drive-the-desktop.md](../../docs/procedures/drive-the-desktop.md) — how another agent operates an application, served as `/drive-desktop`.
  → Promoted to [README](../../README.md), [AGENTS](../../AGENTS.md), [architecture-overview](../../docs/architecture-overview.md) and the orientation map — the body and its two environment variables, where humans and agents enter.
