from __future__ import annotations
from perception import perceive
from memory import STM, MemoryItem
from decision import decide
from action import execute

def run_once(user_text: str, session_id: str = "cli"):
    p = perceive(user_text)
    STM.add(MemoryItem(type="query", content=p.cleaned_query, session_id=session_id))
    plan = decide(p, STM.recent(6, session_id=session_id))
    res = execute(plan)

    if res["type"] == "tool_output":
        # summarize into STM
        preview = "; ".join((h["title"] or h["url"]) for h in res["data"][:3])
        STM.add(MemoryItem(type="tool_output", content=f"Top hits: {preview}", session_id=session_id))
        # render small view
        lines = []
        for h in res["data"]:
            lines.append(f"- {h['title'] or h['url']}  ({h['score']:.2f}) → {h['url']}")
        return "Top results:\n" + "\n".join(lines)

    STM.add(MemoryItem(type="fact", content=res["data"], session_id=session_id))
    return str(res["data"])

if __name__ == "__main__":
    print("Web Memory Agent — type a query. Ctrl+C to exit.")
    try:
        while True:
            q = input("> ").strip()
            if not q: 
                continue
            print(run_once(q))
    except (EOFError, KeyboardInterrupt):
        pass
