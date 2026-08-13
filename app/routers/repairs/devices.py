from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app.database import get_db
from app.crud import crud_device
from app.models_repairs import Device
from app import Device, DeviceCreate, DeviceResponse, DeviceUpdate, crud_device_type, crud_device
from app.utils import generate_custom_serial
from app.api.deps import require_roles
from app.core import LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_device(device_in: DeviceCreate, db: Session = Depends(get_db)):
    """Creates a new device in the database and links it to a client."""
    if device_in.serial_number is None:
        db_device_type = crud_device_type.get_by_id(db, device_in.device_type_id)

        if not db_device_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El tipo de equipo especificado no existe",
            )

        while True:
            generated_serial = generate_custom_serial(db_device_type.prefix)
            if not crud_device.get_by_other(
                db, value=generated_serial, field="serial_number"
            ):
                device_in.serial_number = generated_serial
                break

    else:
        if crud_device.get_by_other(db, value=device_in.serial_number, field="serial_number"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un equipo registrado con este Serial"
            )
        
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
        return crud_device.search_ilike(
            db=db, 
            query=q, 
            search_fields=[cast(Device.client_id, String), Device.device_type, Device.brand, Device.model, Device.serial_number], 
            limit=limit
        )
    return crud_device.get_multi(db, skip=skip, limit=limit)

@router.get("/{device_id}", response_model=DeviceResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_device_by_id(device_id: int, db: Session = Depends(get_db)):
    """Retrieves a single repair order by its ID."""
    db_device = crud_device.get_by_id(db, id=device_id)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Orden de reparacion no encontrada"
        )
    return db_device

@router.get("/client/{client_id}", response_model=List[DeviceResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_devices_by_client(
    client_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of device for a specific client."""
    orders = crud_device.get_other_id(db=db, id=client_id, field="client_id", skip=skip, limit=limit)
    return orders

@router.patch("/{device_id}", response_model=DeviceResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_device(device_id: int, device_in: DeviceUpdate, db: Session = Depends(get_db)):
    """Update a device partially or completely."""
    db_device = crud_device.get_by_id(db, id=device_id)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Equipo no encontrado"
        )

    if device_in.serial_number:
        val_sn = crud_device.get_by_other(db, value=device_in.serial_number, field="serial_number")
        if val_sn and val_sn.id != device_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El número de serie ya pertenece a otro equipo registrado"
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