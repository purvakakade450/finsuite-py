"""The HTTP API, the AI assistant's tools and limits, and the web page itself."""
import json
import re
from pathlib import Path

import pytest

from app import ai_assistant, limits, store
from app.glossary import GLOSSARY

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


# ------------------------------------------------------------------ the API
def test_calculator_endpoints(client):
    assert client.post("/ratios/roe", json={"net_income": 100, "equity": 500}).json() == {"roe_pct": 20.0}
    assert client.post("/ratios/roe", json={"net_income": 1, "equity": 0}).status_code == 422
    tax = client.post("/tax/income", json={"gross_income": 1_500_000}).json()
    assert round(tax["new"]["total_tax"]) == 97_500 and tax["better"] in ("new", "old", "same")
    emi = client.post("/loans/emi", json={"principal": 2_500_000, "annual_rate": 8.5, "tenure_months": 240}).json()
    assert abs(emi["emi"] - 21_696) < 2
    assert client.post("/loans/emi", json={"principal": -1, "annual_rate": 8, "tenure_months": 12}).status_code == 422
    b = client.post("/budget", json={"income": 80_000, "items": [{"category": "Rent", "amount": 20_000, "kind": "need"}]}).json()
    assert b["income"] == 80_000
    assert client.post("/budget", json={"income": 1, "items": [{"category": "x", "amount": 1, "kind": "bad"}]}).status_code == 422


def test_knowledge_center_and_about(client):
    g = client.get("/knowledge/glossary").json()["glossary"]
    assert len(g) == len(GLOSSARY) >= 95
    about = client.get("/about").json()
    assert about["version"] and len(about["sections"]) >= 20


def test_api_validates_query_parameters(client):
    assert client.get("/market/indicators?symbol=X&period=bogus").status_code == 422
    assert client.get("/market/fx?base=USDX").status_code == 422
    assert client.get("/ml/predict?symbol=X&period=10y").status_code == 422


def test_cors_only_allows_finsuite_sites(client):
    ok = client.options("/about", headers={"Origin": "https://finsuite.co.in", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "https://finsuite.co.in"
    bad = client.options("/about", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_large_responses_are_compressed(client):
    r = client.get("/knowledge/glossary", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"


def test_page_files_are_versioned_and_cacheable(client):
    page = client.get("/")
    assert page.headers["cache-control"] == "no-cache"
    files = re.findall(r'(?:src|href)="(/static/[^"?]+\?v=\d+)"', page.text)
    assert any(f.endswith(".css") or ".css?" in f for f in files) and any(".js?" in f for f in files)
    asset = client.get(files[0])
    assert asset.status_code == 200 and "immutable" in asset.headers["cache-control"]
    plain = client.get(files[0].split("?")[0])
    assert plain.headers["cache-control"] == "no-cache"


# ------------------------------------------------------------ the web page
def test_every_tab_has_a_panel_and_numbers_run_01_to_24():
    tabs = re.findall(r'<button class="tab[^"]*" data-tab="(\w+)">(\d\d) ', INDEX)
    assert [n for _, n in tabs] == [f"{i:02d}" for i in range(1, len(tabs) + 1)]
    assert len(tabs) == 24
    for name, _ in tabs:
        assert f'id="panel-{name}"' in INDEX, name
    assert INDEX.count('class="tab active"') == 1 and INDEX.count('class="panel active"') == 1


def test_every_info_icon_resolves_to_a_knowledge_center_entry():
    keys = set()
    for g in GLOSSARY:
        m = re.match(r"^(.*?)\s*\((.*)\)\s*$", g["term"])
        for k in [g["term"], *( [m.group(1), m.group(2)] if m else [] ), *g.get("also", [])]:
            keys.add(k.lower().strip())
    for term in set(re.findall(r'data-term="([^"]+)"', INDEX)):
        t = term.lower().strip()
        assert t in keys or any(k.startswith(t) for k in keys), f"no Knowledge Center entry for {term!r}"


def test_no_duplicate_element_ids():
    ids = re.findall(r'\bid="([^"]+)"', INDEX)
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, dupes


# ------------------------------------------------------- AI assistant tools
def test_tool_schemas_are_plain_objects():
    assert len(ai_assistant.TOOL_DEFS) == len(ai_assistant.TOOLS) >= 16
    for t in ai_assistant.TOOL_DEFS:
        assert t["input_schema"]["type"] == "object" and "$ref" not in json.dumps(t["input_schema"])
        assert t["description"] and t["name"].replace("_", "").isalnum()


def test_pure_tools_run_offline():
    text, err = ai_assistant.run_tool("calculate_income_tax", {"gross_income": 1_500_000})
    assert not err and json.loads(text)["new_regime"]["total_tax"] == pytest.approx(97_500)
    text, err = ai_assistant.run_tool("calculate_loan_emi", {"principal": 2_500_000, "annual_rate": 8.5, "tenure_months": 240})
    assert not err and abs(json.loads(text)["emi"] - 21_696) < 2
    text, err = ai_assistant.run_tool("lookup_finance_term", {"term": "XIRR"})
    assert not err and "dates" in json.loads(text)["answer"]
    text, err = ai_assistant.run_tool("analyse_budget", {"income": 50_000, "items": [{"category": "Rent", "amount": 20_000, "kind": "need"}]})
    assert not err and json.loads(text)["income"] == 50_000


def test_bad_tool_input_is_reported_to_the_model_not_raised():
    text, err = ai_assistant.run_tool("calculate_loan_emi", {"principal": "lots"})
    assert err and "INVALID_INPUT" in text
    text, err = ai_assistant.run_tool("no_such_tool", {})
    assert err
    text, err = ai_assistant.run_tool("calculate_loan_emi", {"principal": 0, "annual_rate": 8, "tenure_months": 12})
    assert err and "must be positive" in text            # a ValueError from the calculator


# -------------------------------------------------------- AI endpoint + caps
def _ndjson(response):
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_without_a_key_the_chat_falls_back_to_the_knowledge_center(client):
    r = client.post("/assistant/ai-chat", json={"messages": [{"role": "user", "content": "what is RSI"}]})
    events = _ndjson(r)
    assert events[0]["type"] == "notice" and events[-1]["type"] == "done"
    assert any("overbought" in e.get("text", "") for e in events)
    assert client.get("/assistant/ai-status").json()["enabled"] is False


def test_conversation_must_end_with_a_user_message(client):
    r = client.post("/assistant/ai-chat", json={"messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]})
    assert r.status_code == 422
    big = {"role": "user", "content": "x" * 19_000}
    assert client.post("/assistant/ai-chat", json={"messages": [big, {"role": "assistant", "content": big["content"]}, big]}).status_code == 413


@pytest.fixture()
def ai_on(monkeypatch):
    monkeypatch.setattr(ai_assistant, "enabled", lambda: True)
    monkeypatch.setattr(ai_assistant, "chat_stream", lambda *a, **k: iter(['{"type": "text", "text": "hi"}\n', '{"type": "done"}\n']))
    monkeypatch.setattr(limits, "ENABLED", True)
    limits.LIMITER._hits.clear()
    with store.db() as conn:
        conn.execute("DELETE FROM counters")


def test_guests_have_a_daily_ai_limit(client, ai_on, monkeypatch):
    monkeypatch.setattr(limits, "AI_PER_IP_DAILY", 2)
    monkeypatch.setattr(limits, "AI_PER_MIN", 100)
    body = {"messages": [{"role": "user", "content": "hello"}]}
    codes = [client.post("/assistant/ai-chat", json=body).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    r = client.post("/assistant/ai-chat", json=body)
    assert "Log in" in r.json()["detail"]


def test_logged_in_users_get_their_own_higher_limit(client, ai_on, user, monkeypatch):
    monkeypatch.setattr(limits, "AI_PER_IP_DAILY", 0)         # guests blocked outright
    monkeypatch.setattr(limits, "AI_PER_USER_DAILY", 2)
    monkeypatch.setattr(limits, "AI_PER_MIN", 100)
    body = {"messages": [{"role": "user", "content": "hello"}]}
    assert client.post("/assistant/ai-chat", json=body).status_code == 429
    assert [client.post("/assistant/ai-chat", json=body, headers=user["headers"]).status_code for _ in range(3)] == [200, 200, 429]


def test_site_wide_daily_cap(client, ai_on, user, monkeypatch):
    monkeypatch.setattr(limits, "AI_DAILY_LIMIT", 1)
    monkeypatch.setattr(limits, "AI_PER_MIN", 100)
    body = {"messages": [{"role": "user", "content": "hello"}]}
    assert client.post("/assistant/ai-chat", json=body, headers=user["headers"]).status_code == 200
    r = client.post("/assistant/ai-chat", json=body, headers=user["headers"])
    assert r.status_code == 429 and "limit for today" in r.json()["detail"]
