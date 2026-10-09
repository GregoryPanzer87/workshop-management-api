from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app import AuditLog, AuditLogResponse, crud_audit, get_db
from app.api.deps import require_roles
from app.core import LEVEL_ADVANCE

router = APIRouter(prefix="/audit_log", tags=["Audit Log"])

@router.get("/", response_model=List[AuditLogResponse], dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def read_audit_log(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    sort_by: Optional[str] = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of log or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_audit.search_ilike(
            db=db, 
            query=q, 
            search_fields=[
                cast(AuditLog.user_id, String), 
                cast(AuditLog.created_at, String), 
                AuditLog.action, 
                AuditLog.entity, 
                AuditLog.details
            ], 
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            sort_order=sort_order
        )
    return crud_audit.get_multi(db, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order)

@router.get("/{log_id}", response_model=AuditLogResponse, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def read_audit_log_by_id(log_id: int, db: Session = Depends(get_db)):
    """Retrieves an audit log specific by its ID."""
    db_log = crud_audit.get_by_id(db, id=log_id)
    if not db_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de auditoría no encontrado"
        )
    return db_log