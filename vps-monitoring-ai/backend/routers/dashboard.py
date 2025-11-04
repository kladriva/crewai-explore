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
    one_hour_ago = now - timedelta(hours=1)

    total_nodes = db.query(func.count(Node.id)).scalar() or 0
    active_nodes = db.query(func.count(Node.id)).filter(Node.is_active == True).scalar() or 0

    total_containers = db.query(func.count()).select_from(Action.metadata.tables.get('containers') if False else None)
    # Fallback simple counts directly from Container model if available
    try:
        from backend.database.models import Container
        total_containers = db.query(func.count(Container.id)).scalar() or 0
        running_containers = db.query(func.count(Container.id)).filter(Container.status == 'running').scalar() or 0
    except Exception:
        total_containers = 0
        running_containers = 0

    active_alerts = db.query(func.count(Alert.id)).filter(Alert.is_resolved == False).scalar() or 0
    critical_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.is_resolved == False, Alert.severity == AlertSeverity.CRITICAL)
        .scalar()
        or 0
    )

    actions_last_hour = (
        db.query(func.count(Action.id))
        .filter(Action.created_at >= one_hour_ago)
        .scalar()
        or 0
    )

    return {
        "total_nodes": total_nodes,
        "active_nodes": active_nodes,
        "total_containers": total_containers,
        "running_containers": running_containers,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "actions_last_hour": actions_last_hour,
    }
