# rag_memory_agent/perception.py
from __future__ import annotations
import json
from .models import PerceptionOut
from .config import GEMINI_API_KEY, GEMINI_MODEL_PERCEPTION
# We'll import google.genai only if a key exists
_client = None

def _gemini_client_once():
    global _client
    if _client is None:
        import google.genai as genai  # lazy import (only when key exists)
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

_GEMINI_PROMPT = """You extract normalized search intents for a web-memory RAG agent.
Return compact JSON ONLY with keys: cleaned_query, intent, tool_hint.
- intents: "semantic_search" (default), "index" (explicit index request), or "qa".
- tool_hint: "search_documents" for search; "index_page" for indexing.
Examples:
User: "index https://mysite/notes — content: my personal notes on FAISS"
-> {"cleaned_query":"https://mysite/notes — content: my personal notes on FAISS","intent":"index","tool_hint":"index_page"}
User: "find IVF vs HNSW explanation"
-> {"cleaned_query":"IVF vs HNSW explanation","intent":"semantic_search","tool_hint":"search_documents"}
JSON:
"""

def _fallback_perception(text: str) -> PerceptionOut:
    t = (text or "").strip()
    tl = t.lower()
    if tl.startswith("index "):
        return PerceptionOut(cleaned_query=t[6:].strip(), intent="index", tool_hint="index_page")
    # You can add more patterns here if you’d like
    return PerceptionOut(cleaned_query=t, intent="semantic_search", tool_hint="search_documents")

def perceive(text: str) -> PerceptionOut:
    # If no key, use manual fallback
    if not GEMINI_API_KEY:
        return _fallback_perception(text)

    # Gemini path
    try:
        client = _gemini_client_once()
        prompt = _GEMINI_PROMPT.replace("JSON:\n", f"User: {text}\nJSON:\n")
        resp = client.models.generate_content(
            model=GEMINI_MODEL_PERCEPTION,
            contents=[{"role":"user","parts":[{"text":prompt}]}],
            config={"temperature":0.2}
        )
        raw = (resp.text or "{}").strip()
        data = json.loads(raw)
        return PerceptionOut(
            cleaned_query=data.get("cleaned_query", (text or "").strip()),
            intent=data.get("intent", "semantic_search"),
            tool_hint=data.get("tool_hint", "search_documents"),
        )
    except Exception:
        # If Gemini errors (rate limit/network/etc.), gracefully fall back
        return _fallback_perception(text)
