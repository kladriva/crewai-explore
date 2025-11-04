"""
Alerts API router
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.connection import get_db
from backend.database.models import Alert, AlertSeverity

router = APIRouter()


def alert_to_dict(a: Alert) -> dict:
    return {
        "id": a.id,
        "node_id": a.node_id,
        "severity": a.severity.value if a.severity else None,
        "title": a.title,
        "message": a.message,
        "metric_type": a.metric_type,
        "metric_value": a.metric_value,
        "threshold_value": a.threshold_value,
        "is_resolved": a.is_resolved,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "notified_email": a.notified_email,
        "notified_telegram": a.notified_telegram,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/alerts")
def list_alerts(
    db: Session = Depends(get_db),
    is_resolved: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    q = db.query(Alert)
    if is_resolved is not None:
        q = q.filter(Alert.is_resolved == is_resolved)
    total = q.count()
    rows = q.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return {"items": [alert_to_dict(a) for a in rows], "total": total}
