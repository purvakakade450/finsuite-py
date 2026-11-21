"""The assistant on a free OpenAI-style service (Gemini, Groq ...), tested with a fake service."""
import json

import pytest
import requests

from app import ai_assistant, ai_compat, translate


class FakeResponse:
    def __init__(self, status=200, chunks=None, body=None):
        self.status_code, self._chunks, self._body, self.text = status, chunks or [], body, json.dumps(body) if body else "error body"

    def iter_lines(self, decode_unicode=True):
        for c in self._chunks:
            yield "data: " + (c if isinstance(c, str) else json.dumps(c))
            yield ""

    def close(self):
        pass

    def json(self):
        return self._body


def delta(**kw):
    return {"choices": [{"delta": kw, "finish_reason": None}]}


def finish(reason):
    return {"choices": [{"delta": {}, "finish_reason": reason}]}


@pytest.fixture()
def free(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "free-key")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    return monkeypatch


def events(stream):
    return [json.loads(line) for line in stream]


# --------------------------------------------------------------------- settings
def test_presets_and_overrides(free):
    assert ai_compat.settings() == ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.1-flash-lite,gemini-3.5-flash-lite,gemini-3.8-flash", "free-key")
    free.setenv("AI_PROVIDER", "groq")
    assert ai_compat.settings()[:2] == ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile")
    free.setenv("AI_MODEL", "openai/gpt-oss-120b")
    assert ai_compat.settings()[1] == "openai/gpt-oss-120b"
    free.setenv("AI_PROVIDER", "custom"); free.setenv("AI_BASE_URL", "https://llm.example.com/v1/")
    assert ai_compat.settings()[0] == "https://llm.example.com/v1"


def test_provider_choice(free):
    assert ai_assistant.provider() == "compat" and ai_assistant.enabled()
    assert ai_assistant.model_name().startswith("gemini-3.1-flash-lite")
    free.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert ai_assistant.provider() == "anthropic"            # a Claude key is used first
    free.setenv("AI_PROVIDER", "groq")
    assert ai_assistant.provider() == "compat"               # unless another provider is chosen on purpose
    free.delenv("ANTHROPIC_API_KEY"); free.delenv("AI_API_KEY"); free.delenv("AI_PROVIDER")
    assert ai_assistant.provider() is None and not ai_assistant.enabled()


def test_tool_schemas_are_reduced_to_what_providers_accept():
    tools = ai_compat.tool_list()
    assert len(tools) == 16 and all(t["type"] == "function" for t in tools)
    text = json.dumps(tools)
    for banned in ("pattern", "anyOf", "$ref", "minimum", "additionalProperties", '"default"'):
        assert banned not in text, banned
    goal = next(t for t in tools if t["function"]["name"] == "plan_goal")["function"]["parameters"]
    assert goal["properties"]["monthly_income"] == {"type": "number"} and goal["required"] == ["target", "years"]


# -------------------------------------------------------------------- streaming
def test_tool_round_trip(free):
    sent = []
    rounds = [
        [delta(tool_calls=[{"index": 0, "id": "call_1", "function": {"name": "calculate_income_tax", "arguments": ""},
                           "extra_content": {"google": {"thought_signature": "SIG"}}}]),
         delta(tool_calls=[{"index": 0, "function": {"arguments": '{"gross_income": 15'}}]),
         delta(tool_calls=[{"index": 0, "function": {"arguments": '00000}'}}]), finish("tool_calls")],
        [delta(content="The new regime "), delta(content="costs 97,500."), finish("stop")],
    ]

    def fake_post(url, json=None, headers=None, stream=None, timeout=None):
        sent.append((url, json, headers))
        return FakeResponse(chunks=rounds[len(sent) - 1])
    free.setattr(requests, "post", fake_post)
    ev = events(ai_compat.chat_stream([{"role": "user", "content": "tax on 15 lakh?"}], {"watchlist": ["TCS.NS"]}, "hi"))
    assert [e["type"] for e in ev] == ["tool", "text", "text", "text", "done"]
    assert ev[0]["name"] == "calculate_income_tax" and "".join(e.get("text", "") for e in ev).strip().endswith("97,500.")

    url, first, headers = sent[0]
    assert url == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert headers["Authorization"] == "Bearer free-key" and first["model"] == "gemini-3.1-flash-lite" and first["stream"] is True
    assert "Hindi" in first["messages"][0]["content"] and "TCS.NS" in first["messages"][0]["content"]
    second = sent[1][1]["messages"]
    assistant, tool = second[-2], second[-1]
    assert assistant["tool_calls"][0]["extra_content"] == {"google": {"thought_signature": "SIG"}}    # echoed back for Gemini 3
    assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {"gross_income": 1500000}
    assert tool["role"] == "tool" and tool["tool_call_id"] == "call_1"
    assert json.loads(tool["content"])["new_regime"]["total_tax"] == pytest.approx(97_500)


def test_parallel_calls_even_when_the_provider_reuses_index_zero(free):
    sent = []
    rounds = [
        [delta(tool_calls=[{"index": 0, "id": "a", "function": {"name": "lookup_finance_term", "arguments": '{"term": "RSI"}'}}]),
         delta(tool_calls=[{"index": 0, "id": "b", "function": {"name": "lookup_finance_term", "arguments": '{"term": "EMI"}'}}]), finish("tool_calls")],
        [delta(content="done"), finish("stop")]]
    free.setattr(requests, "post", lambda *a, **k: sent.append(k["json"]) or FakeResponse(chunks=rounds[len(sent) - 1]))
    events(ai_compat.chat_stream([{"role": "user", "content": "explain both"}]))
    tool_msgs = [m for m in sent[1]["messages"] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["a", "b"]
    assert "overbought" in json.loads(tool_msgs[0]["content"])["answer"]


def test_a_bad_tool_input_is_returned_to_the_model_not_raised(free):
    sent = []
    rounds = [[delta(tool_calls=[{"index": 0, "id": "x", "function": {"name": "calculate_loan_emi", "arguments": "{broken json"}}]), finish("tool_calls")],
              [delta(content="Sorry, let me retry."), finish("stop")]]
    free.setattr(requests, "post", lambda *a, **k: sent.append(k["json"]) or FakeResponse(chunks=rounds[len(sent) - 1]))
    ev = events(ai_compat.chat_stream([{"role": "user", "content": "emi?"}]))
    assert ev[-1]["type"] == "done" and not any(e["type"] == "error" for e in ev)
    assert "INVALID_INPUT" in [m for m in sent[1]["messages"] if m["role"] == "tool"][0]["content"]


@pytest.mark.parametrize("status,words", [(401, "rejected the API key"), (429, "free allowance"), (500, "returned an error")])
def test_provider_errors_become_friendly_messages(free, status, words):
    free.setattr(requests, "post", lambda *a, **k: FakeResponse(status=status))
    ev = events(ai_compat.chat_stream([{"role": "user", "content": "hi"}]))
    assert ev[0]["type"] == "error" and words in ev[0]["message"] and ev[-1]["type"] == "done"


def test_no_connection(free):
    def boom(*a, **k):
        raise requests.ConnectionError("down")
    free.setattr(requests, "post", boom)
    assert "Could not reach" in events(ai_compat.chat_stream([{"role": "user", "content": "hi"}]))[0]["message"]


def test_runaway_tool_loops_stop(free):
    call = [delta(tool_calls=[{"index": 0, "id": "z", "function": {"name": "lookup_finance_term", "arguments": '{"term": "RSI"}'}}]), finish("tool_calls")]
    free.setattr(requests, "post", lambda *a, **k: FakeResponse(chunks=call))
    ev = events(ai_compat.chat_stream([{"role": "user", "content": "loop"}]))
    assert sum(e["type"] == "tool" for e in ev) == ai_assistant.MAX_TOOL_ROUNDS
    assert "Stopped after several" in "".join(e.get("text", "") for e in ev)


# ----------------------------------------------------- JSON mode and translation
def test_json_answers_with_code_fences_and_a_provider_without_json_mode(free):
    calls = []

    def fake_post(url, json=None, **k):
        calls.append(json)
        if "response_format" in json:
            return FakeResponse(status=400)
        return FakeResponse(body={"choices": [{"message": {"content": '```json\n{"items": [{"term": "T", "q": "Q", "a": "A", "example": ""}]}\n```'}}]})
    free.setattr(requests, "post", fake_post)
    assert ai_compat.complete_json("sys", "user") == {"items": [{"term": "T", "q": "Q", "a": "A", "example": ""}]}
    assert "response_format" in calls[0] and "response_format" not in calls[1]


def test_translation_uses_the_free_provider(free):
    free.setattr(requests, "post", lambda *a, **k: FakeResponse(body={"choices": [{"message": {"content": json.dumps(
        {"items": [{"term": "EMI", "q": "ईएमआई क्या है?", "a": "...", "example": ""}]})}}]}))
    out = translate.translate_batch("hi", [{"term": "EMI", "q": "What is EMI?", "a": "x", "example": ""}])
    assert out[0]["q"] == "ईएमआई क्या है?"


# ----------------------------------------------------------------- the endpoint
def test_endpoint_end_to_end_on_the_free_provider(client, free):
    free.setattr(requests, "post", lambda *a, **k: FakeResponse(chunks=[delta(content="Hello from a free model"), finish("stop")]))
    status = client.get("/assistant/ai-status").json()
    assert status["enabled"] and status["provider"] == "compat" and status["model"].startswith("gemini-3.1-flash-lite")
    r = client.post("/assistant/ai-chat", json={"messages": [{"role": "user", "content": "hi"}]})
    ev = [json.loads(line) for line in r.text.splitlines() if line.strip()]
    assert any("free model" in e.get("text", "") for e in ev) and ev[-1]["type"] == "done"


# ---------------------------------------------------- several free models in turn
def test_models_are_tried_in_order_when_one_is_out_of_quota(free):
    free.setenv("AI_MODEL", "model-a,model-b,model-c")
    assert ai_compat.model_list() == ["model-a", "model-b", "model-c"]
    asked = []

    def fake_post(url, json=None, **k):
        asked.append(json["model"])
        if json["model"] in ("model-a", "model-b"):
            return FakeResponse(status=429)                        # daily allowance used up
        return FakeResponse(chunks=[delta(content="answer from c"), finish("stop")])
    free.setattr(requests, "post", fake_post)
    ev = events(ai_compat.chat_stream([{"role": "user", "content": "hi"}]))
    assert asked == ["model-a", "model-b", "model-c"]
    assert "answer from c" in "".join(e.get("text", "") for e in ev) and not any(e["type"] == "error" for e in ev)


def test_a_wrong_key_is_not_retried_on_other_models(free):
    free.setenv("AI_MODEL", "model-a,model-b")
    asked = []
    free.setattr(requests, "post", lambda url, json=None, **k: asked.append(json["model"]) or FakeResponse(status=401))
    ev = events(ai_compat.chat_stream([{"role": "user", "content": "hi"}]))
    assert asked == ["model-a"] and "rejected the API key" in ev[0]["message"]


def test_when_every_model_is_out_the_user_is_told(free):
    free.setenv("AI_MODEL", "model-a,model-b")
    free.setattr(requests, "post", lambda *a, **k: FakeResponse(status=429))
    assert "free allowance" in events(ai_compat.chat_stream([{"role": "user", "content": "hi"}]))[0]["message"]


def test_a_slow_model_is_skipped(free):
    free.setenv("AI_MODEL", "slow,fast")
    waits = []

    def fake_post(url, json=None, timeout=None, **k):
        waits.append((json["model"], timeout[1]))
        if json["model"] == "slow":
            raise requests.Timeout("no answer")
        return FakeResponse(chunks=[delta(content="ok"), finish("stop")])
    free.setattr(requests, "post", fake_post)
    ev = events(ai_compat.chat_stream([{"role": "user", "content": "hi"}]))
    assert [m for m, _ in waits] == ["slow", "fast"] and waits[0][1] == 40 and waits[1][1] == 120   # a short wait only while a spare model exists
    assert "ok" in "".join(e.get("text", "") for e in ev)


def test_later_rounds_stay_on_the_model_that_started_the_answer(free):
    free.setenv("AI_MODEL", "model-a,model-b")
    asked = []
    rounds = [[delta(tool_calls=[{"index": 0, "id": "t", "function": {"name": "lookup_finance_term", "arguments": '{"term": "RSI"}'}}]), finish("tool_calls")],
              [delta(content="done"), finish("stop")]]

    def fake_post(url, json=None, **k):
        asked.append(json["model"])
        if json["model"] == "model-a":
            return FakeResponse(status=503)
        return FakeResponse(chunks=rounds[len([m for m in asked if m == "model-b"]) - 1])
    free.setattr(requests, "post", fake_post)
    events(ai_compat.chat_stream([{"role": "user", "content": "explain"}]))
    assert asked == ["model-a", "model-b", "model-b"]


def test_json_answers_also_move_to_the_next_model(free):
    free.setenv("AI_MODEL", "model-a,model-b")
    asked = []

    def fake_post(url, json=None, **k):
        asked.append(json["model"])
        if json["model"] == "model-a":
            return FakeResponse(status=429)
        return FakeResponse(body={"choices": [{"message": {"content": '{"items": []}'}}]})
    free.setattr(requests, "post", fake_post)
    assert ai_compat.complete_json("s", "u") == {"items": []} and asked == ["model-a", "model-b"]
