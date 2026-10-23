# BRYES — Phase 3: The Brain

Decides the single next action. Given the goal + a **text** description of the screen
+ the history, it outputs one structured action, naming its target **by description**.
Uses **DeepSeek V4.1 Flash** (`deepseek/deepseek-v4.1-flash`) via OpenRouter. Like the
Eyes, it's a rented API client, not a container.

## The one function

```python
from brain.client import decide

action = decide(
    goal="Compute 7 + 8 on the calculator",
    observation="A calculator. The display shows '7'. Buttons 0-9, + - * /, = are visible.",
    history=["click the 7 button (display now shows 7)"],
)
# -> {'thought': '...', 'action': 'click', 'target': 'the + button'}
```

Output schema (every field optional except `thought` and `action`; the action list is
assembled per body from that body's capabilities):

```json
{ "thought": "one sentence", "action": "<one of the body's actions>",
  "target": "element description", "destination": "drop point (drag)",
  "direction": "up|down (scroll)", "text": "text to type", "key": "keyname (key)",
  "command": "shell line (shell)" }
```

The point verbs are `click`, `double_click`, `right_click`, `hover`, `scroll`, `drag`,
`type`, `key`, plus `type_into` (the click/clear/type/Enter combo). The loop metas are
`wait`, `screenshot`, `done` and `fail`, and `shell` is offered only when the body has one.

The `target` is a natural-language element description — in Phase 4 the Eyes ground it
to pixels and the Hands execute it. That's the whole split: **Brain names elements,
Eyes find pixels.**

## Run the proof

```bash
python brain/test_phase3.py
```

Two scenarios prove it both advances and terminates:
- display shows `7` → decides **click the + button**
- display shows `15` → decides **done**

## Why text-only is the right shape

V4.1 Flash **accepts** image input, but this client still sends text only. The Eyes (a
vision model) handle pixels; the Brain handles decisions. This is exactly the roadmap's
rule: *"keep the brain reasoning about elements, not raw pixels."* The two models
specialise instead of one model doing both badly, and a Brain that sees for itself is now
a prompt change rather than a rewrite.

## Model choice

- **`deepseek/deepseek-v4.1-flash`** (default) — the primary. Same structured-output
  discipline as its predecessor: our Pydantic schema, a forced tool-call, our validation
  (ADR-005), verified live before the default moved on 2026-10-21.
- **`google/gemini-2.5-flash-lite`** (backup) — the last attempt escapes here when the
  primary degenerates. Different weights is the whole point: it survives a weight-level
  reasoning loop that the primary cannot.
- Price is a property of the OpenRouter route, not the model: one model id can have many
  endpoints at very different prices, so measure the call rather than quoting a list
  figure. A live `decide()` in the swap session cost $0.0011.
- Avoid the legacy `deepseek-chat` / `deepseek-reasoner` slugs — they retired
  **2026-07-24**.

## Where the observation comes from

The Brain needs a text `observation` of the screen, but it can't see. Phase 4 answered
this: the Eyes describe the screen each step, in two modes (ADR-004), and report a
predicted state back for the Brain to compare (ADR-003/007). The `describe` side runs on
`deepseek-v4.1-flash` since 2026-10-21 — see [eyes/client.py](../eyes/client.py).
