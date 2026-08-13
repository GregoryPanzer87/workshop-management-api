from typing import List, Optional

from app import (
    DeviceBrand, DeviceBrandCreate,
    DeviceBrandResponse, DeviceBrandUpdate,
    crud_device_brand, get_db,
)
from app.api.deps import require_roles
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/devices_brands", tags=["Devices brands"])


@router.post(
    "/",
    response_model=DeviceBrandResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_device_brand(
    device_brand_in: DeviceBrandCreate, db: Session = Depends(get_db)
):
    """Create a device brand in the database."""
    if device_brand_in.name:
        if crud_device_brand.get_by_other(
            db, value=device_brand_in.name, field="name"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nombre de la marca ya está en uso",
            )

    return crud_device_brand.create(db, obj_in=device_brand_in)


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
    """Retrieves a paginated list of devices brands or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_device_brand.search_ilike(
            db=db,
            query=q,
            search_fields=[DeviceBrand.name],
            limit=limit,
        )
    return crud_device_brand.get_multi(db, skip=skip, limit=limit)


@router.patch(
    "/{device_brand_id}",
    response_model=DeviceBrandResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_device_brand(
    device_brand_id: int,
    device_brand_in: DeviceBrandUpdate,
    db: Session = Depends(get_db),
):
    """Update a devices brands partially or completely."""
    db_device_brand = crud_device_brand.get_by_id(db, id=device_brand_id)
    if not db_device_brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marca no encontrada",
        )

    if device_brand_in.name:
        val_nat = crud_device_brand.get_by_other(
            db, value=device_brand_in.name, field="name"
        )
        if val_nat and val_nat.id != device_brand_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nombre de la marca ya está en uso",
            )

    return crud_device_brand.update(
        db, db_obj=db_device_brand, obj_in=device_brand_in
    )


@router.delete(
    "/{device_brand_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_device_brand(device_brand_id: int, db: Session = Depends(get_db)):
    db_devices_brands = crud_device_brand.get_by_id(db, device_brand_id)
    if not db_devices_brands:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marca no encontrada",
        )
    crud_device_brand.delete(db, db_devices_brands)
    return {"message": f"Marca de equipo '{db_devices_brands.name}' eliminada correctamente"}