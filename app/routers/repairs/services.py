from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import (
    Service, ServiceCreate,
    ServiceResponse, ServiceUpdate, User,
    crud_services, get_db,
)
from app.api.deps import get_current_user, require_roles
from app.utils import build_audit_change_details
from app.services import log_action
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/services", tags=["Services"])

NOT_FOUND_SERVICE = ["Servicio no encontrado."]
CONFLICT_SERVICE = ["El nombre del servicio ya está en uso."]
INTEGRITY_ERROR = ["Ocurrió un conflicto al registrar el servicio. Verifique los datos ingresados."]


@router.post(
    "/",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_service(
    service_in: ServiceCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a service in the database."""
    if crud_services.get_by_other(db, value=service_in.name, field="name"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=CONFLICT_SERVICE,
        )

    try:
        db_service = crud_services.create(db, obj_in=service_in)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="services",
            entity_id=db_service.id,
            details=f"Servicio registrado: {db_service.name} (ID: {db_service.id})",
        )

        db.commit()
        db.refresh(db_service)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )
    except Exception as e:
        db.rollback()
        raise e

    return db_service


@router.get(
    "/",
    response_model=List[ServiceResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_services(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Retrieves a paginated list of services or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_services.search_ilike(
            db=db,
            query=q,
            search_fields=[Service.name],
            limit=limit,
        )
    return crud_services.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/{service_id}",
    response_model=ServiceResponse,
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_service_by_id(service_id: int, db: Session = Depends(get_db)):
    """Retrieves a single service by ID."""
    db_service = crud_services.get_by_id(db, id=service_id)
    if not db_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SERVICE,
        )
    return db_service


@router.patch(
    "/{service_id}",
    response_model=ServiceResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_service(
    service_id: int,
    service_in: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a service partially or completely."""
    db_service = crud_services.get_by_id(db, id=service_id)
    if not db_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SERVICE,
        )

    update_data = service_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_service

    new_name = update_data.get("name")
    if new_name and new_name != db_service.name:
        val_name = crud_services.get_by_other(db, value=new_name, field="name")
        if val_name and val_name.id != service_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=CONFLICT_SERVICE,
            )

    audit_details = build_audit_change_details(
        db_obj=db_service,
        update_data=update_data,
        entity_name="Servicio",
    )

    try:
        db_service = crud_services.update(db, db_obj=db_service, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="services",
                entity_id=service_id,
                details=audit_details
            )

        db.commit()
        db.refresh(db_service)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )
    except Exception as e:
        db.rollback()
        raise e

    return db_service


@router.delete(
    "/{service_id}", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_service(
    service_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Deletes a service by ID."""
    db_service = crud_services.get_by_id(db, service_id)
    if not db_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SERVICE,
        )
    try:
        crud_services.delete(db, db_obj=db_service)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="services",
            entity_id=service_id,
            details=f"Servicio eliminado: {db_service.name} (ID: {db_service.id})",
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el servicio porque tiene órdenes de reparación asociadas."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return {"message": f"Servicio '{db_service.name}' eliminado correctamente"}