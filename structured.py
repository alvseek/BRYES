"""BRYES — structured LLM output (the JSON-building STANDARD; ADR-005).

Every structured reply we need from an LLM goes through here. The contract:

  1. Define the shape as a Pydantic model (typed fields + Field(description=...)).
  2. Call structured_call(Model, messages, ...): it asks the model via response_format
     json_schema (the provider is handed the model's JSON schema and replies with JSON in
     message.content), then VALIDATES that reply back through the Pydantic model.
  3. You get a validated Model instance (+ usage), or a StructuredError carrying the
     raw provider body for root-causing.

Why response_format json_schema + OUR OWN validation (ADR-005): the shape is elicited with
response_format — NOT tool-calling, NOT loose `json_object` free-text — and the Pydantic
validation is OUR guard, so validity does NOT depend on the provider enforcing the schema.
We keep strict=False (the schema GUIDES, we validate) because a hard grammar / forced
tool-call constrains a reasoning model's THINKING stream and makes it degenerate (the qwen
failure); loose elicitation + our validation is both safer and portable across providers.

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
    """Ask the model for an instance of `schema_model` via response_format json_schema; validate it.

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
        # Ask for the shape via response_format json_schema (NOT tool-calling): the provider
        # takes `schema` as the JSON Schema for the reply, returned in message.content.
        # strict=False -> the schema GUIDES generation, and OUR Pydantic validation (below) is
        # the real guard — so validity never depends on provider enforcement, and it stays
        # portable across providers (a hard grammar / forced tool-call breaks some reasoning
        # models by constraining their thinking stream). See ADR-005.
        "response_format": {"type": "json_schema", "json_schema": {
            "name": schema_name, "strict": False, "schema": schema}},
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
    raw_args = msg.get("content")     # response_format returns the JSON reply in content
    if not raw_args:
        # Empty content = a reasoning model that spiralled/degenerated (finish_reason=error)
        # or a provider hiccup — the caller retries / escapes to the backup model.
        raise StructuredError(
            f"empty content (finish_reason={choice.get('finish_reason')})",
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
    """Parse the JSON reply. Well-formed content is already valid JSON; the regex fallback
    only rescues a stray-prose wrapper from a model that wrapped its JSON in text."""
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
