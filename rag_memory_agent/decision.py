from __future__ import annotations
from .models import PerceptionOut, MemoryItem
from .config import GEMINI_API_KEY, GEMINI_MODEL_DECISION

_client = None
def _gemini_client_once():
    global _client
    if _client is None:
        import google.genai as genai  # lazy import (only when key exists)
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

_DECISION_SYSTEM = """You are a planner for an agent with tools.
Always output exactly ONE of:
1) FUNCTION_CALL: <tool_name>|arg1="..."|arg2=...
2) FINAL_ANSWER: <one line answer>

Prefer calling search_documents for user queries.
Use index_page only when the user explicitly provides content to index.
No extra prose, no code blocks.
"""

def _fallback_decide(p: PerceptionOut, recent_memory: list[MemoryItem]) -> str:
    # Deterministic planner if no Gemini key is present
    if p.intent == "semantic_search":
        return f'FUNCTION_CALL: search_documents|query="{p.cleaned_query}"|top_k=5'
    if p.intent == "index":
        # Fallback assumes 'cleaned_query' carries text to index if user typed "index <text>"
        return f'FUNCTION_CALL: index_page|url=""|title=""|text="{p.cleaned_query}"'
    # Basic QA fallback — route to search too
    return f'FUNCTION_CALL: search_documents|query="{p.cleaned_query}"|top_k=5'

def decide(p: PerceptionOut, recent_memory: list[MemoryItem]) -> str:
    # If no key, use deterministic fallback
    if not GEMINI_API_KEY:
        return _fallback_decide(p, recent_memory)

    # Gemini planner
    try:
        ctx = "\n".join(f"- {m.type}: {m.content[:120]}" for m in recent_memory[-6:])
        user = f"Intent={p.intent}; ToolHint={p.tool_hint}; Query={p.cleaned_query}"
        prompt = f"{_DECISION_SYSTEM}\n\nRecent:\n{ctx}\n\nUser:\n{user}\n"
        client = _gemini_client_once()
        resp = client.models.generate_content(
            model=GEMINI_MODEL_DECISION,
            contents=[{"role":"user","parts":[{"text":prompt}]}],
            config={"temperature":0.2}
        )
        out = (resp.text or "").strip()
        if not out:
            return _fallback_decide(p, recent_memory)  # empty response → fallback
        return out
    except Exception:
        # Rate limits, network errors, etc.
        return _fallback_decide(p, recent_memory)
