from __future__ import annotations
from .models import PerceptionOut, GOOGLE_API_KEY, GEMINI_MODEL_PERCEPTION
import google.genai as genai
import json

_client = None

def _client_once():
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client

SYSTEM_PROMPT = """You extract normalized search intents for a web-memory RAG agent.
Return compact JSON only with keys: cleaned_query, intent, tool_hint.
intents: "semantic_search" (default), "index" (if explicit), or "qa".
tool_hint: "search_documents" for search; "index_page" for indexing.
"""

def perceive(text: str) -> PerceptionOut:
    client = _client_once()
    prompt = f"""{SYSTEM_PROMPT}
    User text:
    {text}
    JSON:"""
    resp = client.models.generate_content(
        model = GEMINI_MODEL_PERCEPTION,
        contents=[{"role": "user", "parts": [{"text": prompt}]}]
    )
    raw = (resp.text or "{}").strip()
    # very tolerant tiny parser
    
    try:
        data = json.loads(raw)
        return PerceptionOut(
            cleaned_query=data.get("cleaned_query", text.strip()),
            intent=data.get("intent", "semantic_search"),
            tool_hint=data.get("tool_hint", "search_documents"),
        )
    except Exception:
        return PerceptionOut(
            cleaned_query=text.strip(),
            intent="semantic_search",
            tool_hint="search_documents",
        )
