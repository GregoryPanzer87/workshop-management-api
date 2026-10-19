from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app import (
    DeviceModel, DeviceType, DeviceBrand,
    DeviceModelCreate, DeviceModelResponse, 
    DeviceModelUpdate, User,
    crud_device_model, crud_device_type, crud_device_brand, get_db
)
from app.api.deps import get_current_user, require_roles
from app.utils import (
    build_audit_change_details,
    validate_exists_by_create, validate_exists_by_update
)
from app.services import log_action
from app.core import LEVEL_BASIC, LEVEL_MEDIUM

# Nested relationship eager loading: Device -> DeviceModel -> DeviceType & DeviceBrand
DEVICE_MODEL_LOAD_OPTIONS = [
    joinedload(DeviceModel.device_type),
    joinedload(DeviceModel.device_brand)
]

router = APIRouter(prefix="/device_models", tags=["Device Models"])

NOT_FOUND_DEVICE_MODELS = ["Modelo de equipo no encontrado."]

@router.post("/", response_model=DeviceModelResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_device(
    device_in: DeviceModelCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Creates a new device entity and associates it with a specific customer and device model."""
    create_data = device_in.model_dump(exclude_unset=True)

    existence_checks = [
        (crud_device_type, "device_brand_id", "El tipo de equipo especificado no existe"),
        (crud_device_brand, "device_brand_id", "La marca de equipo especificado no existe"),
    ]

    errors_404 = validate_exists_by_create(db, create_data, existence_checks)
    if errors_404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors_404
        )

    try:
        db_device_model = crud_device_model.create(db, obj_in=create_data)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="devices",
            entity_id=db_device_model.id,
            details=f"Equipo registrado: (ID: {db_device_model.id})",
        )

        db.commit()
        db.refresh(db_device_model)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar. Intente de nuevo."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return crud_device_model.get_by_id(db, id=db_device_model.id, options=DEVICE_MODEL_LOAD_OPTIONS)


@router.get("/", response_model=List[DeviceModelResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_devices(
    q: Optional[str] = None,
    skip: int = 0, 
    limit: int = 20, 
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of devices, supporting full-text search via query string or filtering by customer ID."""
    q = q.strip() if q else None
    if q:
        return crud_device_model.search_ilike(
            db=db, 
            query=q, 
            search_fields=[
                DeviceModel.name,
                DeviceType.name, 
                DeviceBrand.name
            ], 
            joins=[DeviceType, DeviceBrand],
            options=DEVICE_MODEL_LOAD_OPTIONS,
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            sort_order=sort_order
        )

    return crud_device_model.get_multi(
        db, 
        skip=skip, 
        limit=limit, 
        options=DEVICE_MODEL_LOAD_OPTIONS,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/{device_model_id}", response_model=DeviceModelResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_device_by_id(device_model_id: int, db: Session = Depends(get_db)):
    """Retrieves detailed information for a single device by its primary key identifier."""
    db_device = crud_device_model.get_by_id(db, device_model_id, options=DEVICE_MODEL_LOAD_OPTIONS)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_DEVICE_MODELS
        )
    return db_device


@router.patch("/{device_model_id}", response_model=DeviceModelResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_device(
    device_model_id: int, 
    device_in: DeviceModelUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Partially updates an existing device instance with the provided request fields."""
    db_device = crud_device_model.get_by_id(db, device_model_id)
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_DEVICE_MODELS
        )

    update_data = device_in.model_dump(exclude_unset=True)
    if not update_data:
        return crud_device_model.get_by_id(db, device_model_id, options=DEVICE_MODEL_LOAD_OPTIONS)

    existence_checks = [
        (crud_device_type, "device_brand_id", "El tipo de equipo especificado no existe"),
        (crud_device_brand, "device_brand_id", "La marca de equipo especificado no existe"),
    ]

    errors = validate_exists_by_update(db, update_data, existence_checks)
    if errors:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=errors)

    audit_details = build_audit_change_details(
        db_obj=db_device,
        update_data=update_data,
        entity_name="Modelo de equipo",
    )

    try:
        crud_device_model.update(db, db_obj=db_device, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="device_models",
                entity_id=device_model_id,
                details=audit_details
            )

        db.commit()
        db.refresh(db_device)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar. Intente de nuevo."]
        )
    except Exception as e:
        db.rollback()
        raise str(e)
        
    return crud_device_model.get_by_id(db, device_model_id, options=DEVICE_MODEL_LOAD_OPTIONS)


@router.delete("/{device_model_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def delete_device(device_model_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Deletes a device record from the database by its primary key identifier."""
    db_device_models = crud_device_model.get_by_id(db, device_model_id, options=DEVICE_MODEL_LOAD_OPTIONS)
    if not db_device_models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_DEVICE_MODELS
        )

    device_model_name = db_device_models.name
        
    try:
        crud_device_model.delete(db, db_obj=db_device_models)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="device_models",
            entity_id=device_model_id,
            details=f"Equipo eliminado: (ID: {device_model_id})",
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el modelo de equipo porque tiene equipos asociadas."]
        )
    except Exception as e:
        db.rollback()
        raise str(e)
    
    return {"message": f"Modelo de equipo '{device_model_name}' eliminado correctamente"}