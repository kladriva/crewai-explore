"""
Nodes API router
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field

from backend.database.connection import get_db
from backend.database.models import Node

router = APIRouter()


class NodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    ip_address: str = Field(..., min_length=3, max_length=45)
    node_type: str = Field(default="slave")  # master | slave
    is_active: bool = True
    os_type: Optional[str] = None
    os_version: Optional[str] = None


class NodeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    node_type: Optional[str] = None
    is_active: Optional[bool] = None
    agent_version: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None


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


@router.post("/nodes", status_code=status.HTTP_201_CREATED)
def create_node(payload: NodeCreate, db: Session = Depends(get_db)):
    # Check uniqueness of IP
    exists = db.query(Node).filter(Node.ip_address == payload.ip_address).first()
    if exists:
        raise HTTPException(status_code=400, detail="IP address already exists")
    node = Node(
        name=payload.name,
        ip_address=payload.ip_address,
        node_type=payload.node_type,
        is_active=payload.is_active,
        os_type=payload.os_type,
        os_version=payload.os_version,
    )
    try:
        db.add(node)
        db.commit()
        db.refresh(node)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create node (constraint error)")
    return node_to_dict(node)


@router.get("/nodes/{node_id}")
def get_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node_to_dict(node)


@router.put("/nodes/{node_id}")
@router.patch("/nodes/{node_id}")
def update_node(node_id: int, payload: NodeUpdate, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(node, field, value)
    try:
        db.commit()
        db.refresh(node)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to update node (constraint error)")
    return node_to_dict(node)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(node)
    db.commit()
    return None
