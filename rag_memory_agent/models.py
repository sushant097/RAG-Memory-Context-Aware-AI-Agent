from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

from .config import (
    GOOGLE_API_KEY, GEMINI_MODEL_DECISION, GEMINI_MODEL_PERCEPTION, EMBED_MODEL, FAISS_DIR, DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP, RECENCY_ALPHA
)

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