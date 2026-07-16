"""BRYES — structured LLM output (the JSON-building STANDARD; ADR-005).

Every structured reply we need from an LLM goes through here. The contract:

  1. Define the shape as a Pydantic model (typed fields + Field(description=...)).
  2. Call structured_call(Model, messages, ...): it asks the model via TOOL-CALLING —
     the provider fills a function whose parameters ARE the model's JSON schema, and
     tool_choice FORCES the call — then VALIDATES the returned arguments back through
     the Pydantic model.
  3. You get a validated Model instance (+ usage), or a StructuredError carrying the
     raw provider body for root-causing.

Why tool-calling + OUR OWN validation (ADR-005): `response_format: json_object` is loose
(the model hand-builds a JSON string it can malform) and strict provider-side enforcement
is a per-model capability we cannot rely on. Tool-calling constrains the shape where the
provider supports it, and the Pydantic validation is OUR guard — so validity does NOT
depend on the provider being able (or willing) to enforce the schema.

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
    """A structured call failed: transport, no tool-call/content, unparseable args, or
    schema validation. `.body` holds the raw provider response (dict) when there was one —
    that is what carries the real cause (e.g. a provider `finish_reason=error`)."""

    def __init__(self, message, *, body=None):
        super().__init__(message)
        self.body = body


def structured_call(schema_model, messages, *, model, api_key, reasoning=None,
                    max_tokens=4096, timeout=60, tool_name="respond",
                    tool_description="Return the result.", schema_transform=None,
                    headers=None):
    """Force the model to return an instance of `schema_model` via tool-calling; validate it.

    Returns (instance, usage_dict). Raises StructuredError (with .body) on any failure.

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
        "tools": [{
            "type": "function",
            "function": {"name": tool_name, "description": tool_description,
                         "parameters": schema},
        }],
        # FORCE the call — the model must answer by filling this function, not free text.
        "tool_choice": {"type": "function", "function": {"name": tool_name}},
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
    """Parse tool-call arguments. Provider-enforced args are already valid JSON; the regex
    fallback only rescues a stray-prose wrapper from a model that ignored tool_choice."""
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
