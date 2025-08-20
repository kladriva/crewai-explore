
from fastapi import APIRouter, Query
from app.state import audit

router = APIRouter(prefix="/api/actions", tags=["actions"])

@router.get("/auto")
def list_auto_actions(limit: int = Query(10, ge=1, le=200)):
    """Retourne les dernières actions automatiques."""
    return {"items": audit.recent(limit)}
