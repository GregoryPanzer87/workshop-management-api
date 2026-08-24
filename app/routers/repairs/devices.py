from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app import (
    DeviceType, DeviceBrand,
    Device, DeviceCreate, 
    DeviceResponse, DeviceUpdate, User,
    crud_device_type, crud_device_brand,
    crud_device, crud_client, get_db
)
from app.api.deps import get_current_user, require_roles
from app.utils import (
    generate_custom_serial, build_audit_change_details,
    validate_exists_by_create, validate_exists_by_update
)
from app.services import log_action
from app.core import LEVEL_BASIC, LEVEL_MEDIUM

DEVICE_LOAD_OPTIONS = [
    joinedload(Device.client),
    joinedload(Device.device_type),
    joinedload(Device.device_brand),
]

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_device(
    device_in: DeviceCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Creates a new device in the database and links it to a client."""
    create_data = device_in.model_dump()

    existence_checks = [
        (crud_client, "client_id", "El cliente especificado no existe"),
        (crud_device_type, "device_type_id", "El tipo de equipo especificado no existe"),
        (crud_device_brand, "device_brand_id", "La marca de equipo especificada no existe"),
    ]

    errors = validate_exists_by_create(db, create_data, existence_checks)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors
        )
    
    serial_in = create_data.get("serial_number")
    if serial_in and serial_in.strip():
        clean_serial = serial_in.strip()
        create_data["serial_number"] = clean_serial
        if crud_device.get_by_other(db, value=clean_serial, field="serial_number"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=["Ya existe un equipo registrado con este Serial"]
            )
    else:
        dev_type = crud_device_type.get_by_id(db, create_data["device_type_id"])
        prefix = dev_type.prefix if (dev_type and dev_type.prefix) else "INN"
        create_data["serial_number"] = generate_custom_serial(db=db, prefix=prefix)
    
    try:
        db_device = crud_device.create(db, obj_in=create_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el serial. Intente de nuevo."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        entity="devices",
        entity_id=db_device.id,
        details=f"Equipo registrado: (ID: {db_device.id})",
    )

    return crud_device.get_by_id(db, id=db_device.id, options=DEVICE_LOAD_OPTIONS)

@router.get("/", response_model=List[DeviceResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_devices(
    q: Optional[str] = None,
    client_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of devices or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_device.search_ilike(
            db=db, 
            query=q, 
            search_fields=[
                DeviceType.name, 
                DeviceBrand.name, 
                Device.model, 
                Device.serial_number
            ], 
            joins=[DeviceType, DeviceBrand],
            options=DEVICE_LOAD_OPTIONS,
            limit=limit
        )
    
    if client_id is not None:
        if not crud_client.get_by_id(db, client_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=["El cliente especificado no existe"]
            )
        return crud_device.get_other_id(db=db, id=client_id, field="client_id", options=DEVICE_LOAD_OPTIONS, skip=skip, limit=limit)

    return crud_device.get_multi(db, skip=skip, limit=limit, options=DEVICE_LOAD_OPTIONS)

@router.get("/random_serial/{device_type_id}", response_model=str, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def generate_random_serial(device_type_id: int, db: Session = Depends(get_db)):
    dev_type = crud_device_type.get_by_id(db, id=device_type_id)
    if not dev_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["El tipo de equipo especificado no existe"]
        )
    prefix = dev_type.prefix if dev_type.prefix else "INN"
    return generate_custom_serial(db, prefix=prefix)

@router.get("/{device_id}", response_model=DeviceResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_device_by_id(device_id: int, db: Session = Depends(get_db)):
    """Retrieves a single device by its ID"""
    db_device = crud_device.get_by_id(db, device_id, options=DEVICE_LOAD_OPTIONS)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Equipo no encontrado"]
        )
    return db_device

@router.patch("/{device_id}", response_model=DeviceResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_device(
    device_id: int, 
    device_in: DeviceUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Update a device partially or completely."""
    db_device = crud_device.get_by_id(db, device_id)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Equipo no encontrado"]
        )

    update_data = device_in.model_dump(exclude_unset=True)
    if not update_data:
        return crud_device.get_by_id(db, device_id, options=DEVICE_LOAD_OPTIONS)

    existence_checks = [
        (crud_device_type, "device_type_id", "El tipo de equipo especificado no existe"),
        (crud_device_brand, "device_brand_id", "La marca de equipo especificada no existe"),
    ]

    errors = validate_exists_by_update(db, update_data, existence_checks)
    if errors:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=errors)

    serial_in = update_data.get("serial_number")
    if serial_in:
        clean_serial = serial_in.strip()
        update_data["serial_number"] = clean_serial
        if clean_serial != db_device.serial_number:
            val_sn = crud_device.get_by_other(db, value=clean_serial, field="serial_number")
            if val_sn and val_sn.id != device_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=["El serial ya pertenece a otro equipo registrado"]
                )

    audit_details = build_audit_change_details(
        db_obj=db_device,
        update_data=update_data,
        entity_name="Equipo",
    )

    try:
        crud_device.update(db, db_obj=db_device, obj_in=update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el serial. Intente de nuevo."]
        )

    if audit_details:
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="devices",
            entity_id=device_id,
            details=audit_details
        )
        
    return crud_device.get_by_id(db, device_id, options=DEVICE_LOAD_OPTIONS)

@router.patch("/{device_id}/transfer/{new_client_id}", response_model=DeviceResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def change_owner(
    device_id: int, 
    new_client_id: int,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Transfers the ownership of a device to another client."""
    db_device = crud_device.get_by_id(db=db, id=device_id, options=[joinedload(Device.client)])
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Equipo no encontrado"]
        )

    if db_device.client_id == new_client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["El equipo ya pertenece al cliente seleccionado"]
        )

    new_client = crud_client.get_by_id(db, new_client_id)
    if not new_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["El nuevo cliente especificado no existe"]
        )

    old_client_str = f"{db_device.client.name} (ID: {db_device.client.id})" if db_device.client else "Desconocido"
    new_client_str = f"{new_client.name} (ID: {new_client.id})"

    db_device = crud_device.update_owner(db, device_id=device_id, client_id=new_client_id)

    log_action(
        db,
        user_id=current_user.id,
        action="UPDATE",
        entity="devices",
        entity_id=device_id,
        details=f"Transferencia de dueño del equipo #{device_id}: De {old_client_str} a {new_client_str}",
    )

    return crud_device.get_by_id(db, device_id, options=DEVICE_LOAD_OPTIONS)