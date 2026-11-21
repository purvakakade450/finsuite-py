"""
AI assistant on any OpenAI-style service, so FinSuite can run on a FREE model
(Google Gemini's free tier, Groq's free plan, OpenRouter's free models) with
no payment, instead of the paid Anthropic API.

Settings (environment variables):
    AI_API_KEY    the key from the provider (this turns the assistant on)
    AI_PROVIDER   gemini (default), groq, openrouter, mistral or custom
    AI_MODEL      overrides the provider's default model
    AI_BASE_URL   for "custom": the service's OpenAI-style address

It uses the same 16 FinSuite tools and the same guard rails as the Claude
version (see ai_assistant.py) and streams the same events to the page.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Iterator

import requests

from . import ai_assistant as core

log = logging.getLogger("finsuite.ai")

# provider: (base address, default model)
PRESETS = {
    # Free tiers give each model its own small daily allowance (one Gemini model allows only 20 requests a day),
    # so several are listed: when one has run out or is overloaded, the next one is tried.
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.1-flash-lite,gemini-3.5-flash-lite,gemini-3.8-flash"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free"),
    "mistral": ("https://api.mistral.ai/v1", "mistral-small-latest"),
}
# Keywords that some providers reject in a tool's schema. FinSuite checks every input itself
# (with the full schema) before running a tool, so dropping them here is safe.
_UNSUPPORTED = {"pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength",
                "minItems", "maxItems", "default", "title", "additionalProperties", "$defs", "format"}


class ProviderError(Exception):
    def __init__(self, status: int | None, message: str):
        super().__init__(message)
        self.status = status


def configured() -> bool:
    return bool(os.environ.get("AI_API_KEY", "").strip())


def model_list() -> list[str]:
    """The models to try, in order (AI_MODEL may hold several, separated by commas)."""
    return [m.strip() for m in settings()[1].split(",") if m.strip()]


def settings() -> tuple[str, str, str]:
    """(base address, model or comma-separated models, key)"""
    provider = os.environ.get("AI_PROVIDER", "gemini").strip().lower()
    base, model = PRESETS.get(provider, (os.environ.get("AI_BASE_URL", ""), os.environ.get("AI_MODEL", "")))
    return (os.environ.get("AI_BASE_URL", base).rstrip("/"), os.environ.get("AI_MODEL", model) or model,
            os.environ.get("AI_API_KEY", "").strip())


def simplify(schema):
    """A tool schema reduced to what every provider accepts."""
    if isinstance(schema, list):
        return [simplify(x) for x in schema]
    if not isinstance(schema, dict):
        return schema
    if "anyOf" in schema:                                   # Optional[x] -> x
        options = [o for o in schema["anyOf"] if o.get("type") != "null"]
        merged = {**{k: v for k, v in schema.items() if k != "anyOf"}, **(options[0] if options else {})}
        return simplify(merged)
    return {k: simplify(v) for k, v in schema.items() if k not in _UNSUPPORTED}


def tool_list() -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": simplify(t["input_schema"])}} for t in core.TOOL_DEFS]


def _explain(status: int | None, text: str) -> str:
    if status in (401, 403):
        return "The AI service rejected the API key. Check AI_API_KEY."
    if status == 429:
        return "The free AI service is busy or today's free allowance is used up. Please try again later."
    if status == 400:
        return f"The AI service could not process this request ({text[:160]})."
    return f"The AI service returned an error ({status}). Please try again."


_RETRY_ON_NEXT_MODEL = (None, 429, 500, 502, 503, 504)     # out of quota, overloaded, unreachable or too slow


def _post(payload: dict, stream: bool, wait: int | None = None):
    base, _model, key = settings()
    try:
        r = requests.post(f"{base}/chat/completions", json=payload, stream=stream,
                          timeout=(10, wait or (120 if stream else 75)),
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    except requests.Timeout as e:
        raise ProviderError(None, "The AI service took too long to answer. Please try again.") from e
    except requests.RequestException as e:
        raise ProviderError(None, "Could not reach the AI service. Check the internet connection.") from e
    if r.status_code != 200:
        body = ""
        try:
            body = r.text
        except Exception:
            pass
        raise ProviderError(r.status_code, _explain(r.status_code, body))
    return r


def _first_working(models: list[str], send):
    """Call send(model) for each model until one succeeds; only a quota, overload or timeout moves on to the next."""
    last: ProviderError | None = None
    for i, model in enumerate(models):
        try:
            return model, send(model, 40 if i < len(models) - 1 else None)
        except ProviderError as e:
            last = e
            if e.status not in _RETRY_ON_NEXT_MODEL:
                raise
            log.info("AI model %s unavailable (%s), trying the next one", model, e.status)
    raise last


def _read_stream(response) -> Iterator[tuple[str, object]]:
    """Yield ("text", piece) while the answer arrives, then ("done", (text, tool_calls, finish_reason))."""
    text, calls, finish = "", [], None
    for raw in response.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        data = raw[5:].strip()
        if data == "[DONE]":
            break
        try:
            choice = json.loads(data)["choices"][0]
        except (ValueError, KeyError, IndexError):
            continue
        delta = choice.get("delta") or {}
        if delta.get("content"):
            text += delta["content"]
            yield "text", delta["content"]
        for tc in delta.get("tool_calls") or []:
            tid, fn = tc.get("id"), tc.get("function") or {}
            if tid and not any(c["id"] == tid for c in calls):
                calls.append({"id": tid, "name": "", "args": ""})
                cur = calls[-1]
            elif tid:
                cur = next(c for c in calls if c["id"] == tid)
            else:                                           # a later piece of a call that has already started
                index = tc.get("index", len(calls) - 1)
                if not calls or not 0 <= index < len(calls):
                    calls.append({"id": f"call_{len(calls)}", "name": "", "args": ""})
                    index = len(calls) - 1
                cur = calls[index]
            if fn.get("name"):
                cur["name"] = fn["name"]
            if fn.get("arguments"):
                cur["args"] += fn["arguments"]
            if tc.get("extra_content"):                     # Gemini 3 needs this echoed back with the call
                cur["extra"] = tc["extra_content"]
        if choice.get("finish_reason"):
            finish = choice["finish_reason"]
    yield "done", (text, calls, finish)


def chat_stream(history: list[dict], context: dict | None = None, language: str = "en") -> Iterator[str]:
    """Same events as ai_assistant.chat_stream: tool, text, error, done."""
    models = model_list()
    system = core.SYSTEM_PROMPT + core.LANGUAGE_NOTES.get(language, "")
    note = core._context_note(context)
    if note:
        system += "\n\nFacts about this user: " + note
    messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in history[-core.MAX_HISTORY:]]
    tools = tool_list()
    try:
        for _round in range(core.MAX_TOOL_ROUNDS):
            payload = {"messages": messages, "tools": tools, "stream": True, "max_tokens": core.MAX_OUTPUT_TOKENS}
            text, calls, finish = "", [], None
            # The first request of a question may move to another model; the rest stay with the one that answered,
            # because some models tie a tool call to the model that made it.
            chosen, response = _first_working(models, lambda m, wait: _post({**payload, "model": m}, stream=True, wait=wait))
            models = [chosen]
            try:
                for kind, value in _read_stream(response):
                    if kind == "text":
                        yield core._event(type="text", text=value)
                    else:
                        text, calls, finish = value
            finally:
                response.close()
            calls = [c for c in calls if c["name"]]
            if not calls:
                if finish == "length":
                    yield core._event(type="text", text="\n\n(The answer got too long and was cut off.)")
                break
            for c in calls:
                yield core._event(type="tool", name=c["name"], label=core.TOOLS.get(c["name"], ("", None, None, "Working"))[3])
            messages.append({"role": "assistant", "content": text or None, "tool_calls": [
                {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["args"] or "{}"},
                 **({"extra_content": c["extra"]} if c.get("extra") else {})} for c in calls]})
            for c in calls:
                try:
                    args = json.loads(c["args"] or "{}")
                except ValueError:
                    args = None
                result, _is_error = core.run_tool(c["name"], args)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": result})
            yield core._event(type="text", text="\n\n")
        else:
            yield core._event(type="text", text="\n\n(Stopped after several data lookups; please narrow the question.)")
    except ProviderError as e:
        if e.status not in (401, 403, 429):
            log.warning("AI provider error: %s", e)
        yield core._event(type="error", message=str(e))
    yield core._event(type="done")


def complete_json(system: str, user: str) -> dict:
    """One non-streaming request that must answer with a JSON object (used for translations)."""
    payload = {"temperature": 0, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}

    def ask(model, wait):
        try:
            return _post({**payload, "model": model, "response_format": {"type": "json_object"}}, stream=False, wait=wait)
        except ProviderError as e:
            if e.status != 400:
                raise
            return _post({**payload, "model": model}, stream=False, wait=wait)   # a provider without JSON mode
    _model, reply = _first_working(model_list(), ask)
    content = reply.json()["choices"][0]["message"]["content"] or ""
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    return json.loads(content)
