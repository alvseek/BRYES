# BRYES — Phase 4: Close the Loop

Chains all four pieces into one autonomous cycle:

```
screenshot ─▶ Eyes.describe ─▶ Brain.decide ─▶ Eyes.locate ─▶ Hands act ─▶ (repeat)
             (what's here)     (what to do)    (where)        (do it)
                                                      until "done" / "fail" / step-limit
```

- **Eyes.describe** tells the Brain what's on screen (Brain is text-only).
- **Brain.decide** picks ONE next action, naming its target by description.
- **Eyes.locate** grounds that description to a pixel.
- **Hands** (the Screen container) execute it.

## Run it

```bash
cd screen && docker compose up -d          # Screen must be running
python agent/test_phase4.py                # runs the ONE task
```

The one task: **compute 7 + 8 on the calculator**. A clean run finishes in 5 steps
(`7 → plus(+) → 8 → equals(=) → done`) and leaves **15** on the display —
saved to `agent_final.png`.

```python
from agent.loop import run
run("Use the calculator to compute 7 + 8", max_steps=12)
# -> {'status': 'done', 'steps': 5, 'history': [...]}
```

## What broke on the way (→ input for Phase 5)

Per the roadmap, the base loop working isn't the product — the *reliability* is. The
failures found here are exactly what the Phase 5 verify-and-recover layer must handle:

1. **Bare-symbol grounding.** The Brain first wrote *"the = button"*; UI-TARS
   consistently mislocated the bare `=` glyph (to (173,262) instead of (267,476)),
   so `=` never pressed and the loop spun — clearing and retrying forever. Fixed for
   now by coaching the Brain to name symbols in words (*"the equals (=) button"*), but
   the real fix is a **verify step**: "I clicked =, did the display change to a
   result? If not, re-locate / retry." Without verify, a single bad grounding
   dead-ends the whole task.
2. **No effect-checking.** The loop trusts every action landed. A missed click is
   invisible until the next `describe`, and the Brain can loop. Phase 5 adds the
   "did the intended thing happen?" check after each action.
3. **Reasoning-token truncation** (fixed). DeepSeek V4 is a reasoning model; its
   hidden thinking tokens ate the output budget and truncated the JSON
   (`content: null`). Fixed by disabling reasoning for the decider (`reasoning:
   {enabled: false}`) — one next-action doesn't need extended thought.
4. **Cold-connection flake** (fixed). The Screen's Flask dev server occasionally drops
   the first request after a restart; the loop's HTTP calls now retry.

## Cost per run

~5 steps × (1 describe + ~1 locate UI-TARS call + 1 Brain call) ≈ **under $0.005**
for the whole task. The Eyes dominate (called ~2× per step) — the Phase 6 cost line.
