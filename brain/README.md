# BRYES — Phase 3: The Brain

Decides the single next action. Given the goal + a **text** description of the screen
+ the history, it outputs one structured action, naming its target **by description**.
Uses **DeepSeek V4** via OpenRouter. Like the Eyes, it's a rented API client, not a
container.

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

Output schema:

```json
{ "thought": "one sentence", "action": "click|type|key|done|fail",
  "target": "element description (click)", "text": "text (type)", "key": "keyname (key)" }
```

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

DeepSeek V4 (`deepseek-v4-flash` / `-pro`) is a **text** model — it can't see images,
by design. The Eyes (a vision model) handle pixels; the Brain handles decisions. This
is exactly the roadmap's rule: *"keep the brain reasoning about elements, not raw
pixels."* The two models specialise instead of one model doing both badly.

## Model choice

- **`deepseek/deepseek-v4-flash`** (default) — $0.077/M in, $0.15/M out, 1M context.
  ~$0.00008 per decision. Enough for single-step choices.
- **`deepseek/deepseek-v4-pro`** — 4.5× the price, stronger reasoning. Switch `MODEL`
  in [client.py](client.py) if the Brain makes weak calls on your real task.
- Avoid the legacy `deepseek-chat` / `deepseek-reasoner` slugs — they retire
  **2026-07-24**.

## Open question for Phase 4

The Brain needs a text `observation` of the screen, but it can't see. Phase 4 (Close
the Loop) must decide where that description comes from — most likely by asking
UI-TARS (a vision model) to *describe* the screen each step, in addition to its
*grounding* role.
