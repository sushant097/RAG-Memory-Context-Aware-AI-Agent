# 🧠 RAG with Memory — Agentic Web Memory Backend

A fully-agentic **AI memory system** built with `FastAPI`, `Gemini`, and `FAISS`.
It continuously **learns from the web pages you visit**, builds a **semantic memory** of them, and later **recalls the precise snippet and source** when you ask — functioning as your **personal, retrieval-augmented web memory agent**.

---

## 🚀 Concept

This project turns the classic RAG (Retrieval-Augmented Generation) pipeline into a **living memory system** — one that perceives, decides, acts, and remembers.

> “It doesn’t just search — it *remembers* what you read, when you read it, and where you saw it.”

You can think of it as a self-contained *AI hippocampus* for your browser.

---

## 🧩 Agentic Architecture

The backend follows the cognitive architecture:

> **Agent → Perception → Memory → Decision → Action**

Each layer mirrors a mental function, powered by **Gemini models** and **vector memory**.

```
Chrome Extension
     ↓
  HTTP API (FastAPI)
     ↓
   Core Logic
     ↓
  MCP Tools (index/search)
     ↓
  Agentic Loop (Gemini reasoning)
     ↓
  FAISS Vector Store (long-term memory)
```

| Layer          | Role                                                                                      |             |           |
| -------------- | ----------------------------------------------------------------------------------------- | ----------- | --------- |
| **Perception** | Gemini interprets text/query, classifies intent, and hints which tool to use.             |             |           |
| **Decision**   | Gemini planner outputs structured calls like `FUNCTION_CALL: search_documents             | query="..." | top_k=5`. |
| **Action**     | Executes the function, then writes the result back into short-term memory.                |             |           |
| **Memory**     | Maintains both *working memory* (session context) and *long-term FAISS memory*.           |             |           |
| **MCP Tools**  | Provide clean modular interfaces (`index_page`, `search_documents`, `process_documents`). |             |           |

---

## 🔬 Key Idea

Each webpage is broken into **semantic chunks**, embedded via **Google’s `text-embedding-004`** (or optionally local Nomic embeddings), and stored in a FAISS vector store.
When a user later asks a question, the system performs **semantic + temporal retrieval**, boosting newer content and returning the *exact snippet* and *URL* where it appeared.

---

## 💡 Example Scenario

1. You read multiple pages on *vector databases*.
2. Weeks later you ask:

   > “Which article explained IVF and HNSW in FAISS?”
3. The agent searches its memory and returns:

   ```
   “IVF and HNSW indexing accelerate large-scale similarity search...”
   [Source: https://example.com/vector-db, ID: a3c1_002]
   ```

   → The extension opens the page and highlights that text.

---

## 🧠 Core Features

| Feature                       | Description                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------ |
| **Gemini-Driven Reasoning**   | Both perception and decision use Gemini 2.0 Flash for intelligent planning.          |
| **Dual Embedding Backend**    | Supports *Google embeddings* for precision or *Ollama/Nomic* for offline use.        |
| **Temporal Awareness**        | Adds time-decay weighting: recent knowledge ranks higher in retrieval.               |
| **Deduplication**             | SHA-1 hashing avoids re-embedding duplicate content.                                 |
| **Hybrid Memory**             | Short-term (RAM) + long-term (FAISS) = contextual continuity.                        |
| **MCP + REST Dual Interface** | Accessible both as an MCP stdio toolset and as a FastAPI HTTP service.               |
| **Document Ingestion**        | Converts `.html`, `.pdf`, `.docx`, `.md` via MarkItDown for batch indexing.          |
| **Extension-Ready**           | `/index_page` and `/search` endpoints integrate directly with Chrome MV3 extensions. |

---

## ⚙️ Tech Stack

| Layer             | Technology                                 | Purpose                             |
| ----------------- | ------------------------------------------ | ----------------------------------- |
| **LLM**           | Gemini 2.0 Flash                           | Perception & decision reasoning     |
| **Embeddings**    | Google `text-embedding-004` / Ollama Nomic | Vector representations              |
| **Vector DB**     | FAISS                                      | Nearest-neighbor retrieval          |
| **Protocol**      | MCP (Model Context Protocol)               | Modular tool calls                  |
| **API**           | FastAPI                                    | Bridge for Chrome extension         |
| **Parsing**       | MarkItDown                                 | Clean text extraction from HTML/PDF |
| **Orchestration** | uv                                         | Modern Python dependency management |

---

## 🧮 Data & Memory Model

| Type                   | Description                                                       |
| ---------------------- | ----------------------------------------------------------------- |
| **Short-Term Memory**  | Session-scoped objects managed in RAM (`memory.py`).              |
| **Long-Term Memory**   | FAISS index + JSONL metadata with embeddings, titles, timestamps. |
| **Temporal Weighting** | `score = sim * (1 + α * freshness(days))` — prioritizes recency.  |
| **Metadata Schema**    | `{url, title, snippet, chunk_id, timestamp, score}`               |
| **Chunking**           | ~900 characters with 160-char overlap for semantic continuity.    |

---

## 📦 Repository Structure

```
rag_memory_agent/
├── core.py           # All FAISS, embedding, chunking, and indexing logic
├── mcp_tools.py      # MCP-decorated tools (index_page, search_documents)
├── http.py           # REST endpoints for Chrome extension
├── agent.py          # Orchestrator for Gemini-powered reasoning loop
├── perception.py     # Gemini perception layer (intent extraction)
├── decision.py       # Gemini decision layer (planner)
├── action.py         # Executes tool calls and manages output
├── memory.py         # Short-term session memory
├── models.py         # Config + Pydantic schemas
├── documents/        # Optional folder for batch ingestion
└── faiss_index/      # Persistent FAISS store + metadata.jsonl
```

---

## 🧭 Data Flow

### 🔹 Indexing

```
Chrome → POST /index_page
     ↓
FastAPI → core.index_page_core()
     ↓
Chunks → Embeddings → FAISS + metadata
```

### 🔹 Searching

```
User query → perception.py (Gemini)
     ↓
decision.py → FUNCTION_CALL: search_documents
     ↓
action.py → core.search_documents_core()
     ↓
FAISS search (semantic + temporal)
     ↓
Return URLs + snippets → highlight in Chrome
```

---

## 🏗️ Running the Backend

### 1️⃣ Environment & Install

```bash
uv venv
uv sync
```

### 2️⃣ Choose Embedding Provider

```bash
# A) Google (requires key)
export EMBEDDINGS_PROVIDER=google
export GOOGLE_API_KEY=your_key
# B) Local (Ollama)
ollama pull nomic-embed-text
ollama serve
```

### 3️⃣ Start API

```bash
uvicorn rag_memory_agent.http:app --reload --port 8000
```

### 4️⃣ Index & Search

```bash
curl -X POST http://localhost:8000/index_page \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com","title":"Example","text":"Vector DBs use IVF, HNSW..."}'

curl "http://localhost:8000/search?q=vector%20dbs"
```

### 5️⃣ CLI Agent

```bash
python -m rag_memory_agent.agent
> what was that blog about HNSW indexing?
```

---

## 🧩 MCP Tools

| Tool                  | Description                                     |
| --------------------- | ----------------------------------------------- |
| **index_page**        | Ingests live web text (chunks → embed → FAISS). |
| **search_documents**  | Returns semantic matches with source metadata.  |
| **process_documents** | Batch-ingests `/documents` folder.              |

---

## 🏆 Unique Aspects

✅ **Unified Core Architecture**

All indexing, retrieval, and embedding logic consolidated in `core.py`, ensuring MCP, REST, and agent all share one codebase.

✅ **Temporal & Semantic Hybrid Ranking**

Combines cosine similarity with a lightweight temporal decay model — newer memories surface first.

```python
  score = sim * (1 + α * freshness(days))
  ```

  → newer pages rank higher.

✅ **Dual-Mode Memory**

Supports **short-term** (RAM) and **long-term** (FAISS) memory separation — enabling hybrid reasoning loops.

✅ **Dual Transport (MCP + REST)**

Works both as a traditional MCP stdio toolset *and* a REST API — bridging AI agent ecosystems and browser extensions.

✅ **Dynamic Embedding Backend**

Can seamlessly switch between local (`ollama nomic-embed-text`) and cloud (`text-embedding-004`) without touching code.

✅ **Agentic Reasoning with Gemini**

Perception and decision stages leverage Gemini 2.0 Flash for contextual tool planning, not static prompts.

✅ **Data Efficiency**

Uses deduplicated SHA1 chunk hashing and JSONL metadata for minimal storage overhead.

✅ **Practical RAG Evolution**

Instead of ephemeral chat memory, this agent builds a persistent semantic map of what the user reads online.

---

## 🌍 Vision

This project demonstrates how **RAG can evolve into long-term memory**:
an AI system that learns continuously, remembers semantically, and retrieves with context awareness — bridging *information retrieval*, *memory persistence*, and *agentic cognition*.

---

## 🪄 Summary

> **RAG with Memory** isn’t just another retrieval project —
> it’s a **cognitive infrastructure** for AI systems that think, remember, and act autonomously.
> Combining **Gemini reasoning**, **FAISS retrieval**, and **Chrome extension integration**,
> it sets the groundwork for *persistent, context-aware agents*.