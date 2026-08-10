from typing import List, Optional

from app import (
    OrderService, OrderServiceCreate,
    OrderServiceResponse, OrderServiceUpdate,
    crud_order_service, crud_service_type, get_db,
)
from sqlalchemy import cast, String
from app.api.deps import require_roles
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/order_services", tags=["Order Services"])

@router.post(
    "/",
    response_model=OrderServiceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_order_service(
    order_service_in: OrderServiceCreate, db: Session = Depends(get_db)
):
    """Create a order service in the database."""
    validation = crud_order_service.search_where_by_IDs(
        db=db,
        id_1=order_service_in.repair_order_id,
        id_2=order_service_in.service_type_id,
        field_1="repair_order_id",
        field_2="service_type_id"
    )
    if validation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"No puedes añadir a la orden #{order_service_in.repair_order_id} el mismo servicio"
        )
    return crud_order_service.create(db, obj_in=order_service_in)

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
    if q and q.strip():
        return crud_order_service.search_ilike(
            db=db,
            query=q,
            search_fields=[cast(OrderService.id, String)],
            limit=limit,
        )
    return crud_order_service.get_multi(db, skip=skip, limit=limit)


@router.patch(
    "/{order_service_id}",
    response_model=OrderServiceResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_order_service(
    order_service_id: int,
    order_service_in: OrderServiceUpdate,
    db: Session = Depends(get_db),
):
    """Update a order services partially or completely."""
    db_order_service = crud_order_service.get_by_id(db, id=order_service_id)
    if not db_order_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio de orden no encontrado",
        )
    changing_service = (
        order_service_in.service_type_id
        and order_service_in.service_type_id != db_order_service.service_type_id
    )

    if changing_service:
        validation = crud_order_service.search_where_by_IDs(
            db=db,
            id_1=db_order_service.repair_order_id,
            id_2=order_service_in.service_type_id,
            field_1="repair_order_id",
            field_2="service_type_id",
        )
        if validation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No puedes añadir a la orden #{db_order_service.repair_order_id} el mismo servicio",
            )
    
    return crud_order_service.update(
        db, db_obj=db_order_service, obj_in=order_service_in
    )


@router.delete(
    "/{order_service_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_order_service(order_service_id: int, db: Session = Depends(get_db)):
    try:
        deleted_order_service = crud_order_service.delete(
            db, id=order_service_id
        )
        if not deleted_order_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servicio de orden no encontrado",
            )

        db_service_type = crud_service_type.get_by_id(
            db, deleted_order_service.service_type_id
        )
        service_name = db_service_type.name if db_service_type else "Desconocido"

        return {
            "message": f"Servicio '{service_name}' de la orden #{deleted_order_service.repair_order_id} eliminado correctamente"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )