from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core import clock
from app.database.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["Bitácora"], dependencies=[Depends(require_admin)])


@router.get("/")
def list_audit(
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = Query(300, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    """Bitácora de operaciones sensibles, de la más reciente a la más antigua."""
    query = db.query(AuditLog, User.full_name).outerjoin(User, User.id == AuditLog.user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    rows = query.order_by(AuditLog.id.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "created_at": clock.to_local(log.created_at).strftime("%d/%m/%Y %H:%M:%S") if log.created_at else None,
            "user_name": full_name or "—",
            "action": log.action,
            "entity": log.entity,
            "entity_id": log.entity_id,
            "detail": log.detail,
        }
        for log, full_name in rows
    ]
