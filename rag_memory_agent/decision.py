from __future__ import annotations
from models import GOOGLE_API_KEY, GEMINI_MODEL_DECISION, PerceptionOut, MemoryItem
import google.genai as genai

_client = None

def _client_once():
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client

DECISION_SYSTEM_PROMPT = """You are a planner for an agent with tools.
Always output exactly ONE of:
1) FUNCTION_CALL: <tool_name>|arg1="..."|arg2=...
2) FINAL_ANSWER: <one line answer>

Prefer calling search_documents for user queries. Use index_page only when explicitly indexing content (handled by HTTP).
No extra prose, no code blocks.
"""

def decide(p: PerceptionOut, recent_memory: list[MemoryItem]) -> str:
    client = _client_once()
    ctx = "\n".join(f"- {m.type}: {m.content[:120]}" for m in recent_memory[-6:])
    user = f"Intent={p.intent}; ToolHint={p.tool_hint}; Query={p.cleaned_query}"
    prompt = f"{DECISION_SYSTEM_PROMPT}\n\nRecent:\n{ctx}\n\nUser:\n{user}\n"
    resp = client.models.generate_content(
        model = GEMINI_MODEL_DECISION,
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
        config={"temperature": 0.2}
    )
    out = (resp.text or "").strip()
    # last fallback
    if not out:
        out = f'FUNCTION_CALL: search_documents|query="{p.cleaned_query}"|top_k=5'
    return out