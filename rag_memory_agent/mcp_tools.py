from mcp.server.fastmcp import FastMCP
from typing import List
from .core import index_page_core, search_documents_core

app = FastMCP("WebMemory")

@app.tool()
def index_page(url: str, title: str, text: str) -> dict:
    """Chunk→embed→append to FAISS (core)."""
    return index_page_core(url, title, text)

@app.tool()
def search_documents(query: str, k: int = 5) -> List[str]:
    """
    String results:
      "<snippet>\\n[Source: <url|title>, ID: <chunk_id>]"
    """
    records = search_documents_core(query, top_k=max(1, int(k)))
    if not records:
        return ["ERROR: No results"]
    out = []
    for r in records:
        src = r["url"] or r["title"]
        out.append(f"{r['snippet']}\n[Source: {src}, ID: {r['chunk_id']}]")
    return out

# Optional: allow running as an MCP stdio server
if __name__ == "__main__":
    app.run(transport="stdio")
