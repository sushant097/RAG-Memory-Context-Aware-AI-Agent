
# 🧠 RAG with Memory — Agentic Web Memory Backend

A complete **agentic AI backend** built with `FastAPI`, `Gemini`, and `FAISS`, designed for the **RAG with Memory Assignment**.  
It powers a Chrome Extension that can **index every visited webpage**, **store its semantic meaning**, and **recall the exact snippet later** — effectively becoming a **personal web memory agent**.

---

## 📘 Overview

This backend is structured around the **Agentic AI architecture** taught in class:

> **Agent → Perception → Memory → Decision → Action**

Each module handles a distinct cognitive stage, and tools are implemented via a separate **MCP (Model Context Protocol)** server.

### 🎯 Goal

> Build an AI agent that continuously **learns from your browsing activity** and retrieves what it learned when you ask — connecting context, memory, and reasoning.

### 💡 Example Use Case

> You visit multiple web pages about *vector databases*.  
> Later, you search in the Chrome extension:  
> “What was that blog about IVF and HNSW indexing?”  
> → The backend retrieves and highlights the relevant snippet from the exact source page.

---

## 🧩 Architecture Overview

```

Chrome Extension → FastAPI HTTP Layer → MCP Tools → Agentic Pipeline (Gemini)
↓
FAISS Vector Store

````

### 🔹 Core Components

| File | Purpose |
|------|----------|
| **agent.py** | Main orchestrator — runs Perception → Decision → Action loop. |
| **perception.py** | Uses Gemini to clean and interpret user input, identify intent and tool hints. |
| **memory.py** | Manages short-term in-memory state for conversational context. |
| **decision.py** | Uses Gemini to plan — outputs `FUNCTION_CALL:` or `FINAL_ANSWER:`. |
| **action.py** | Executes tool calls (e.g., `search_documents`, `index_page`) and normalizes output. |
| **mcp_tools.py** | Implements actual tools: chunking, embedding (Google), FAISS search/indexing. |
| **http.py** | Exposes REST endpoints (`/index_page`, `/search`) for Chrome extension integration. |
| **models.py** | Configuration + Pydantic models (schema definitions, constants). |

---

## 🧠 Data Flow

### 🧩 Indexing Workflow

1. **Chrome Extension** captures current webpage (URL, title, full text).
2. Sends it to backend via:

```http
   POST /index_page
   {
     "url": "https://example.com",
     "title": "Vector Databases 101",
     "text": "IVF and HNSW improve FAISS performance..."
   }
```

3. Backend:

   * Chunks text into ~900-character blocks.
   * Creates **Google embeddings (`text-embedding-004`)** via `llama-index`.
   * Stores vectors in **FAISS index** + metadata JSON:

     ```json
     {
       "url": "...",
       "title": "...",
       "chunk_id": "abcd#c001",
       "timestamp": "2025-10-31T12:00:00Z",
       "snippet": "IVF and HNSW improve..."
     }
     ```

---

### 🔎 Search Workflow

1. **User types query** in Chrome extension or CLI.
2. **Perception**: Gemini classifies it as `semantic_search` and recommends tool `search_documents`.
3. **Decision**: Gemini emits plan:

   ```
   FUNCTION_CALL: search_documents|query="vector databases"|top_k=5
   ```
4. **Action**: Executes `mcp_tools.search_documents()`:

   * Embeds query.
   * Searches FAISS (cosine similarity + **temporal boost**).
   * Returns most relevant snippets.
5. **Chrome extension** receives result, opens page, and **highlights** the matched text.

---

## ⚙️ Tech Stack

| Layer           | Technology                                      | Purpose                                   |
| --------------- | ----------------------------------------------- | ----------------------------------------- |
| **LLM**         | Gemini 2.0 Flash                                | Reasoning, planning, perception, decision |
| **Embeddings**  | Google `text-embedding-004` (via `llama-index`) | High-quality semantic vectors             |
| **Vector DB**   | FAISS (CPU)                                     | Efficient nearest-neighbor retrieval      |
| **Parsing**     | MarkItDown                                      | Converts HTML, PDF, DOCX to markdown      |
| **API Layer**   | FastAPI                                         | Chrome extension integration              |
| **Protocol**    | MCP (Model Context Protocol)                    | Modular tool interface                    |
| **Persistence** | JSONL + FAISS                                   | Long-term memory store                    |

---

## 🚀 Running the Backend

### 1️⃣ Setup with **uv**

```bash
uv venv
uv sync
```

### 2️⃣ Set Environment Variables

```bash
echo "GOOGLE_API_KEY=your_gemini_api_key_here" > .env
```

### 3️⃣ (Optional) Batch Index Local Docs

Put `.pdf`, `.html`, or `.txt` files inside `/documents` folder and run:

```bash
python mcp_tools.py
```

### 4️⃣ Run the HTTP API

```bash
uvicorn http:app --reload --port 8000
```

### 5️⃣ Test API

#### ✅ Index a Page

```bash
curl -X POST http://localhost:8000/index_page \
  -H "content-type: application/json" \
  -d '{"url":"https://example.com","title":"Example","text":"Vector databases scale via IVF and HNSW..."}'
```

#### 🔍 Search

```bash
curl "http://localhost:8000/search?q=vector%20databases"
```

### 6️⃣ (Optional) Run CLI Agent

```bash
python agent.py
> what was that article about HNSW?
```

---

## 🧮 Memory & Retrieval Details

| Type                   | Description                                                                |
| ---------------------- | -------------------------------------------------------------------------- |
| **Short-term memory**  | Managed by `memory.py`, keeps latest queries and results in-session.       |
| **Long-term memory**   | Stored in FAISS index + JSON metadata, retrieved via embeddings.           |
| **Temporal weighting** | Recent pages get a slight score boost: `score = sim * (1 + α * freshness)` |
| **Deduplication**      | Based on SHA1 chunk hashes, avoids re-indexing same content.               |

---

## 🧠 Agentic Flow Diagram

```

User Query
   │
   ▼
[Perception]  → Gemini extracts intent & tool hint
   │
   ▼
[Decision]    → Gemini outputs FUNCTION_CALL
   │
   ▼
[Action]      → Executes tool (index/search)
   │
   ▼
[Memory]      → Stores results (short-term + FAISS)
   │
   ▼
Response / Highlight in Chrome

```

---

## 🧩 MCP Tools

| Tool                  | Description                                         |
| --------------------- | --------------------------------------------------- |
| **index_page**        | Indexes text + metadata from web pages.             |
| **search_documents**  | Semantic FAISS search (Google embeddings).          |
| **process_documents** | Batch-ingests `/documents` folder using MarkItDown. |

---

## 🧭 Project Tree

```
.
├── agent.py
├── action.py
├── decision.py
├── memory.py
├── perception.py
├── mcp_tools.py
├── http.py
├── models.py
├── documents/
├── faiss_index/
│   ├── index.bin
│   └── metadata.jsonl
└── pyproject.toml
```

---

## 🏆 Extra Work Beyond Assignment

✅ **1. Google Gemini Integration**

* Used **Gemini 2.0 Flash** for both perception and decision layers, replacing static rule-based parsing.
* Enables contextual tool planning and intelligent intent extraction.

✅ **2. Temporal-Aware Memory**

* Added **recency weighting** in FAISS search:

  ```python
  score = sim * (1 + α * freshness(days))
  ```

  → newer pages rank higher.

✅ **3. Structured Metadata**

* Every chunk has structured metadata (`url`, `title`, `timestamp`, `chunk_id`, `snippet`)
  → simplifies highlighting in Chrome extension.

✅ **4. Dual-Mode Memory**

* Supports **short-term** (RAM) and **long-term** (FAISS) memory separation — enabling hybrid reasoning loops.

✅ **5. Clean API for Chrome**

* Added **FastAPI shim** (`/index_page` and `/search`) to allow direct browser communication.

✅ **6. Full MCP Compatibility**

* Follows instructor’s **MCP architecture** for tool invocation, supporting future expansion.

✅ **7. Batch + Live Indexing**

* Two ingestion modes:

  * Batch (`process_documents`)
  * Live (Chrome → `/index_page`)

---

## 📦 Future Work

* 🪶 **Chrome Extension Integration**
  Next phase — capture DOM text and highlight retrieved snippets.

* 📚 **Hybrid RAG (Notes + Web)**
  Merge user’s personal notes (DynamoDB or Notion API) with FAISS search.

* 🧩 **Multi-Agent Coordination**
  Add “Summarizer” and “Planner” agents for richer recall and question answering.

---

<!-- ## 📽️ Demo Video -->

<!-- 🎥 [YouTube Demo — RAG with Memory Agent (Chrome + Gemini)](https://youtu.be/Gnc-11kfXFc) -->

---

## 🪄 Summary

> This project isn’t just a search index.
> It’s a **cognitive memory system** that perceives, plans, and remembers like an agent —
> powered by **Gemini**, **FAISS**, and **Google embeddings**, built to evolve into a **truly agentic RAG**.
