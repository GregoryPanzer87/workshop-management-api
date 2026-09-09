from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_current_user, require_roles
from app import (
    Storage, StorageCreate, StorageResponse, 
    StorageUpdate, Device, User, 
    crud_storage, crud_device,
    get_db
)
from app.utils import build_audit_change_details
from app.services import log_action
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/storage", tags=["Storage"])

STORAGE_LOAD_OPTIONS = [
    joinedload(Storage.device).joinedload(Device.customer),
    joinedload(Storage.device).joinedload(Device.device_type),
    joinedload(Storage.device).joinedload(Device.device_brand),
]


@router.post(
    "/", 
    response_model=StorageResponse, 
    status_code=status.HTTP_201_CREATED, 
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))]
)
def add_device_to_storage(
    storage_in: StorageCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Registers a new entry in storage (linked to a device)."""
    db_device = crud_device.get_by_id(db, id=storage_in.device_id)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Este equipo no existe."],
        )

    existing_device = crud_storage.get_by_other(
        db, value=storage_in.device_id, field="device_id"
    )
    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Este equipo ya está en el depósito."],
        )

    try:
        db_storage = crud_storage.create(db, obj_in=storage_in)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="storage",
            entity_id=db_storage.id,
            details=f"Equipo (ID: {db_storage.device_id}) ingresado al depósito",
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Este equipo ya está en el depósito."]
        )

    except Exception as e:
        db.rollback()
        raise e
        
    return crud_storage.get_by_id(db, db_storage.id, options=STORAGE_LOAD_OPTIONS)


@router.get("/", response_model=List[StorageResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_storage_entries(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of storage entries or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_storage.search_ilike(
            db=db, 
            query=q, 
            search_fields=[cast(Storage.entry_date, String), Device.serial_number, Storage.column],
            joins=[Device],
            options=STORAGE_LOAD_OPTIONS,
            limit=limit,
        )
    return crud_storage.get_multi(db, options=STORAGE_LOAD_OPTIONS, skip=skip, limit=limit)


@router.get("/device/{device_id}", response_model=StorageResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_storage_by_device_id(device_id: int, db: Session = Depends(get_db)):
    """Get storage record using the internal Device ID."""
    db_storage = crud_storage.get_by_other(
        db, value=device_id, field="device_id",
        options=STORAGE_LOAD_OPTIONS,
    )
    if not db_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["No existe un registro en depósito asociado a este ID de equipo."],
        )
    return db_storage


@router.get("/{storage_id}", response_model=StorageResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_storage_entry(storage_id: int, db: Session = Depends(get_db)):
    """Get a specific storage entry by its primary key (Storage ID)."""
    db_storage = crud_storage.get_by_id(db, id=storage_id, options=STORAGE_LOAD_OPTIONS)
    if not db_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Equipo en el depósito no encontrado."],
        )
    return db_storage


@router.patch("/{storage_id}", response_model=StorageResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_storage_entry(
    storage_id: int, 
    storage_in: StorageUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates a storage location details (such as column, row, or assigned device ID)."""
    db_storage = crud_storage.get_by_id(db, id=storage_id, options=STORAGE_LOAD_OPTIONS)
    if not db_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Equipo en el depósito no encontrado."]
        )

    update_data = storage_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_storage

    if (
        storage_in.device_id is not None
        and storage_in.device_id != db_storage.device_id 
    ):
        db_device = crud_device.get_by_id(db, id=storage_in.device_id)
        if not db_device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=["El equipo no existe."]
            )

        existing_device = crud_storage.get_by_other(db, value=storage_in.device_id, field="device_id")
        if existing_device and existing_device.id != storage_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=["Este equipo ya está en el depósito."]
            )

    audit_details = build_audit_change_details(
        db_obj=db_storage,
        update_data=update_data,
        entity_name="Depósito",
    )

    try: 
        crud_storage.update(db, db_obj=db_storage, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="storage",
                entity_id=storage_id,
                details=audit_details
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["El equipo ya está en el depósito."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return crud_storage.get_by_id(db, id=storage_id, options=STORAGE_LOAD_OPTIONS)


@router.delete("/{storage_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_storage_entry(
    storage_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a storage record and returns a descriptive message."""
    db_storage = crud_storage.get_by_id(db, id=storage_id, options=STORAGE_LOAD_OPTIONS)
    if not db_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Equipo en el depósito no encontrado."],
        )

    serial_number = db_storage.device.serial_number if db_storage.device else "N/A"
    client_name = db_storage.device.customer.name if (db_storage.device and db_storage.device.customer) else "N/A"
    detail_msg = f"Equipo de {client_name} (Serial: {serial_number})"

    try:
        crud_storage.delete(db, db_obj=db_storage)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="storage",
            entity_id=storage_id,
            details=f"Retirado del depósito: {detail_msg}",
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede retirar el registro del depósito debido a dependencias asociadas."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return {"message": f"{detail_msg} eliminado correctamente del depósito"}