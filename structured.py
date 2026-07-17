"""BRYES — structured LLM output (the JSON-building STANDARD; ADR-005).

Every structured reply we need from an LLM goes through here. The contract:

  1. Define the shape as a Pydantic model (typed fields + Field(description=...)).
  2. Call structured_call(Model, messages, ...): it FORCES the model to call one virtual
     function whose parameters ARE the model's JSON schema (tool_choice pins it), then
     VALIDATES the returned arguments back through the Pydantic model.
  3. You get a validated Model instance (+ usage), or a StructuredError carrying the
     raw provider body for root-causing.

Why FORCED tool-calling + OUR OWN validation (ADR-005): the shape is elicited by forcing a
tool-call (the model answers by filling the function's arguments), and the Pydantic validation
is OUR guard, so validity does NOT depend on the provider. Tool-call arguments get strong
structural pressure — models fill them COMPLETELY (optional fields included). A brief switch to
`response_format json_schema` (strict:false) let reasoning models be terse and DROP optional
fields (visual_expectation emission fell ~89% -> 0%; Phase-5 verify silently died, 2026-07-17).
We had only left tool-calling to dodge qwen's "tool_choice not supported in thinking mode" 400;
qwen is since dropped (deepseek primary + gemini backup, both fine with tool-calling), so we
reverted. The virtual function is NEVER executed — it is purely an output-shaping device.

Transport only (OpenRouter, OpenAI-compatible). Retry / model-fallback policy lives in the
caller, which catches StructuredError and decides what to do next.
"""
import json
import re
import urllib.error
import urllib.request

from pydantic import BaseModel, ValidationError  # noqa: F401  (BaseModel re-exported for callers)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class StructuredError(RuntimeError):
    """A structured call failed: transport, empty content, unparseable JSON, or
    schema validation. `.body` holds the raw provider response (dict) when there was one —
    that is what carries the real cause (e.g. a provider `finish_reason=error`)."""

    def __init__(self, message, *, body=None):
        super().__init__(message)
        self.body = body


def structured_call(schema_model, messages, *, model, api_key, reasoning=None,
                    max_tokens=4096, timeout=60, schema_name="respond",
                    schema_transform=None, headers=None):
    """Force the model to return an instance of `schema_model` via a forced tool-call; validate it.

    Returns (instance, usage_dict). Raises StructuredError (with .body) on any failure.

    `schema_name` names the (virtual, never-executed) function the model is forced to call;
    `schema_transform(schema_dict) -> schema_dict` lets the caller tweak the generated JSON
    schema before it is sent (e.g. inject a dynamic enum into one property).
    """
    schema = schema_model.model_json_schema()
    if schema_transform:
        schema = schema_transform(schema)
    body = {
        "model": model,
        "temperature": 0,
        "messages": messages,
        "max_tokens": max_tokens,
        # Elicit the shape by FORCING one tool-call whose parameters ARE `schema`: the model
        # answers by filling the function's arguments (returned in tool_calls[0]). Tool-call
        # arguments get stronger structural pressure than a strict:false response_format, so the
        # model fills optional fields (e.g. visual_expectation) it otherwise drops. OUR Pydantic
        # validation (below) is still the guard; the function is never executed. See ADR-005.
        "tools": [{"type": "function", "function": {
            "name": schema_name, "description": "Return the result.", "parameters": schema}}],
        "tool_choice": {"type": "function", "function": {"name": schema_name}},
    }
    if reasoning is not None:
        body["reasoning"] = reasoning

    req = urllib.request.Request(
        OPENROUTER_URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json", **(headers or {})},
        method="POST")
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        raise StructuredError(f"HTTP {e.code}: {e.read().decode()[:400]}") from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise StructuredError(f"network error: {e}") from e

    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    tool_calls = msg.get("tool_calls") or []
    if tool_calls:
        raw_args = tool_calls[0].get("function", {}).get("arguments")
    else:
        raw_args = msg.get("content")     # fallback: a model that ignored tool_choice
    if not raw_args:
        # No tool-call AND no content = a reasoning model that spiralled/degenerated
        # (finish_reason=error) or a provider hiccup — the caller retries / escapes to backup.
        raise StructuredError(
            f"no tool-call or content (finish_reason={choice.get('finish_reason')})",
            body=data)

    args = _loads_lenient(raw_args)
    if args is None:
        raise StructuredError(f"arguments were not JSON: {str(raw_args)[:200]!r}", body=data)

    try:
        instance = schema_model.model_validate(args)
    except ValidationError as e:
        raise StructuredError(f"schema validation failed: {e}", body=data) from e

    return instance, data.get("usage")


def _loads_lenient(raw):
    """Parse the tool-call arguments (a JSON string). Provider-enforced args are already valid
    JSON; the regex fallback only rescues a stray-prose wrapper from a model that ignored
    tool_choice and answered in content instead."""
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
