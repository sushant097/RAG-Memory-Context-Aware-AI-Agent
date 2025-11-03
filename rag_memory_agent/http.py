# rag_memory_agent/http.py
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from .core import index_page_core, search_documents_core
from .models import IndexPageIn

app = FastAPI(title="Web Memory HTTP API")

@app.post("/index_page")
def http_index_page(payload: IndexPageIn):
    return JSONResponse(index_page_core(payload.url, payload.title, payload.text))

@app.get("/search")
def http_search(q: str = Query(...), top_k: int = 5):
    return JSONResponse(search_documents_core(q, top_k=top_k))
