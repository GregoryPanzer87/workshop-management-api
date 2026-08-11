from typing import List, Optional

from app import (
    ServiceType, ServiceTypeCreate,
    ServiceTypeResponse, ServiceTypeUpdate,
    crud_service_type, get_db,
)
from sqlalchemy import cast, String
from app.api.deps import require_roles
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/service_types", tags=["Service Types"])

@router.post(
    "/",
    response_model=ServiceTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_service_type(
    service_type_in: ServiceTypeCreate, db: Session = Depends(get_db)
):
    """Create a service type in the database."""
    validation = crud_service_type.get_by_other(
        db, value=service_type_in.name, field="name"
    )
    if validation:
        raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, 
                    detail="No puedes crear un servicio con un nombre ya existente"
                )
    return crud_service_type.create(db, obj_in=service_type_in)

@router.get(
    "/",
    response_model=List[ServiceTypeResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_service_types(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Retrieves a paginated list of service type or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_service_type.search_ilike(
            db=db,
            query=q,
            search_fields=[cast(ServiceType.id, String), ServiceType.name],
            limit=limit,
        )
    return crud_service_type.get_multi(db, skip=skip, limit=limit)


@router.patch("/{service_type_id}", response_model=ServiceTypeResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_service_type(service_type_id: int, service_type_in: ServiceTypeUpdate, db: Session = Depends(get_db)):
    """Update a service type partially or completely."""
    db_service_type = crud_service_type.get_by_id(db, id=service_type_id)
    if not db_service_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    if service_type_in.name is not None:
        validation = crud_service_type.get_by_other(
            db, value=service_type_in.name, field="name"
        )
        if validation and validation.id != service_type_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes cambiar el nombre de un servicio a uno ya existente",
            )
    return crud_service_type.update(db, db_obj=db_service_type, obj_in=service_type_in)