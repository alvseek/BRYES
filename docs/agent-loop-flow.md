---
project: BRYES
title: Agent Loop — Wiring & Data Flow
updated: 2026-07-13
doc_type: flow-diagram
tags: [loop, data-flow, wiring, describe, decide, locate, verify, phase-5, post-mortem]
---

# BRYES — Agent Loop: Wiring & Data Flow

**What this doc is:** the *flow* view of BRYES — who is connected to whom, over what
transport, and exactly what each piece is fed and emits each step. It complements
[architecture-overview.md](architecture-overview.md), which is the *structural* view
(what the pieces are, model slugs, coordinate convention). For those static facts,
read that; for "how does one step actually move through the system, and where does it
break," read this.

It closes with the **1024 clear-loop post-mortem** — the concrete Phase-4 failure that
motivates Phase 5 — traced through the two seams this flow exposes.

---

## 1. How the four pieces connect

Everything fans through **one orchestrator**: [`agent/loop.py`](../agent/loop.py)
`run(goal)`. The four pieces **never call each other** — the loop calls each in turn
and carries the data between them. There is no peer-to-peer wiring to reason about;
there is only the loop.

Two transports, two homes:

| Piece | Home | Transport | Entry point |
|---|---|---|---|
| **Screen** | local Docker container | HTTP `:8000` | `GET /screenshot` |
| **Hands** | *same* container (not a separate service) | HTTP `:8000` | `POST /action` (runs `xdotool`) |
| **Eyes** | rented, OpenRouter — Qwen2.5-VL-72B (`describe`) + UI-TARS-1.5-7B (`locate`) | HTTPS | `describe()`, `locate()` |
| **Brain** | rented, OpenRouter (DeepSeek V4) | HTTPS | `decide()` |

```mermaid
graph TD
    Loop["agent/loop.py — run(goal)<br/>the only orchestrator"]

    subgraph container["Docker container (:8000)"]
        Screen["Screen<br/>GET /screenshot -> PNG"]
        Hands["Hands<br/>POST /action -> xdotool"]
    end

    subgraph openrouter["OpenRouter (HTTPS)"]
        Eyes["Eyes<br/>describe(png): Qwen2.5-VL-72B<br/>locate(png, target): UI-TARS-1.5-7B"]
        Brain["Brain — DeepSeek V4<br/>decide(goal, obs, history)"]
    end

    Loop -->|"GET /screenshot"| Screen
    Screen -->|"PNG bytes"| Loop
    Loop -->|"describe: prompt + PNG"| Eyes
    Eyes -->|"text observation (<=512 tok)"| Loop
    Loop -->|"decide: prompt + goal + obs + history (TEXT only)"| Brain
    Brain -->|"JSON action"| Loop
    Loop -->|"locate: prompt + PNG + target"| Eyes
    Eyes -->|"pixel (x,y)"| Loop
    Loop -->|"POST /action {click x,y | type | key}"| Hands
```

**Key structural fact:** Screen and Hands share one container and one HTTP port; Eyes
and Brain share one OpenRouter key. Nothing runs *inside* anything else. The loop is
the single point where all four are stitched together.

---

## 2. What each piece is fed, and what it emits

This is the "what prompt / what feed flows to each other" answer. Per step:

| # | Call | Fed (input / prompt) | Emits | Source |
|---|---|---|---|---|
| 1 | `screenshot()` | — | PNG bytes | [screen/server/app.py](../screen/server/app.py) |
| 2 | `describe(png, focus?)` | `DESCRIBE_PROMPT` + optional **focus** + PNG → **Qwen2.5-VL-72B** | **text** report that separates the *live entry* from *history* (<=512 tok) | [eyes/client.py](../eyes/client.py) |
| 3 | `decide(goal, obs, history)` | `SYSTEM_PROMPT` + `{goal, observation, history}` — **text only**, Think High (`reasoning.effort=high`) | JSON `{thought, action, target?, text?, key?, focus?}` | [brain/client.py](../brain/client.py) |
| 4 | `locate(png, target)` | `GROUND_PROMPT(target)` + PNG → **UI-TARS-1.5-7B** | pixel `(x,y)` (+ diagnostics) | [eyes/client.py](../eyes/client.py) |
| 5 | `hands(payload)` | `{type: click, x, y}` / `{type: type, text}` / `{type: key, key}` | xdotool executes; `{ok}` | [screen/server/app.py](../screen/server/app.py) |

Notes that matter for Phase 5:

- **The Brain never sees the PNG.** Steps 2 and 3 are where pixels become text and the
  Brain reasons on that text alone. This is **Seam A** (below).
- **`describe` and `locate` are two separate Eyes calls on the *same* screenshot.**
  `describe` is a general report (step 2); `locate` is targeted grounding for the one
  element the Brain named (step 4). `locate` re-uses the screenshot taken at the *top*
  of the step, so grounding is consistent with what the Brain reasoned about.
- **The Brain names targets in words, not pixels** (`"the equals (=) button"`), because
  UI-TARS mislocates bare symbols. The Eyes turn that phrase into `(x,y)`.
- **(2026-07-12) The Brain now steers the Eyes and remembers outcomes.** `decide` returns
  an optional `focus` that the loop carries into the *next* `describe`; `history` now
  pairs each step's observation with the action taken; the Brain runs Think High. See
  *First Phase-5 cut* (§6).

---

## 3. One step, end to end

```mermaid
sequenceDiagram
    participant L as Loop
    participant S as Screen/Hands (:8000)
    participant E as Eyes (UI-TARS)
    participant B as Brain (DeepSeek)

    L->>S: GET /screenshot
    S-->>L: PNG
    L->>E: describe(PNG)
    E-->>L: text observation
    L->>B: decide(goal, observation, history)
    B-->>L: JSON action {thought, action, target...}
    Note over L: done/fail -> return. Otherwise act:
    L->>E: locate(PNG, target)
    E-->>L: pixel (x,y)
    L->>S: POST /action {click x,y}
    S-->>L: {ok}
    Note over L: history.append("clicked 'target' at (x,y)")<br/>-- the ATTEMPT, never verified --
    Note over L: sleep(settle), next step
```

Narration, keyed to [`agent/loop.py`](../agent/loop.py):

1. **Screenshot** the current desktop (top of every step — one fresh frame per step).
2. **`describe`** it → a text observation for the Brain.
3. **`decide`** from `goal + observation + history` → one JSON action.
4. If the action is `done`/`fail`, return. Otherwise it is `click`/`type`/`key`.
5. For `click` (and `type` with a target), **`locate`** the named element on the *same*
   screenshot → `(x,y)`, then **Hands** execute it.
6. **Append to history** a string describing the *attempted* action, then settle and loop.

---

## 4. The two lossy seams (why Phase 5 exists)

The flow above has exactly two places where information is lost. Every Phase-4 failure
we have seen lands on one of them.

### Seam A — the Brain is blind (pixels -> text, one way)

The Brain never receives the PNG. Its entire model of the world is `describe`'s
<=512-token text plus the history strings. Two consequences:

- **Compression:** anything `describe` omits or garbles, the Brain cannot recover.
- **No live-vs-history distinction:** `describe` reports *all visible text as-is*. It has
  no concept of "current input field" vs "log of a past result." If both are on screen,
  the Brain is handed both as equally-current facts.

> **Addressed (2026-07-13):** the live-vs-history half of this seam is largely closed —
> `describe` moved from UI-TARS (a grounding fine-tune that flattened history into the
> current state) to a general VLM (**Qwen2.5-VL-72B**) that explicitly labels the *live
> entry* vs *history*. The Brain is still text-only (compression remains), but it now
> gets a faithful, structured reading. See §6.

### Seam B — history is authored, not observed (no verification)

After acting, the loop appends a string describing what it *tried*
([loop.py:79](../agent/loop.py#L79)) — it never compares the next screenshot to confirm
the action changed anything. So:

- **A misclick is invisible.** "clicked the AC button at (x,y)" is recorded identically
  whether AC did something, did nothing, or hit the wrong element.
- **No progress model.** The Brain *does* receive the history every step
  ([loop.py:58](../agent/loop.py#L58) -> `HISTORY` in the prompt), so it can see it has
  clicked AC five times. But the history records *attempts, not outcomes*, and the Brain
  is not instructed to treat "same action, no change" as futile — so repetition is
  **visible yet unflagged**. If the observation hasn't changed, it makes the same
  decision again. Memory of actions is not enough; Phase 5 needs outcomes *in* the memory
  plus reasoning that stops on repetition.

> **Seam B is Phase 5.** The roadmap's differentiator — *"after each action, check the
> new screenshot: did the thing I intended actually happen? If not, recover"* — is
> precisely the verification this loop does not yet do.

---

## 5. Post-mortem: the 1024 clear-loop

**The failure (Phase 4, gnome-calculator).** The prior `100x3=300` task succeeded and
left that line in gnome-calculator's **history/scrollback**. New goal: `1024x921/73`.
The agent clicked **AC (All Clear)** over and over and **never typed a digit**, looping
until the step budget ran out.

**Mechanism — the same three text/observation values recur every step:**

```mermaid
flowchart TD
    A["screenshot: history still shows '100x3 = 300'"] --> B
    B["describe: reports 'the display shows 100x3=300'<br/>(cannot tell it is a PAST result)"] --> C
    C["decide: 'screen is dirty -> clear it first'<br/>action: click 'the clear (AC) button'"] --> D
    D["locate + Hands click AC"] --> E
    E["AC clears the ENTRY, but history line stays"] --> F
    F["history.append('clicked AC') -- never verified"] --> A
    A -.->|"nothing changed; identical inputs -> identical decision"| A
```

**Three layered causes (root -> trigger):**

1. **Root 1 - Seam B (no verify / no progress model).** "I clicked AC and nothing
   changed" is invisible, so the Brain repeats the same move on an unchanged observation.
   Even a trivial *"the screen didn't change after my last action, stop repeating it"*
   breaks the loop. **Highest-leverage fix — it catches this whole class of failure
   regardless of the app.**
2. **Root 2 - Seam A (describe conflates history with live state).** A structured,
   task-directed describe (e.g. `current entry: empty | history: 100x3=300`) would let
   the Brain ignore the stale log and see the entry is actually empty.
3. **Trigger - gnome-calculator's AC is not a blank slate.** AC clears the current entry
   but not the scrollback. The agent's implicit model ("clear = clean screen") is false
   for this app. This environmental quirk is the *match, not the gas*: it merely
   **exposes** Roots 1 and 2.

**Fix priority for Phase 5:** verification / no-progress detection (Root 1) generalizes
and should come first; structured/task-directed describe (Root 2) removes the trigger for
display-with-history apps specifically. Both are on the Phase-5 table; Root 1 is the
product.

---

## 6. First Phase-5 cut (implemented 2026-07-12) + what remains

Changes aimed at the two seams above — verified live (see "Verified" below).

| Change | What | Attacks |
|---|---|---|
| **Outcomes in memory** | `history` now pairs each step's *observation* with the *action taken* (`saw: … / did: …`), not just the action | **Seam B** — gives the Brain the material to see "I acted, screen unchanged" across steps |
| **Think High** | Brain runs `reasoning.effort=high` (`max_tokens` raised 4096->8192 for trace + JSON headroom) | **Seam B** — the reasoning that *uses* the paired history to judge progress and stop repeating a futile action. No hardcoded "don't repeat" rule — that inference is the reasoning model's job |
| **Task-directed describe** | Brain emits an optional `focus`; the loop carries it into the next `describe`, which then concentrates on that area and distinguishes a live entry from a log of past results | **Seam A** — the Eyes report the task-relevant area in detail instead of a flat dump; removes the history-vs-live conflation that triggered the 1024 loop |

Note the split of labor: **outcomes-in-memory supplies the data, Think High supplies the
reasoning to act on it.** They are orthogonal — the 1024 loop happened with reasoning
*disabled*, so the fix is to turn reasoning on over richer memory, not to bolt a
heuristic onto a mechanical decider.

**Follow-on fixes (2026-07-12/13), each from a live failure:**
- **Disambiguate by position** — name a symbol-button with its location when the symbol
  also appears in the display ("the equals button on the keypad"), else `locate` grabs
  the "=" shown in the equation.
- **English-only + `decide()` JSON retry** — flash occasionally reasoned in Chinese and
  emitted invalid JSON; a global English rule + retry-on-bad-JSON removed both.
- **VLM describe (the decisive Seam-A fix)** — `describe` moved from UI-TARS to
  **Qwen2.5-VL-72B**. UI-TARS (a grounding fine-tune) confabulated results and flattened a
  history/log into the current state; the VLM explicitly labels *live entry* vs *history*,
  killing the recurring clear-loop that prompt-tuning couldn't.

**Verified (2026-07-13):** varied calcs complete cleanly end-to-end — `1550×3÷4=1162.5`,
`128+47=175`, `512−137=375`, `7÷8=0.875`, and `12+34+56=102` **on a cluttered calculator**
(a `7÷8` result in history) — the exact scenario that clear-looped before.

**Still open:** an *explicit* post-action re-check/recover step — the loop still infers
progress implicitly rather than a deliberate "did it land?" branch; and the **Brain likely
moves to `deepseek-v4-pro`** for harder multi-step reasoning (re-benchmark flash on the
now-clean describe first, since much of its earlier flakiness was describe garbage-in).
