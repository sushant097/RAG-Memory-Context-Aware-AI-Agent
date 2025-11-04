from __future__ import annotations
import os, json, time, hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

import numpy as np
import faiss
import math


from .config import (
    FAISS_DIR, INDEX_PATH, MAX_CHUNKS_PER_DOC, META_PATH, EMBEDDINGS_PROVIDER,
    GOOGLE_API_KEY, EMBED_URL, EMBED_MODEL,
    GOOGLE_EMBED_MODEL, EMBED_BATCH_SIZE,
    CHUNK_SIZE, CHUNK_OVERLAP, 
    HALF_LIFE_DAYS, FRESHNESS_WEIGHT, POPULARITY_WEIGHT, MAX_TEMPORAL_BOOST, SIM_WEIGHT,
    TEMP_WEIGHT
)
# ---------- Embeddings ----------
_embedder = None

def _embed_batch(texts: List[str]) -> np.ndarray:
    """
    Returns L2-normalized float32 embeddings for texts.
    Provider controlled by EMBEDDINGS_PROVIDER env var:
      - ollama  → local http://localhost:11434/api/embeddings
      - google  → via GoogleGenAIEmbedding (llama_index-embeddings-google-genai)
    """
    global _embedder
    if EMBEDDINGS_PROVIDER == "google":
        if _embedder is None:
            try:
                from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
            except ImportError:
                raise ImportError(
                    "GoogleGenAIEmbedding not found. "
                    "Install with: pip install llama-index-embeddings-google-genai"
                )
            
            _embedder = GoogleGenAIEmbedding(
                model_name=GOOGLE_EMBED_MODEL,
                embed_batch_size=EMBED_BATCH_SIZE,  # safe batch size for API
                )
        vecs = _embedder.get_text_embedding_batch(texts)
        arr = np.array(vecs, dtype="float32")
    else:
        # ---------- Ollama local embeddings ----------
        import requests
        arr = []
        for t in texts:
            r = requests.post(
                EMBED_URL,
                json={"model": EMBED_MODEL, "prompt": t},
                timeout=60,
            )
            r.raise_for_status()
            v = np.array(r.json()["embedding"], dtype="float32")
            arr.append(v)
        arr = np.stack(arr, axis=0)

    # normalize for cosine/IP equivalence
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return arr / norms

# ---------- FAISS + metadata ----------
_index: faiss.Index | None = None
_meta:  List[Dict[str, Any]] = []

def _load():
    """Load index + metadata into memory (lazy)."""
    global _index, _meta
    if INDEX_PATH.exists():
        _index = faiss.read_index(str(INDEX_PATH))
    else:
        _index = None
    if META_PATH.exists():
        with META_PATH.open("r", encoding="utf-8") as f:
            _meta = [json.loads(line) for line in f]
    else:
        _meta = []

def _save():
    """Persist index + metadata."""
    if _index is not None:
        faiss.write_index(_index, str(INDEX_PATH))
    with META_PATH.open("w", encoding="utf-8") as f:
        for row in _meta:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def _ensure_loaded():
    global _index
    if _index is None:
        _load()

def _append(vecs: np.ndarray, rows: List[Dict[str, Any]]):
    global _index, _meta
    if _index is None:
        dim = vecs.shape[1]
        # Use IP (cosine-equivalent due to normalization)
        _index = faiss.IndexFlatIP(dim)
    _index.add(vecs)
    _meta.extend(rows)
    _save()

# ---------- Chunking ----------
def _chunks(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    i = 0
    n = len(text)
    while i < n:
        yield i, text[i:i+size]
        i += max(1, size - overlap)

# ---------- Core functions ----------
def visit_url_core(url: str) -> dict:
    """
    Increment visit count and update last_seen for all chunks of this URL.
    Creates no new vectors; just updates metadata and persists.
    Returns {ok, url, visits} where visits is the max count across this URL's chunks.
    """
    _ensure_loaded()
    now_iso = datetime.utcnow().isoformat() + "Z"
    found = False
    max_visits = 0
    for row in _meta:
        if row.get("url") == url:
            found = True
            row["last_seen"] = now_iso
            v = int(row.get("visits", 0)) + 1
            row["visits"] = v
            max_visits = max(max_visits, v)

    if not found:
        return {"ok": False, "url": url, "visits": 0, "reason": "url_not_indexed"}

    _save()
    return {"ok": True, "url": url, "visits": max_visits}

# ---------- Public core APIs ----------
def index_page_core(url: str, title: str, text: str) -> Dict[str, Any]:
    """
    Chunk -> embed -> append to FAISS; write metadata.jsonl
    Returns {ok, indexed_chunks, url, title}
    """
    _ensure_loaded()
    ts = datetime.utcnow().isoformat() + "Z"
    base = hashlib.sha1(url.encode()).hexdigest()[:10]

    rows, payloads = [], []
    existing = {m.get("chunk_hash") for m in _meta if "chunk_hash" in m}
    
    prior = [m for m in _meta if m.get("url") == url]
    prior_visits = max([int(m.get("visits", 0)) for m in prior], default=0)
    visits_init = max(1, prior_visits)  # keep at least 1


    for off, chunk in _chunks(text):
        if len(rows) >= MAX_CHUNKS_PER_DOC:
            break
        ch = hashlib.sha1((url + str(off) + chunk).encode()).hexdigest()[:16]
        if ch in existing:
            continue
        rows.append({
            "url": url,
            "title": title,
            "timestamp": ts,
            "chunk_id": f"{base}#c{len(rows):04d}",
            "offset_start": off,
            "snippet": chunk[:240],
            "chunk_hash": ch,
            "chunk": chunk,
            "visits": visits_init,
            "last_seen": ts
        })
        payloads.append(chunk)

    if not payloads:
        return {"ok": True, "indexed_chunks": 0, "url": url, "title": title}

    vecs = _embed_batch(payloads)
    _append(vecs, rows)
    return {"ok": True, "indexed_chunks": len(rows), "url": url, "title": title}

def search_documents_core(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Embed query -> FAISS -> recency re-rank -> top_k dicts
    [{url,title,snippet,chunk_id,score,timestamp}]
    """
    _ensure_loaded()
    if _index is None or _index.ntotal == 0:
        return []
    qv = _embed_batch([query])
    D, I = _index.search(qv, top_k * 4)  # oversample for recency re-rank

    now = time.time()
    hits: List[Dict[str, Any]] = []
    for idx, sim in zip(I[0], D[0]):
        if idx < 0 or idx >= len(_meta):
            continue
        m = _meta[idx]
        ts = m.get("timestamp")
        try:
            ts_sec = datetime.fromisoformat(ts.replace("Z","")).timestamp() if ts else now
        except Exception:
            ts_sec = now
        days = max(0.0, (now - ts_sec) / 86400.0)
        
        # 1) Freshness (exponential decay): 1.0 today, 0.5 after HALF_LIFE_DAYS, 0.25 after 2*half-life, etc.
        lambda_   = math.log(2) / max(1e-6, HALF_LIFE_DAYS)
        freshness = math.exp(-lambda_ * days)  # [0..1], higher = newer

        # 2) Popularity (smoothly saturating with visits; ~0 for never, →1 as visits grow)
        visits      = float(m.get("visits", 1))
        popularity  = 1.0 - math.exp(-visits / 3.0)  # 3 is a soft scale; tweak if needed

        # 3) Blend (weights sum ≤ 1); keep a tiny floor so recency can help even with no visits
        hybrid = FRESHNESS_WEIGHT * freshness + POPULARITY_WEIGHT * popularity  # in [0..1]

        # 4) Cap total temporal boost for stability (e.g., ≤ +25%)
        # boost = 1.0 + min(MAX_TEMPORAL_BOOST, MAX_TEMPORAL_BOOST * hybrid)

        # score = float(sim * boost)
        # Weighted blend (semantics dominate)
        final = (SIM_WEIGHT * float(sim)) + (TEMP_WEIGHT * float(hybrid))
        score = float(final)

        hits.append({
            "url": m.get("url",""),
            "title": m.get("title",""),
            "snippet": m.get("snippet") or m.get("chunk","")[:240],
            "chunk_id": m.get("chunk_id",""),
            "score": score,
            "timestamp": ts or datetime.utcfromtimestamp(now).isoformat() + "Z"
        })

    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits[:top_k]

def process_documents_core(directory: str) -> Dict[str, Any]:
    """
    Batch ingest from a folder: convert to text via MarkItDown, then index.
    """
    from markitdown import MarkItDown
    md = MarkItDown()
    added = 0
    for root, _, files in os.walk(directory):
        for f in files:
            if f.startswith("."):
                continue
            path = Path(root) / f
            try:
                r = md.convert(str(path))
                text = r.text_content or ""
                if not text.strip():
                    continue
                url = str(path)
                title = path.stem
                added += index_page_core(url, title, text)["indexed_chunks"]
            except Exception:
                continue
    return {"ok": True, "indexed_chunks": added}
