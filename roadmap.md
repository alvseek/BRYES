# Vision-Based Computer-Use Agent — Build Roadmap

A milestone-driven plan you can hand to Claude Code one phase at a time.
Each step lists: **the goal**, **what to have Claude Code build**, **the test that proves it works**, and **the trap to avoid**.

## The architecture you're building toward

Four independent pieces that talk over HTTP. None runs inside another.

- **Brain** — DeepSeek V4, rented via OpenRouter. Decides the next action.
- **Eyes** — UI-TARS-1.5-7B, rented via OpenRouter. Turns a screenshot into element coordinates.
- **Screen** — a local Ubuntu container with a virtual display. The desktop the agent controls.
- **Hands** — `xdotool` inside that container. Executes clicks and typing.

The loop: **screenshot → eyes find elements → brain picks an action → hands do it → new screenshot → repeat.**

Your differentiator is a **verify step** bolted on top: after each action, check the new screenshot to confirm the action actually did what was intended, and recover if it didn't.

**Two rules that keep you fast:**
1. Rent everything until it hurts. Your GPU (3060 Ti, 8GB) is a last resort, not a starting point.
2. Prove ONE real task end-to-end before making anything general.

---

## Phase 0 — Setup (30 min, do this first)

**Goal:** Have the one account and the one task you'll build against.

- Get a single **OpenRouter** API key. This one key covers both the brain and the eyes.
- Load a small amount of credit ($10–20 is plenty for prototyping).
- **Pick your ONE task.** Not "a general assistant." Something concrete and boring with a clear success state, e.g. "open this app, fill this form, confirm it saved." Write it down. Everything you build gets tested against this task.

**Done when:** You have a working key and a one-sentence task written down.

**Trap:** Picking a vague or ambitious first task. The narrower it is, the faster you'll know if the thing works.

---

## Phase 1 — The Screen (the local container)

**Goal:** A disposable Linux desktop running in a container on your machine that you can screenshot and click inside.

- Have Claude Code build a container image with: Ubuntu, a virtual display (Xvfb), an X11 session, and `xdotool` installed.
- Expose two simple abilities from the container: **take a screenshot** (returns an image) and **perform an action** (click at x/y, type text, press a key).
- Put one visible app inside it to test against — even just a file manager or a browser.

**Done when:** You can trigger a screenshot and get back a PNG of the desktop, AND you can send a "click at (x, y)" and see something happen in that screenshot afterward.

**Trap:** Hand-rolling the display server from scratch. Tell Claude Code to start from an existing computer-use / Xvfb container base image. This is the classic time sink.

---

## Phase 2 — Wire the Eyes

**Goal:** Send a screenshot out, get back element locations.

- Point Claude Code at the OpenRouter endpoint for **UI-TARS-1.5-7B** (OpenAI-compatible format, same key as everything else).
- Build the single function: screenshot in → the model returns what elements are on screen and where (coordinates).

**Done when:** You hand it a screenshot of your task's app and it correctly reports where a known button or field is. Sanity-check the coordinates against what you see.

**Trap:** Reaching for a generic vision model (GPT-4o vision, Gemini, Qwen-VL) because it's already handy. Those are bad at precise coordinates — that's the whole reason a grounding model exists. Use UI-TARS specifically.

---

## Phase 3 — Wire the Brain

**Goal:** Given the goal + what's on screen, decide the next single action.

- Point Claude Code at the OpenRouter endpoint for **DeepSeek V4** (same key, OpenAI format).
- Build the function: (the task goal + the eyes' description of the screen) in → one concrete next action out (e.g. "click the Submit button").
- Keep the brain reasoning about *elements*, not raw pixels. The eyes handle pixels; the brain handles decisions.

**Done when:** Given a screenshot description and your task, it outputs a sensible next step in plain, structured terms.

**Trap:** Wiring the legacy model names (`deepseek-chat` / `deepseek-reasoner`) into any fallback logic — they retire July 24, 2026. Use `deepseek-v4-pro` or `deepseek-v4-flash`.

---

## Phase 4 — Close the Loop

**Goal:** Run the full cycle unattended on your ONE task.

- Have Claude Code chain the pieces: screenshot → eyes → brain → hands → screenshot → repeat, until the task's success state or a step limit.
- Run it against your ONE task. Watch it.

**Done when:** It completes your one task start to finish at least once, on its own.

**Trap:** Trying to handle every edge case now. Get one clean success first, even a fragile one. Note *how* it fails on the retries — those failures are the input to the next phase.

---

## Phase 5 — The Verify Layer (your actual product)

**Goal:** The agent knows whether each action worked, and recovers when it didn't. This is the part that makes it better than the incumbents.

- After each action, have the brain look at the *new* screenshot and answer: "Did the thing I intended actually happen?"
- If yes → continue. If no → don't blindly proceed; re-assess and try a recovery (re-locate the element, retry, or pick a different action).
- Feed it the specific failure modes you saw in Phase 4 (misclicks, missed dialogs, wrong element).

**Done when:** You deliberately make the screen behave unexpectedly (move a button, add a popup) and the agent notices the action didn't land instead of marching on into a broken sequence.

**Trap:** Skipping this because Phase 4 "already works." The base loop working isn't the product — the reliability is. This is where your earlier validation/cost work pays off.

---

## Phase 6 — Decide on Hosting (only if forced)

**Goal:** Address cost/reliability only once real usage reveals a real problem.

- Watch which line item hurts. The **eyes get called on every single step**, so they quietly become your highest-volume cost even though each call is cheap.
- Only *if* the rented eyes are the pain point, consider: jump to UI-TARS-72B (still rented), a Volcano Engine / other endpoint for the newer UI-TARS-2, or self-hosting a small 2B grounding model on the 3060 Ti (fits 8GB).
- The brain almost never needs to move off rented — leave it on OpenRouter.

**Done when:** You have a specific measured reason to change hosting, not a hypothetical one.

**Trap:** Pre-optimizing into DIY or chasing the newest model version before the cheap rented setup has actually failed on your real screens.

---

## Quick reference — the order that keeps you fast

1. Key + one task written down.
2. A container you can screenshot and click.
3. Eyes: screenshot → coordinates.
4. Brain: state → next action.
5. Loop them until the one task completes once.
6. Add verify-and-recover — this is the product.
7. Touch hosting only when a measured cost or reliability problem appears.

Everything rented, one OpenRouter key, one local container, zero local GPU until Phase 6 forces the question.
