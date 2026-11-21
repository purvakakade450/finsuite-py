"""
Hindi and Marathi for the Knowledge Center.

Each entry is translated once by the AI model and kept in the database, so
the cost is a one-off and later visits are instant. Until an entry is
translated the English text is shown. Needs the AI key (ANTHROPIC_API_KEY);
without it the Knowledge Center stays in English.
"""
from __future__ import annotations

import json
import logging
import os
import threading

from . import ai_assistant, store
from .glossary import GLOSSARY

log = logging.getLogger("finsuite.translate")

LANGS = {"hi": "Hindi", "mr": "Marathi"}
MODEL = os.environ.get("FINSUITE_TRANSLATE_MODEL", "claude-sonnet-5-5")
BATCH = 8

_running: set[str] = set()
_lock = threading.Lock()

_ITEM = {"type": "object", "properties": {"term": {"type": "string"}, "q": {"type": "string"},
                                          "a": {"type": "string"}, "example": {"type": "string"}},
         "required": ["term", "q", "a", "example"], "additionalProperties": False}
SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": _ITEM}},
          "required": ["items"], "additionalProperties": False}

PROMPT = """You translate a plain-language finance glossary for beginners in India into {language} (Devanagari script).

Rules:
- Translate q (the question), a (the explanation) and example. Keep the meaning and the simple tone; write the way a helpful teacher would speak, not literal word-for-word.
- Return every entry once, with its term field copied unchanged (the English term is the key).
- Keep numbers, rupee amounts (₹) and percentages exactly as written; keep common English abbreviations (ROE, ROA, EMI, SIP, NAV, RSI, XIRR, CAGR, ETF, NSE, BSE) and tickers in English letters.
- If example is an empty string, return an empty string."""


def _init() -> None:
    with store.db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS translations (lang TEXT NOT NULL, term TEXT NOT NULL, "
                     "data TEXT NOT NULL, PRIMARY KEY (lang, term))")


def cached(lang: str) -> dict[str, dict]:
    _init()
    with store.db() as conn:
        return {r["term"]: json.loads(r["data"])
                for r in conn.execute("SELECT term, data FROM translations WHERE lang=?", (lang,))}


def translate_batch(lang: str, entries: list[dict]) -> list[dict]:
    """Ask the model to translate up to BATCH entries. Returns [{term, q, a, example}]."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL, max_tokens=12000, system=PROMPT.format(language=LANGS[lang]),
        messages=[{"role": "user", "content": json.dumps(entries, ensure_ascii=False)}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)["items"]


def _translate_all(lang: str) -> None:
    try:
        done = cached(lang)
        todo = [g for g in GLOSSARY if g["term"] not in done]
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            items = translate_batch(lang, [{"term": g["term"], "q": g["q"], "a": g["a"], "example": g["example"] or ""}
                                           for g in chunk])
            wanted = {g["term"] for g in chunk}
            with store.db() as conn:
                for it in items:
                    if it["term"] in wanted:
                        conn.execute("INSERT INTO translations VALUES (?,?,?) ON CONFLICT(lang, term) DO UPDATE SET data=excluded.data",
                                     (lang, it["term"], json.dumps({k: it[k] for k in ("q", "a", "example")}, ensure_ascii=False)))
    except Exception as e:                      # try again on the next visit
        log.warning("translation to %s stopped: %s", lang, e)
    finally:
        with _lock:
            _running.discard(lang)


def ensure_async(lang: str) -> bool:
    """Start translating whatever is missing in the background. True if work is (or was already) running."""
    if lang not in LANGS or not ai_assistant.enabled():
        return False
    with _lock:
        if lang in _running:
            return True
        if not [g for g in GLOSSARY if g["term"] not in cached(lang)]:
            return False
        _running.add(lang)
    threading.Thread(target=_translate_all, args=(lang,), name=f"translate-{lang}", daemon=True).start()
    return True


def glossary(lang: str) -> dict:
    """The glossary with translated text where available."""
    pending = ensure_async(lang)
    done = cached(lang)
    entries = []
    for g in GLOSSARY:
        t = done.get(g["term"])
        entries.append({**g, **({"q": t["q"], "a": t["a"], "example": t["example"] or None, "translated": True}
                                if t else {"translated": False})})
    return {"glossary": entries, "lang": lang, "translated": len(done), "total": len(GLOSSARY),
            "pending": pending, "available": ai_assistant.enabled()}
