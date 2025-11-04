"""
Nodes API router
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import Node

router = APIRouter()


def node_to_dict(n: Node) -> dict:
    return {
        "id": n.id,
        "name": n.name,
        "ip_address": n.ip_address,
        "node_type": n.node_type,
        "is_active": n.is_active,
        "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
        "agent_version": n.agent_version,
        "os_type": n.os_type,
        "os_version": n.os_version,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@router.get("/nodes")
def list_nodes(db: Session = Depends(get_db), active: Optional[bool] = Query(None)):
    q = db.query(Node)
    if active is not None:
        q = q.filter(Node.is_active == active)
    nodes = q.order_by(Node.id.desc()).all()
    # Frontend expects an array of nodes
    return [node_to_dict(n) for n in nodes]
