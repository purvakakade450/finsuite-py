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
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.8-flash"),
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


def settings() -> tuple[str, str, str]:
    """(base address, model, key)"""
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


def _post(payload: dict, stream: bool):
    base, _model, key = settings()
    try:
        r = requests.post(f"{base}/chat/completions", json=payload, stream=stream, timeout=(10, 120 if stream else 75),
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
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
    _base, model, _key = settings()
    system = core.SYSTEM_PROMPT + core.LANGUAGE_NOTES.get(language, "")
    note = core._context_note(context)
    if note:
        system += "\n\nFacts about this user: " + note
    messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in history[-core.MAX_HISTORY:]]
    tools = tool_list()
    try:
        for _round in range(core.MAX_TOOL_ROUNDS):
            payload = {"model": model, "messages": messages, "tools": tools, "stream": True,
                       "max_tokens": core.MAX_OUTPUT_TOKENS}
            text, calls, finish = "", [], None
            response = _post(payload, stream=True)
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
    _base, model, _key = settings()
    payload = {"model": model, "temperature": 0, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    try:
        reply = _post({**payload, "response_format": {"type": "json_object"}}, stream=False)
    except ProviderError as e:
        if e.status != 400:
            raise
        reply = _post(payload, stream=False)                # a provider without JSON mode: ask in plain text
    content = reply.json()["choices"][0]["message"]["content"] or ""
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    return json.loads(content)
