# Centralized configuration
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env once at startup
load_dotenv()

# ---------- Base paths ----------
ROOT = Path(__file__).resolve().parent.parent
FAISS_DIR = Path(os.getenv("FAISS_DIR", ROOT / "faiss_index"))
DOCS_DIR  = Path(os.getenv("DOCS_DIR", ROOT / "documents"))

# ---------- Model / API keys ----------
GOOGLE_API_KEY      = os.getenv("GOOGLE_API_KEY", "")
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", GOOGLE_API_KEY)  # fallback
GEMINI_MODEL_DECISION   = os.getenv("GEMINI_MODEL_DECISION", "gemini-2.0-flash")
GEMINI_MODEL_PERCEPTION = os.getenv("GEMINI_MODEL_PERCEPTION", "gemini-2.0-flash")

# ---------- Embeddings ----------
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "ollama").lower()  # "google" or "ollama"

# --- Google Embeddings ---
GOOGLE_EMBED_MODEL = os.getenv("GOOGLE_EMBED_MODEL", "text-embedding-004")

# --- Ollama Embeddings ---
EMBED_URL   = os.getenv("EMBED_URL", "http://localhost:11434/api/embeddings")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# ---------- Chunking / Index ----------
CHUNK_SIZE      = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP   = int(os.getenv("CHUNK_OVERLAP", "160"))
RECENCY_ALPHA   = float(os.getenv("RECENCY_ALPHA", "0.05"))

# ---------- Optional tuning ----------
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "100"))  # for Google
MAX_CHUNKS_PER_DOC = int(os.getenv("MAX_CHUNKS_PER_DOC", "500"))

# ---------- Derived paths ----------
INDEX_PATH = FAISS_DIR / "index.bin"
META_PATH  = FAISS_DIR / "metadata.jsonl"

FAISS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
