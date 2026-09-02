from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import (
    SparePart, SparePartCreate,
    SparePartResponse, SparePartUpdate, User,
    crud_spare_part, get_db,
)
from app.api.deps import get_current_user, require_roles
from app.utils import build_audit_change_details
from app.services import log_action
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/spare_parts", tags=["Spare Parts"])

NOT_FOUND_SPARE_PART = ["Repuesto no encontrado."]
CONFLICT_SPARE_PART = ["El nombre del repuesto ya existe."]
INTEGRITY_ERROR = ["Ocurrió un conflicto al registrar el repuesto. Verifique los datos ingresados."]

@router.post(
    "/",
    response_model=SparePartResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_spare_part(
    spare_part_in: SparePartCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a spare part in the database."""
    if crud_spare_part.get_by_other(db, value=spare_part_in.name, field="name"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=CONFLICT_SPARE_PART,
        )

    try:
        db_spare_part = crud_spare_part.create(db, obj_in=spare_part_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )

    log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        entity="spare_parts",
        entity_id=db_spare_part.id,
        details=f"Repuesto registrado: {db_spare_part.name} (ID: {db_spare_part.id})",
    )

    return db_spare_part


@router.get(
    "/",
    response_model=List[SparePartResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_spare_part(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Retrieves a paginated list of spare parts or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_spare_part.search_ilike(
            db=db,
            query=q,
            search_fields=[SparePart.name],
            limit=limit,
        )
    return crud_spare_part.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/{spare_part_id}",
    response_model=SparePartResponse,
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_spare_part_by_id(spare_part_id: int, db: Session = Depends(get_db)):
    """Retrieves a single spare part by ID."""
    db_spare_part = crud_spare_part.get_by_id(db, id=spare_part_id)
    if not db_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SPARE_PART,
        )
    return db_spare_part


@router.patch(
    "/{spare_part_id}",
    response_model=SparePartResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_spare_part(
    spare_part_id: int,
    spare_part_in: SparePartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a spare part partially or completely."""
    db_spare_part = crud_spare_part.get_by_id(db, id=spare_part_id)
    if not db_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SPARE_PART,
        )

    update_data = spare_part_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_spare_part

    new_name = update_data.get("name")
    if new_name and new_name != db_spare_part.name:
        val_name = crud_spare_part.get_by_other(db, value=new_name, field="name")
        if val_name and val_name.id != spare_part_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=CONFLICT_SPARE_PART,
            )

    audit_details = build_audit_change_details(
        db_obj=db_spare_part,
        update_data=update_data,
        entity_name="Repuesto",
    )

    try:
        db_spare_part = crud_spare_part.update(db, db_obj=db_spare_part, obj_in=update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )

    if audit_details:
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="spare_parts",
            entity_id=spare_part_id,
            details=audit_details
        )

    return db_spare_part


@router.delete(
    "/{spare_part_id}", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_spare_part(
    spare_part_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Deletes a spare part by ID."""
    db_spare_part = crud_spare_part.get_by_id(db, spare_part_id)
    if not db_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SPARE_PART,
        )
    try:
        crud_spare_part.delete(db, db_obj=db_spare_part)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el repuesto porque tiene órdenes de reparacion asociadas."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        entity="spare_parts",
        entity_id=spare_part_id,
        details=f"Repuesto eliminado: {db_spare_part.name} (ID: {db_spare_part.id})",
    )
    return {"message": f"Repuesto '{db_spare_part.name}' eliminado correctamente"}