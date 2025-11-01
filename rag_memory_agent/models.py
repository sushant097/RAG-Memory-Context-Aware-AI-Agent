from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

# ------ Config (env-overridable) ------
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL_DECISION: str = os.getenv("GEMINI_MODEL_DECISION", "gemini-2.0-flash")
GEMINI_MODEL_PERCEPTION: str = os.getenv("GEMINI_MODEL_PERCEPTION", "gemini-2.0-flash")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-004")   # Google embeddings
FAISS_DIR: str = os.getenv("FAISS_DIR", "./faiss_index")
DOCS_DIR: str = os.getenv("DOCS_DIR", "./documents")
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "160"))
RECENCY_ALPHA: float = float(os.getenv("RECENCY_ALPHA", "0.05"))    # temporal weighting


# ------ HTTP/Tool IO Schemas ------
class IndexPageIn(BaseModel):
    url: str
    title: str
    text: str

class SearchHit(BaseModel):
    url: str
    title: str
    snippet: str
    chunk_id: str
    score: float
    timestamp: datetime

class PerceptionOut(BaseModel):
    cleaned_query: str
    intent: str                # "index" | "semantic_search" | "qa"
    tool_hint: Optional[str]   # e.g., "search_documents" | "index_page"


class MemoryItem(BaseModel):
    type: str                  # "query" | "fact" | "tool_output"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None