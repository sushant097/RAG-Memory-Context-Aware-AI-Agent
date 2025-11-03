from __future__ import annotations
import os, json, time, hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

import numpy as np
import faiss

# ---------- Config ----------
ROOT = Path(__file__).parent.parent.resolve()
FAISS_DIR = Path(os.getenv("FAISS_DIR", ROOT / "faiss_index"))
FAISS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = FAISS_DIR / "index.bin"
META_PATH  = FAISS_DIR / "metadata.jsonl"

CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "160"))
RECENCY_ALPHA = float(os.getenv("RECENCY_ALPHA", "0.05"))

EMBED_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "ollama").lower()  # "ollama" | "google"
# Ollama
EMBED_URL   = os.getenv("EMBED_URL", "http://localhost:11434/api/embeddings")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
# Google (via LlamaIndex)
GOOGLE_EMBED_MODEL = os.getenv("GOOGLE_EMBED_MODEL", "text-embedding-004")

# ---------- Embeddings ----------
_embedder = None

def _embed_batch(texts: List[str]) -> np.ndarray:
    """
    Returns L2-normalized float32 embeddings for `texts`.
    Provider controlled by EMBEDDINGS_PROVIDER env.
    """
    global _embedder
    if EMBED_PROVIDER == "google":
        # Lazy init LlamaIndex Google embedder
        if _embedder is None:
            from llama_index.embeddings.google import GoogleGenerativeAIEmbedding
            _embedder = GoogleGenerativeAIEmbedding(model_name=GOOGLE_EMBED_MODEL)
        vecs = _embedder.get_text_embedding_batch(texts)
        arr = np.array(vecs, dtype="float32")
    else:
        # Ollama embeddings API
        import requests
        arr = []
        for t in texts:
            r = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "prompt": t}, timeout=60)
            r.raise_for_status()
            v = np.array(r.json()["embedding"], dtype="float32")
            arr.append(v)
        arr = np.stack(arr, axis=0)

    # L2 normalize for cosine/IP scoring
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

    for off, chunk in _chunks(text):
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
            "chunk": chunk
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
        boost = 1.0 + RECENCY_ALPHA * max(0.0, (30.0 - min(days, 30.0))) / 30.0
        score = float(sim * boost)

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
