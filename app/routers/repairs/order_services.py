from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from app import (
    OrderService, OrderServiceCreate,
    OrderServiceResponse, OrderServiceUpdate,
    Service, User,
    crud_order_service, crud_services, crud_repair_order, get_db,
)
from app.utils import build_audit_change_details
from app.services import log_action
from app.api.deps import get_current_user, require_roles
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/order_services", tags=["Order Services"])

ORDER_SERVICES_LOAD_OPTIONS = [
    joinedload(OrderService.services)
]

NOT_FOUND_SERVICE = ["El servicio especificado no existe."]
NOT_FOUND_ORDER_SERVICE = ["Servicio hecho en la orden."]

@router.post(
    "/",
    response_model=OrderServiceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_order_service(
    order_service_in: OrderServiceCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Create an order service in the database."""
    if not crud_repair_order.get_by_id(db, id=order_service_in.repair_order_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[f"La orden de reparación #{order_service_in.repair_order_id} no existe"],
        )

    db_service = crud_services.get_by_id(db, id=order_service_in.service_id)
    if not db_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SERVICE,
        )

    validation = crud_order_service.search_where_by_fields(
        db=db,
        repair_order_id=order_service_in.repair_order_id,
        service_id=order_service_in.service_id,
    )
    if validation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=[f"El servicio '{db_service.name}' ya se encuentra registrado en la orden #{order_service_in.repair_order_id}"]
        )
    
    try:
        db_order_service = crud_order_service.create(db, obj_in=order_service_in)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="order_services",
            entity_id=db_order_service.id,
            details=f"Servicio '{db_service.name}' agregado a la orden #{db_order_service.repair_order_id}",
        )

        db.commit()
        db.refresh(db_order_service)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al asociar el servicio a la orden. Verifique los datos ingresados."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return crud_order_service.get_by_id(db, db_order_service.id, options=ORDER_SERVICES_LOAD_OPTIONS)


@router.get(
    "/",
    response_model=List[OrderServiceResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_order_services(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Retrieves a paginated list of order services or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_order_service.search_ilike(
            db=db,
            query=q,
            search_fields=[
                cast(OrderService.repair_order_id, String),
                Service.name
            ],
            joins=[Service],
            options=ORDER_SERVICES_LOAD_OPTIONS,
            limit=limit,
        )
    return crud_order_service.get_multi(db, options=ORDER_SERVICES_LOAD_OPTIONS, skip=skip, limit=limit)


@router.get(
    "/{order_service_id}", 
    response_model=OrderServiceResponse, 
    dependencies=[Depends(require_roles(LEVEL_BASIC))]
)
def read_order_service_by_id(order_service_id: int, db: Session = Depends(get_db)):
    """Retrieves a single order service by ID."""
    db_order_service = crud_order_service.get_by_id(db, id=order_service_id)
    if not db_order_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_ORDER_SERVICE
        )
    return crud_order_service.get_by_id(db, order_service_id, options=ORDER_SERVICES_LOAD_OPTIONS)


@router.patch(
    "/{order_service_id}",
    response_model=OrderServiceResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_order_service(
    order_service_id: int,
    order_service_in: OrderServiceUpdate,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Update an order service partially or completely."""
    db_order_service = crud_order_service.get_by_id(db, id=order_service_id, options=ORDER_SERVICES_LOAD_OPTIONS)
    if not db_order_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_ORDER_SERVICE,
        )

    update_data = order_service_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_order_service

    new_service_id = update_data.get("service_id")
    if new_service_id and new_service_id != db_order_service.service_id:
        db_service = crud_services.get_by_id(db, id=new_service_id)
        if not db_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=NOT_FOUND_SERVICE,
            )

        validation = crud_order_service.search_where_by_fields(
            db=db,
            repair_order_id=db_order_service.repair_order_id,
            service_id=new_service_id,
        )
        if validation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=[f"El servicio '{db_service.name}' ya se encuentra registrado en la orden #{db_order_service.repair_order_id}"],
            )

    audit_details = build_audit_change_details(
        db_obj=db_order_service,
        update_data=update_data,
        entity_name="Servicio de Orden",
    )

    try:
        crud_order_service.update(db, db_obj=db_order_service, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="order_services",
                entity_id=order_service_id,
                details=audit_details,
            )

        db.commit()
        db.refresh(db_order_service)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar el servicio de la orden. Verifique los datos ingresados."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return crud_order_service.get_by_id(db, order_service_id, options=ORDER_SERVICES_LOAD_OPTIONS)


@router.delete(
    "/{order_service_id}", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_order_service(
    order_service_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes an order service by ID."""
    db_order_service = crud_order_service.get_by_id(db, id=order_service_id, options=ORDER_SERVICES_LOAD_OPTIONS)
    if not db_order_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_ORDER_SERVICE,
        )
    
    service_name = db_order_service.services.name if db_order_service.services.name else f"ID {db_order_service.services_id}"
    repair_order_id = db_order_service.repair_order_id

    try:
        crud_order_service.delete(db, db_obj=db_order_service)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="order_services",
            entity_id=order_service_id,
            details=f"Servicio '{service_name}' eliminado de la orden #{repair_order_id}",
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el servicio de la orden debido a dependencias asociadas."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return {"message": f"Servicio '{service_name}' de la orden #{repair_order_id} eliminado correctamente"}