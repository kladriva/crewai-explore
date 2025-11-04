"""
Dashboard stats API router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta

from backend.database.connection import get_db
from backend.database.models import Node, Alert, AlertSeverity, Action, ActionStatus

router = APIRouter()


@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    total_nodes = db.query(func.count(Node.id)).scalar() or 0
    active_nodes = db.query(func.count(Node.id)).filter(Node.is_active == True).scalar() or 0

    total_alerts = db.query(func.count(Alert.id)).scalar() or 0
    unresolved_alerts = db.query(func.count(Alert.id)).filter(Alert.is_resolved == False).scalar() or 0
    critical_unresolved = (
        db.query(func.count(Alert.id))
        .filter(Alert.is_resolved == False, Alert.severity == AlertSeverity.CRITICAL)
        .scalar()
        or 0
    )

    actions_today = (
        db.query(func.count(Action.id))
        .filter(Action.created_at >= today_start)
        .scalar()
        or 0
    )

    successful_actions_today = (
        db.query(func.count(Action.id))
        .filter(Action.created_at >= today_start, Action.status == ActionStatus.SUCCESS)
        .scalar()
        or 0
    )

    return {
        "nodes": {"total": total_nodes, "active": active_nodes},
        "alerts": {
            "total": total_alerts,
            "unresolved": unresolved_alerts,
            "critical_unresolved": critical_unresolved,
        },
        "actions": {
            "today": actions_today,
            "successful_today": successful_actions_today,
        },
        "timestamp": now.isoformat(),
    }
