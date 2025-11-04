"""
Actions API router
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.database.connection import get_db
from backend.database.models import Action, ActionStatus

router = APIRouter()


def action_to_dict(a: Action) -> dict:
    return {
        "id": a.id,
        "node_id": a.node_id,
        "container_id": a.container_id,
        "action_type": a.action_type,
        "status": a.status.value if a.status else None,
        "reason": a.reason,
        "agent_explanation": a.agent_explanation,
        "triggered_by": a.triggered_by,
        "execution_time": a.execution_time,
        "error_message": a.error_message,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "started_at": a.started_at.isoformat() if a.started_at else None,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
    }


@router.get("/actions")
def list_actions(
    db: Session = Depends(get_db),
    status: Optional[ActionStatus] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    q = db.query(Action)
    if status is not None:
        q = q.filter(Action.status == status)
    rows = q.order_by(Action.created_at.desc()).offset(offset).limit(limit).all()
    # Frontend expects an array of actions
    return [action_to_dict(a) for a in rows]
