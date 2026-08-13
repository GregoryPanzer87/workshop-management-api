from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app import Storage, StorageCreate, StorageResponse, StorageUpdate, crud_storage, crud_device, crud_client, get_db
from app.api.deps import require_roles
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/storage", tags=["Storage"])

@router.post("/", response_model=StorageResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def add_device_to_storage(storage_in: StorageCreate, db: Session = Depends(get_db)):
    """Registers a new entry in storage (optionally linked to a device)."""
    if storage_in.device_id is not None:
        db_device = crud_device.get_by_id(db, storage_in.device_id)

        if not db_device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El equipo no existe",
            )

        existing_device = crud_storage.get_other_id(
            db, id=storage_in.device_id, field="device_id"
        )
        if existing_device:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este equipo ya está en el depósito",
            )
        
    return crud_storage.create(db, obj_in=storage_in)

@router.get("/", response_model=List[StorageResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_storage_entries(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of storage entries or performs a real-time search by sending 'q'."""
    if q and q.strip():
        search_query = q.strip()
        device_serial = crud_storage.get_by_serial_number(db, serial_number=search_query)
        if device_serial:
            return [device_serial]

        return crud_storage.search_ilike(
            db=db, 
            query=search_query, 
            search_fields=[cast(Storage.id, String), cast(Storage.entry_date, String), Storage.column],
            limit=limit
        )
    return crud_storage.get_multi(db, skip=skip, limit=limit)

@router.get("/device/{device_id}", response_model=StorageResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_storage_by_device_id(device_id: int, db: Session = Depends(get_db)):
    """Get storage record using the internal Device ID."""
    db_storage = crud_storage.get_other_id(
        db, id=device_id, field="device_id"
    )
    if not db_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un registro en depósito asociado a este ID de equipo",
        )
    return db_storage

@router.get("/{storage_id}", response_model=StorageResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_storage_entry(storage_id: int, db: Session = Depends(get_db)):
    """Get a specific storage entry by its primary key (Storage ID)."""
    db_storage = crud_storage.get_by_id(db, id=storage_id)
    if not db_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de depósito no encontrado",
        )
    return db_storage

@router.patch("/{storage_id}", response_model=StorageResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_storage_entry(storage_id: int, storage_in: StorageUpdate, db: Session = Depends(get_db)):
    """Updates a storage location details (such as column, row, or assigned device ID)."""
    db_storage = crud_storage.get_by_id(db, id=storage_id)
    if not db_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Registro de depósito no encontrado"
        )

    if (storage_in.device_id is not None
        and storage_in.device_id != db_storage.device_id 
    ):
        db_device = crud_device.get_by_id(db, id=storage_in.device_id)
        if not db_device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El equipo no existe"
            )

        existing_device = crud_storage.get_other_id(db, id=storage_in.device_id, field="device_id")
        if existing_device and existing_device.id != storage_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este equipo ya está en el depósito"
            )
        
    return crud_storage.update(db, db_obj=db_storage, obj_in=storage_in)

@router.delete("/{storage_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_storage_entry(storage_id: int, db: Session = Depends(get_db)):
    """Deletes a storage record and returns a descriptive message."""
    db_storage = crud_storage.get_by_id(db, id=storage_id)
    if not db_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de depósito no encontrado",
        )

    detail_msg = f"Registro de depósito #{storage_id}"
    if db_storage.device_id:
        db_device = crud_device.get_by_id(db, id=db_storage.device_id)
        if db_device:
            db_client = crud_client.get_by_id(db, id=db_device.client_id)
            client_name = db_client.name if db_client else "Desconocido"
            detail_msg = f"Equipo de {client_name} (Serial: {db_device.serial_number})"

    crud_storage.delete(db, id=storage_id)
    return {"message": f"{detail_msg} eliminado correctamente del depósito"}