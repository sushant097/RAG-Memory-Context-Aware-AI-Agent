from __future__ import annotations
from typing import List, Optional
from .models import MemoryItem

class ShortTermMemory:
    """Simple in-RAM short-term memory for the agent loop."""
    def __init__(self):
        self._items: List[MemoryItem] = []

    def add(self, item: MemoryItem) -> None:
        self._items.append(item)

    def recent(self, k: int=10, session_id: Optional[str]=None) -> List[MemoryItem]:
        items = self._items if session_id is None else [m for m in self._items if m.session_id == session_id]
        return items[-k:]
    
    def clear(self, session_id: Optional[str]= None)-> None:
        if session_id is None:
            self._items = []
        else:
            self._items = [m for m in self._items if m.session_id != session_id]


# One global short-term memory instance
STM = ShortTermMemory()