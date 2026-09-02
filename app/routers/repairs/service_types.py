from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import (
    ServiceType, ServiceTypeCreate,
    ServiceTypeResponse, ServiceTypeUpdate, User,
    crud_service_type, get_db,
)
from app.api.deps import get_current_user, require_roles
from app.utils import build_audit_change_details
from app.services import log_action
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/service_types", tags=["Service Types"])

NOT_FOUND_SERVICE_TYPE = ["Servicio no encontrado."]
CONFLICT_SERVICE_TYPE = ["El nombre del servicio ya está en uso."]
INTEGRITY_ERROR = ["Ocurrió un conflicto al registrar el servicio. Verifique los datos ingresados."]

@router.post(
    "/",
    response_model=ServiceTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_service_type(
    service_type_in: ServiceTypeCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a service type in the database."""
    if crud_service_type.get_by_other(db, value=service_type_in.name, field="name"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=CONFLICT_SERVICE_TYPE,
        )

    try:
        db_service_type = crud_service_type.create(db, obj_in=service_type_in)
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
        entity="service_types",
        entity_id=db_service_type.id,
        details=f"Tipo de servicio registrado: {db_service_type.name} (ID: {db_service_type.id})",
    )

    return db_service_type


@router.get(
    "/",
    response_model=List[ServiceTypeResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_service_type(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Retrieves a paginated list of service types or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_service_type.search_ilike(
            db=db,
            query=q,
            search_fields=[ServiceType.name],
            limit=limit,
        )
    return crud_service_type.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/{service_type_id}",
    response_model=ServiceTypeResponse,
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_service_type_by_id(service_type_id: int, db: Session = Depends(get_db)):
    """Retrieves a single service type by ID."""
    db_service_type = crud_service_type.get_by_id(db, id=service_type_id)
    if not db_service_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SERVICE_TYPE,
        )
    return db_service_type


@router.patch(
    "/{service_type_id}",
    response_model=ServiceTypeResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_service_type(
    service_type_id: int,
    service_type_in: ServiceTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a service type partially or completely."""
    db_service_type = crud_service_type.get_by_id(db, id=service_type_id)
    if not db_service_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SERVICE_TYPE,
        )

    update_data = service_type_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_service_type

    new_name = update_data.get("name")
    if new_name and new_name != db_service_type.name:
        val_name = crud_service_type.get_by_other(db, value=new_name, field="name")
        if val_name and val_name.id != service_type_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=CONFLICT_SERVICE_TYPE,
            )

    audit_details = build_audit_change_details(
        db_obj=db_service_type,
        update_data=update_data,
        entity_name="Tipo de servicio",
    )

    try:
        db_service_type = crud_service_type.update(db, db_obj=db_service_type, obj_in=update_data)
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
            entity="service_types",
            entity_id=service_type_id,
            details=audit_details
        )

    return db_service_type


@router.delete(
    "/{service_type_id}", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_service_type(
    service_type_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Deletes a service type by ID."""
    db_service_type = crud_service_type.get_by_id(db, service_type_id)
    if not db_service_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SERVICE_TYPE,
        )
    try:
        crud_service_type.delete(db, db_obj=db_service_type)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el servicio porque tiene órdenes de reparacion asociadas."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        entity="service_types",
        entity_id=service_type_id,
        details=f"Servicio eliminado: {db_service_type.name} (ID: {db_service_type.id})",
    )
    return {"message": f"Servicio '{db_service_type.name}' eliminado correctamente"}