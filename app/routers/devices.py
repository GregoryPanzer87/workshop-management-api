from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app.database import get_db
from app.crud import crud_device
from app.models import Device
from app.schemas import DeviceCreate, DeviceResponse, DeviceUpdate
from app.api.deps import require_roles
from app.core.security import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE, LEVEL_PROFESSIONAL

router = APIRouter(prefix="/devices", tags=["devices"])

@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_device(device_in: DeviceCreate, db: Session = Depends(get_db)):
    """Creates a new device in the database and links it to a client."""
    return crud_device.create(db, obj_in=device_in)

@router.get("/", response_model=List[DeviceResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_devices(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of customers or performs a real-time search by sending 'q'."""
    if q and q.strip():
        search_result = crud_device.search(
            db=db, 
            query=q, 
            search_fields=[cast(Device.client_id, String), Device.device_type, Device.brand, Device.model, Device.serial_number], 
            limit=limit
        )
        if not search_result:
            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND, 
                                detail={
                                "message": f"No se encontraron coincidencias para '{q}'",
                                "query": q,
                                "search_fields": ["Nombre", "Telefono", "Cedula/RIF", "Direccion"]
                                }
                            )
        return search_result

    return crud_device.get_multi(db, skip=skip, limit=limit)

@router.patch("/{device_id}", response_model=DeviceResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_device(device_id: int, device_in: DeviceUpdate, db: Session = Depends(get_db)):
    """Update a device partially or completely."""
    db_device = crud_device.get(db, id=device_id)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Equipo no encontrado"
        )
    return crud_device.update(db, db_obj=db_device, obj_in=device_in)

@router.patch("/{device_id}/transfer/{mew_client_id}", dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def change_owner(device_id: int, new_client_id: int, device_in: DeviceUpdate, db: Session = Depends(get_db)):
    """Change the owner of device by other"""
    db_device = crud_device.update_owner(db, device_id=device_id, client_id=new_client_id)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Equipo no encontrado"
        )
    return crud_device.update_owner(db, db_obj=db_device, obj_in=device_in)