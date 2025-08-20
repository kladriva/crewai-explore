from fastapi import APIRouter, Query
from app.state.audit import recent_actions

router = APIRouter(prefix="/api", tags=["audit"])

@router.get("/auto-actions")
def get_auto_actions(limit: int = Query(10, ge=1, le=100)):
    """
    Renvoie les dernières actions automatiques.
    Format attendu par l'UI:
      [
        { "ts": 1734123456, "action": "restart_container", "target": "nginx",
          "outcome": "ok", "reason": "mem>90%", "severity": "crit" }
      ]
    """
    return {"items": recent_actions(limit)}
