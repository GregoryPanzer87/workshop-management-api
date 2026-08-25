from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from app import (
    OrderSparePart, OrderSparePartCreate,
    OrderSparePartResponse, OrderSparePartUpdate,
    crud_order_spare_part, crud_spare_part, crud_repair_order, get_db,
    User
)
from app.utils import build_audit_change_details
from app.services import log_action
from app.api.deps import get_current_user, require_roles
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/order_spare_parts", tags=["Order Spare Parts"])


@router.post(
    "/",
    response_model=OrderSparePartResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_order_spare_part(
    order_spare_part_in: OrderSparePartCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Create an order spare part in the database."""
    # 1. Validar existencia de entidades referenciadas (FKs)
    if not crud_repair_order.get_by_id(db, id=order_spare_part_in.repair_order_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[f"La orden de reparación #{order_spare_part_in.repair_order_id} no existe"],
        )

    db_spare_part = crud_spare_part.get_by_id(db, id=order_spare_part_in.spare_part_id)
    if not db_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["El repuesto especificado no existe"],
        )

    # 2. Validar duplicados en la misma orden
    validation = crud_order_spare_part.search_where_by_fields(
        db=db,
        repair_order_id=order_spare_part_in.repair_order_id,
        spare_part_id=order_spare_part_in.spare_part_id,
    )
    if validation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=[f"El repuesto '{db_spare_part.name}' ya se encuentra registrado en la orden #{order_spare_part_in.repair_order_id}"]
        )
    
    try:
        db_order_spare_part = crud_order_spare_part.create(db, obj_in=order_spare_part_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al asociar el repuesto a la orden. Verifique los datos ingresados."]
        )
    
    log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        entity="order_spare_parts",
        entity_id=db_order_spare_part.id,
        details=f"Repuesto '{db_spare_part.name}' agregado a la orden #{db_order_spare_part.repair_order_id} (Cant: {db_order_spare_part.quantity})",
    )

    return db_order_spare_part


@router.get(
    "/",
    response_model=List[OrderSparePartResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))],
)
def read_order_spare_parts(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Retrieves a paginated list of order spare parts or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_order_spare_part.search_ilike(
            db=db,
            query=q,
            search_fields=[cast(OrderSparePart.repair_order_id, String)],
            limit=limit,
        )
    return crud_order_spare_part.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/{order_spare_part_id}", 
    response_model=OrderSparePartResponse, 
    dependencies=[Depends(require_roles(LEVEL_BASIC))]
)
def read_order_spare_part_by_id(order_spare_part_id: int, db: Session = Depends(get_db)):
    """Retrieves a single order spare part by ID."""
    db_order_spare_part = crud_order_spare_part.get_by_id(db, id=order_spare_part_id)
    if not db_order_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Repuesto no usado en la orden"]
        )
    return db_order_spare_part


@router.patch(
    "/{order_spare_part_id}",
    response_model=OrderSparePartResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_order_spare_part(
    order_spare_part_id: int,
    order_spare_part_in: OrderSparePartUpdate,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Update an order spare part partially or completely."""
    db_order_spare_part = crud_order_spare_part.get_by_id(db, id=order_spare_part_id)
    if not db_order_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Repuesto no usado en la orden"],
        )

    update_data = order_spare_part_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_order_spare_part

    new_spare_part_id = update_data.get("spare_part_id")
    if new_spare_part_id and new_spare_part_id != db_order_spare_part.spare_part_id:
        db_spare_part = crud_spare_part.get_by_id(db, id=new_spare_part_id)
        if not db_spare_part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=["El repuesto especificado no existe"],
            )

        validation = crud_order_spare_part.search_where_by_fields(
            db=db,
            repair_order_id=db_order_spare_part.repair_order_id,
            spare_part_id=new_spare_part_id,
        )
        if validation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=[f"El repuesto '{db_spare_part.name}' ya se encuentra registrado en la orden #{db_order_spare_part.repair_order_id}"],
            )

    audit_details = build_audit_change_details(
        db_obj=db_order_spare_part,
        update_data=update_data,
        entity_name="Repuesto de Orden",
    )

    try:
        crud_order_spare_part.update(db, db_obj=db_order_spare_part, obj_in=update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar el repuesto de la orden. Verifique los datos ingresados."]
        )

    if audit_details:
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="order_spare_parts",
            entity_id=order_spare_part_id,
            details=audit_details,
        )

    return db_order_spare_part


@router.delete(
    "/{order_spare_part_id}", 
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_order_spare_part(
    order_spare_part_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes an order spare part by ID."""
    db_order_spare_part = crud_order_spare_part.get_by_id(db, id=order_spare_part_id)
    if not db_order_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Repuesto no usado en la orden"],
        )
    
    db_spare_part = crud_spare_part.get_by_id(db, id=db_order_spare_part.spare_part_id)
    spare_part_name = db_spare_part.name if db_spare_part else f"ID {db_order_spare_part.spare_part_id}"

    try:
        crud_order_spare_part.delete(db, db_obj=db_order_spare_part)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el repuesto de la orden debido a dependencias asociadas."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        entity="order_spare_parts",
        entity_id=order_spare_part_id,
        details=f"Repuesto '{spare_part_name}' eliminado de la orden #{db_order_spare_part.repair_order_id}",
    )

    return {"message": f"Repuesto '{spare_part_name}' de la orden #{db_order_spare_part.repair_order_id} eliminado correctamente"}