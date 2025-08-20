
from collections import deque
from threading import Lock
from datetime import datetime, timezone
from typing import Any, Dict, List

_LOCK = Lock()
_EVENTS: deque = deque(maxlen=200)

def log_action(kind: str, target: str, result: str, meta: Dict[str, Any] | None = None) -> None:
    """Ajoute une action automatique (ex: redémarrage conteneur) au journal."""
    with _LOCK:
        _EVENTS.appendleft({
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,          
            "target": target,      
            "result": result,      
            "meta": meta or {},    
        })

def recent(limit: int = 50) -> List[dict]:
    with _LOCK:
        return list(list(_EVENTS)[:limit])
