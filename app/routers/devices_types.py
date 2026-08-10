from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import DeviceType, DeviceTypeCreate, DeviceTypeResponse, DeviceTypeUpdate, crud_device_type, get_db
from app.utils import generate_device_type_prefix
from app.api.deps import require_roles
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/devices_types", tags=["Devices Types"])

@router.post("/", response_model=DeviceTypeResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_device_type(device_type_in: DeviceTypeCreate, db: Session = Depends(get_db)):
    """Create a device type in the database."""
    errors = []
    if device_type_in.name:
        if crud_device_type.get_by_other(db, value=device_type_in.name, field="name"):
            errors.append("El tipo de equipo ya esta en uso")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors
        )

    device_type_in.prefix = generate_device_type_prefix(device_type_in.name, db)
        
    return crud_device_type.create(db, obj_in=device_type_in)

@router.get("/", response_model=List[DeviceTypeResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_devices_types(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of devices types or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_device_type.search_ilike(
            db=db, 
            query=q, 
            search_fields=[DeviceType.name, DeviceType.prefix], 
            limit=limit
        )
    return crud_device_type.get_multi(db, skip=skip, limit=limit)

@router.patch("/{device_type_id}", response_model=DeviceTypeResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_device_type(device_type_id: int, device_type_in: DeviceTypeUpdate, db: Session = Depends(get_db)):
    """Update a devices types partially or completely."""
    db_device_type = crud_device_type.get_by_id(db, id=device_type_id)
    if not db_device_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Tipo de equipo no encontrado"
        )

    errors = []
    
    if device_type_in.name:
        val_nat = crud_device_type.get_by_other(db, value=device_type_in.name, field="name")
        if val_nat and val_nat.id != device_type_id:
            errors.append("El tipo de equipo ya esta en uso")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors
        )
        
    return crud_device_type.update(db, db_obj=db_device_type, obj_in=device_type_in)

@router.delete("/{device_type_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_device_type(device_type_id: int, db: Session = Depends(get_db)):
    try:
        deleted_devices_types = crud_device_type.delete(db, device_type_id=device_type_id)
        if not deleted_devices_types:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tipo de equipo no encontrado"
            )
        return {"message": f"Tipo de equipo '{deleted_devices_types.name}' eliminado correctamente"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )