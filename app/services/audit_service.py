from typing import Optional
from sqlalchemy.orm import Session
from app import AuditLog, AuditLogCreate, crud_audit

def log_action(
    db: Session,
    user_id: int,
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    details: Optional[str] = None,
    db_obj: Optional[AuditLogCreate] = None
) -> AuditLog:
    "Register a new entry by table audilog in the database"
    if db_obj is None:
        db_obj = AuditLogCreate(
            user_id=user_id,
            action=action.upper(),
            entity=entity.lower(),
            entity_id=entity_id,
            details=details
        )
    db_audit = crud_audit.create(db, obj_in=db_obj)
    return db_audit