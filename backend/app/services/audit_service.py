"""Registro en la bitácora de auditoría (tabla audit_logs).

`record` solo agrega la fila a la sesión: se guarda con el mismo commit de la
operación que describe, así nunca queda una operación sin su registro ni un
registro de algo que al final no se guardó.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record(
    db: Session,
    user,
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    detail: Optional[str] = None,
) -> None:
    db.add(AuditLog(
        user_id=getattr(user, "id", user),
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=(detail or None) and detail[:500],
    ))
