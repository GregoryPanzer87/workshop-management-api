from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import (
    DeviceType, DeviceTypeCreate,
    DeviceTypeResponse, DeviceTypeUpdate, User,
    crud_device_type, get_db,
)
from app.api.deps import get_current_user, require_roles
from app.utils import (
    validate_unique_fields_by_create,
    validate_unique_fields_by_update, 
    build_audit_change_details,
    generate_device_type_prefix
)
from app.services import log_action
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/device_types", tags=["Device Types"])

NOT_FOUND_DEVICE_TYPES = ["Tipo de equipo no encontrado."]

@router.post(
    "/",
    response_model=DeviceTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_device_type(
    device_type_in: DeviceTypeCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a device type in the database."""
    create_data = device_type_in.model_dump(exclude_unset=True)

    unique_fields = [
        ("name", "El nombre del tipo de equipo ya esta en uso"),
        ("prefix", "El prefijo ya esta en uso"),
    ]

    errors_409 = validate_unique_fields_by_create(
        db, 
        crud_repo=crud_device_type, 
        create_data=create_data, 
        unique_fields=unique_fields
    )

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    prefix = generate_device_type_prefix(type_name=create_data.get("name"), db=db)
    create_data["prefix"] = prefix

    try:
        db_device_type = crud_device_type.create(db, obj_in=create_data)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="device_types",
            entity_id=db_device_type.id,
            details=f"Tipo de equipo registrado: {db_device_type.name} (ID: {db_device_type.id})",
        )

        db.commit()
        db.refresh(db_device_type)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el Tipo de equipo. Verifique los datos ingresados."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return db_device_type


@router.get(
    "/",
    response_model=List[DeviceTypeResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_devices_types(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Retrieves a paginated list of device types or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_device_type.search_ilike(
            db=db,
            query=q,
            search_fields=[DeviceType.name, DeviceType.prefix],
            limit=limit,
        )
    return crud_device_type.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/{device_type_id}",
    response_model=DeviceTypeResponse,
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_device_type_by_id(device_type_id: int, db: Session = Depends(get_db)):
    """Retrieves a single device type by ID."""
    db_device_type = crud_device_type.get_by_id(db, id=device_type_id)
    if not db_device_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_DEVICE_TYPES,
        )
    return db_device_type


@router.patch(
    "/{device_type_id}",
    response_model=DeviceTypeResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_device_type(
    device_type_id: int,
    device_type_in: DeviceTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a device type partially or completely."""
    db_device_type = crud_device_type.get_by_id(db, id=device_type_id)
    if not db_device_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_DEVICE_TYPES,
        )

    update_data = device_type_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_device_type

    unique_fields = [
        ("name", "El nombre del tipo de equipo ya esta en uso."),
        ("prefix", "El prefijo ya esta en uso."),
    ]

    errors_409 = validate_unique_fields_by_update(
        db, 
        crud_repo=crud_device_type, 
        db_obj=db_device_type,
        update_data=update_data, 
        unique_fields=unique_fields
    )

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    audit_details = build_audit_change_details(
        db_obj=db_device_type,
        update_data=update_data,
        entity_name="Tipo de Equipo",
    )

    try:
        db_device_type = crud_device_type.update(db, db_obj=db_device_type, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="device_types",
                entity_id=device_type_id,
                details=audit_details
            )

        db.commit()
        db.refresh(db_device_type)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar el tipo de equipo. Verifique los datos ingresados."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return db_device_type


@router.delete(
    "/{device_type_id}", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_device_type(
    device_type_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Deletes a device type by ID."""
    db_device_type = crud_device_type.get_by_id(db, device_type_id)
    if not db_device_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_DEVICE_TYPES,
        )
    try:
        crud_device_type.delete(db, db_obj=db_device_type)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="device_types",
            entity_id=device_type_id,
            details=f"Tipo de equipo eliminado: {db_device_type.name} (ID: {db_device_type.id})",
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar este tipo de equipo porque tiene equipos asociados."]
        )
    except Exception as e:
            db.rollback()
            raise e
    
    return {"message": f"Tipo de equipo '{db_device_type.name}' eliminado correctamente"}