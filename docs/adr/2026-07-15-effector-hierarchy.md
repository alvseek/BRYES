# ADR-001: Effector Hierarchy — Tiered Channels with Vision as Fallback

**Date**: 2026-07-15

**Status**: Accepted

---

## Problem

BRYES began as a pure **vision** agent: every action goes through screenshot → describe → decide → locate → click. Vision is the lossiest, most expensive, most fragile channel — the project's own history shows perception, not the model, is where reliability is lost. Driving a task through screenshots-and-clicks when it has a clean CLI or API is strictly worse (more failure modes, more cost, slower). BRYES needs a way to use **direct, deterministic** channels when they exist, and reserve vision for surfaces that genuinely require it.

---

## Decision

**We decided to**: adopt a **tiered effector model** — the Brain routes each intent to the highest-available channel, and vision is demoted from *the only* effector to *the fallback* effector.

The Brain gets a toolbelt instead of a single tool. Per intent it picks:

- **Tier 1 — API / MCP** (future): structured, deterministic, lossless. For anything with a programmatic interface (email, calendar, own services). Named here; not built yet.
- **Tier 2 — Shell / CLI**: run commands directly for OS / file / CLI / network tasks. The first Tier-2 instance is a `POST /exec` endpoint on the Screen server, sandboxed inside the container.
- **Tier 3 — Vision (Eyes + Hands)**: the fallback for GUI-only surfaces, for surfaces where being human-indistinguishable matters (e.g. a persona app like WhatsApp), and for genuinely-interactive terminals (vision-driving `xterm`).

**Why we chose this:**
- Extends BRYES's proven thesis — *the harness, not the model, is where capability lives*. More/better effectors beat a smarter Brain squinting at pixels.
- Vision stays available for what only vision can do, so nothing is lost — only the *default* changes.
- Incremental: one channel (shell) now, a clear pattern that future channels (http, mcp, email, phone) inherit — no rewrite.

---

## What to Build (Requirements)

**Core Requirements:**
- A `shell` action in the Brain's vocabulary and a `POST /exec` endpoint that runs a **non-interactive** command inside the sandboxed Screen container and returns `{ok, exit_code, stdout, stderr}`.
- A **routing rule** in the Brain prompt: use the highest tier available (shell for OS/CLI, vision for GUI-only), with non-interactive discipline (flags/pipes/heredocs; interactive terminals → vision-driving `xterm`).
- The shell result threads back through **HISTORY** (a shell command's output is invisible on screen, so text must carry the feedback — vision uses the screenshot).
- A **liveness guarantee**: a synchronous command can't freeze the loop indefinitely — a fixed-default, Brain-extendable, clamped timeout converts a hang into a recoverable result.
- The **sandbox is the safety boundary**: the shell runs only inside the container (no host mounts, no docker socket, no secrets); host-level execution is out of scope.

**Success Criteria:**
- The Brain completes an OS/CLI task via the shell channel with output correctly fed back — no vision fallback needed.
- A hung command is killed at the timeout and reported, never freezing the agent.
- Future channels can be added as new tiers/actions without changing this model.

---

## Alternatives Rejected

- **Vision-only (status quo)**: keeps the self-imposed harness limit the project is trying to escape — lossy/fragile/expensive wherever a clean CLI exists.
- **API/MCP-only direct tools**: doesn't cover general OS/file/CLI work, and many tasks have no API; a bigger lift than shell for less coverage.
- **Full MCP tool-use rewrite**: the right long-term shape but over-scoped for adding one channel now.
- **Shell folded into `/action`**: conflates GUI-input injection (Tier 3) with process execution (Tier 2) — muddies the effector model.
- **Async/background `/exec` from the start**: its payoff (stay in control during a wait) is gated behind loop concurrency BRYES doesn't have; a single sequential loop just polls instead of blocks for the same wall-clock. Deferred as a clean additive upgrade.
- **Level-3 interactive PTY session**: high-cost machinery for a case vision already covers (drive `xterm`).
- **Command allow/deny list**: adds friction + false safety when Docker isolation is already the boundary.

---

**Full context**: [High Wizard plan](../../plans/2026-07-15-bryes-shell-effector-channel.md)
