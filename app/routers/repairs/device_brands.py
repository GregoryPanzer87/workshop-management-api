from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import (
    DeviceBrand, DeviceBrandCreate,
    DeviceBrandResponse, DeviceBrandUpdate, User,
    crud_device_brand, get_db,
)
from app.api.deps import get_current_user, require_roles
from app.utils import build_audit_change_details
from app.services import log_action
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/device_brands", tags=["Device brands"])


@router.post(
    "/",
    response_model=DeviceBrandResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_device_brand(
    device_brand_in: DeviceBrandCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a device brand in the database."""
    if crud_device_brand.get_by_other(db, value=device_brand_in.name, field="name"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["El nombre de la marca ya está en uso"],
        )

    try:
        db_device_brand = crud_device_brand.create(db, obj_in=device_brand_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar la marca. Verifique los datos ingresados."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        entity="device_brands",
        entity_id=db_device_brand.id,
        details=f"Marca registrada: {db_device_brand.name} (ID: {db_device_brand.id})",
    )

    return db_device_brand


@router.get(
    "/",
    response_model=List[DeviceBrandResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_devices_brands(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Retrieves a paginated list of device brands or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_device_brand.search_ilike(
            db=db,
            query=q,
            search_fields=[DeviceBrand.name],
            limit=limit,
        )
    return crud_device_brand.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/{device_brand_id}",
    response_model=DeviceBrandResponse,
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_device_brand_by_id(device_brand_id: int, db: Session = Depends(get_db)):
    """Retrieves a single device brand by ID."""
    db_device_brand = crud_device_brand.get_by_id(db, id=device_brand_id)
    if not db_device_brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Marca no encontrada"],
        )
    return db_device_brand


@router.patch(
    "/{device_brand_id}",
    response_model=DeviceBrandResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_device_brand(
    device_brand_id: int,
    device_brand_in: DeviceBrandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a device brand partially or completely."""
    db_device_brand = crud_device_brand.get_by_id(db, id=device_brand_id)
    if not db_device_brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Marca no encontrada"],
        )

    update_data = device_brand_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_device_brand

    new_name = update_data.get("name")
    if new_name != db_device_brand.name:
        val_name = crud_device_brand.get_by_other(db, value=new_name, field="name")
        if val_name and val_name.id != device_brand_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=["El nombre de la marca ya está en uso"],
            )

    audit_details = build_audit_change_details(
        db_obj=db_device_brand,
        update_data=update_data,
        entity_name="Marca de equipo",
    )

    try:
        db_device_brand = crud_device_brand.update(db, db_obj=db_device_brand, obj_in=update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar la marca. Verifique los datos ingresados."]
        )

    if audit_details:
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="device_brands",
            entity_id=device_brand_id,
            details=audit_details
        )

    return db_device_brand


@router.delete(
    "/{device_brand_id}", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_device_brand(
    device_brand_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Deletes a device brand by ID."""
    db_device_brand = crud_device_brand.get_by_id(db, device_brand_id)
    if not db_device_brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Marca no encontrada"],
        )
    try:
        crud_device_brand.delete(db, db_obj=db_device_brand)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar esta marca porque tiene equipos asociados."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        entity="device_brands",
        entity_id=device_brand_id,
        details=f"Marca eliminada: {db_device_brand.name} (ID: {db_device_brand.id})",
    )
    return {"message": f"Marca '{db_device_brand.name}' eliminada correctamente"}