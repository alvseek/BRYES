# ADR-005: Structured LLM Output — Pydantic + Forced Tool-Calling (formats are enforced by tools, not the AI)

**Date**: 2026-07-16

**Status**: Accepted

---

## Problem

The Brain's `decide()` asked the model for JSON the **loosest** possible way: `response_format: {"type": "json_object"}` (which only guarantees *some* valid JSON, not our shape) + a JSON schema pasted into the **prompt as prose** + a lenient regex scrape of the reply. There was **no guard**: a malformed reply, a missing field, or a wrong-typed value would slip straight through, or fail deep in the loop.

Two failures made this concrete:

1. **Malformed JSON class** — a reasoning model occasionally emits invalid JSON (an unescaped quote, a stray token). The lenient parser papered over some of it and silently mangled the rest.
2. **A provider degeneration crash** — live capture (`decide-error` records) caught qwen3.6-flash returning HTTP 200 with `finish_reason=error`, `content: null`, and a **1148-token reasoning loop** ("click division, then 112, then equals" repeated). Alibaba's own message blamed *"generating a JSON response for response_format."* Asking a reasoning model to *both* think hard *and* hand-build free-form JSON gave it rope to hang itself.

The root principle: **any output that must conform to a format should be produced and validated by tools — never left to the model (or a hand-built string) to get right.**

---

## Decision

**We decided to** make structured LLM output go through one reusable path — **define a Pydantic model → force a tool-call built from its schema → validate the returned args back through the model** — and make that the project **standard** for all format-bearing LLM output.

- **`structured.py`** — the standard, transport-only helper: `structured_call(schema_model, messages, *, model, api_key, reasoning, schema_transform, ...)`. It builds a function whose parameters ARE `schema_model.model_json_schema()`, sends it with `tool_choice` **forcing** the call, extracts the tool-call arguments, and **validates them through Pydantic**. Returns a validated instance (+ usage), or raises `StructuredError` carrying the raw provider body for root-causing. Retry / model-fallback policy stays in the caller.
- **`brain/client.py`** — the action shape is a Pydantic `BrainAction` model (field descriptions ARE the schema the model sees); `decide()` calls `structured_call` with the dynamic `action` enum injected per-body via `schema_transform`; the loose `json_object` path, the prose schema block, and `_extract_json` are gone.

**Why we chose this (Path A — Pydantic + native tool-calling):**
- **Our validation is the guard — not the provider's.** Tool-calling constrains the shape *where the provider supports it*, but strict enforcement is a per-model capability we refuse to depend on. Pydantic validates every reply on our side, so validity holds even on a provider that ignores the schema. (User's load-bearing point: "we should have our own standard, not rely on something that may not be available.")
- **Widest support.** Tool-calling is supported on **18/18** providers for the backup model (deepseek-v4-flash) and on the primary (qwen3.6-flash) — wider even than strict `json_schema` (13/18). Check `supported_parameters` (or set `provider: {require_parameters: true}`) before trusting it on a *new* model.
- **The model fills fields, it doesn't format.** A forced tool-call is the simplest generation job — no free-form JSON string to malform.
- **Minimal footprint.** Native tool-calling keeps the agent on hand-rolled `urllib` (no OpenAI-SDK/instructor migration); Pydantic is the one added dep, alongside the Eyes' existing Pillow.

---

## What this fixes (and what it doesn't)

- **Eliminates the malformed-JSON class** entirely — a bad reply is a caught `StructuredError`, retried, never a silent mangle.
- **Makes the degeneration survivable** — the reasoning-loop crash becomes a `StructuredError` the caller retries and (ADR: model fallback) escapes to the backup model, instead of a fatal crash.
- **Does NOT, by itself, stop a pure reasoning spiral** — that runs before the args. Resilience against it comes from the retry + the multi-provider backup model, not from the output format. Honest boundary.

---

## The standard (reusable)

Any format-bearing LLM output MUST use this shape:

1. Define the output as a **Pydantic model** (typed fields, `Field(description=...)` as the model-facing guidance).
2. Call **`structured_call(Model, messages, ...)`** — forced tool-call + **our** validation.
3. Handle **`StructuredError`** (retry / fall back / surface) in the caller.

Forbidden for structured data: `response_format: {"type": "json_object"}` free-text, or asking the model to emit a JSON string you then parse by hand. Documented in [quality-standard.md](../quality-standard.md) Dimension 9; checked in review by `/analyze-code-quality` (Dimension 8); enforced at runtime by `structured.py`.

---

## Alternatives Rejected

- **Keep `json_object` + a stricter prompt / more retries** — beating around the bush: at `temperature: 0` a same-params retry re-triggers a deterministic degeneration, and nothing guards the *format*. The user named this directly.
- **Strict `json_schema` structured outputs** — constrains content provider-side, but only 13/18 providers support it (vs 18/18 for tools), and it still relies on the provider, not us.
- **Our own labeled-field text parser** (`ACTION: ... / TARGET: ...`, we assemble the dict) — zero-dep and robust, but loses typed validation and nested structure; Pydantic + tools is cleaner for the same guarantee.
- **`instructor` + OpenAI SDK** — the batteries-included version of exactly this, but it migrates the Brain off `urllib` onto the OpenAI SDK (heavier footprint) for no extra guarantee over native tool-calling + Pydantic.
- **A build-time guard script** (grep for forbidden patterns, fail CI) — deferred; runtime Pydantic + `/analyze-code-quality` cover enforcement without new machinery.

---

## Relationship to the other ADRs

Orthogonal to ADR-001 (effector tier), ADR-002 (body), ADR-003 (change-feedback), ADR-004 (foveal describe) — those shape *what* the Brain decides and *how* the Eyes perceive; this shapes *how the decision is transported and validated*. It hardens the `decide()` these all depend on: every action now arrives type-checked.
