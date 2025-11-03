from __future__ import annotations
from typing import Dict, Any
from .core import search_documents_core, index_page_core


def execute(plan: str) -> Dict[str, Any]:
    """
    Parse:
      FUNCTION_CALL: search_documents|query="..."|top_k=5
      FINAL_ANSWER: ...
    """
    plan = plan.strip()
    if plan.startswith("FINAL_ANSWER:"):
        return {"type":"final", "data": plan.split(":",1)[1].strip()}

    if not plan.startswith("FUNCTION_CALL:"):
        return {"type":"final", "data": "(no-op)"}

    _, rest = plan.split(":", 1)
    rest = rest.strip()
    fn, *argparts = rest.split("|")
    fn = fn.strip()

    args: Dict[str, Any] = {}
    for part in argparts:
        if "=" in part:
            k, v = part.split("=", 1)
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            args[k.strip()] = v

    if fn == "search_documents":
        q = args.get("query","")
        top_k = int(args.get("top_k","5"))
        return {"type": "tool_output", "data": search_documents_core(q, top_k)}
    elif fn == "index_page":
        return {"type":"tool_output", "data": index_page_core(
            args.get("url",""), args.get("title",""), args.get("text","")
        )}

    return {"type":"final", "data": "(unknown tool)"}