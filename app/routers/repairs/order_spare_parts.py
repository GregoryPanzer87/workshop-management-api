from typing import List, Optional

from app import (
    OrderSparePart, OrderSparePartCreate,
    OrderSparePartResponse, OrderSparePartUpdate,
    crud_order_spare_part, crud_spare_part, get_db,
)
from sqlalchemy import cast, String
from app.api.deps import require_roles
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/order_spare_parts", tags=["Order Spare Parts"])

@router.post(
    "/",
    response_model=OrderSparePartResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_order_spare_part(
    order_spare_part_in: OrderSparePartCreate, db: Session = Depends(get_db)
):
    """Create a order spare part in the database."""
    validation = crud_order_spare_part.search_where_by_IDs(
        db=db,
        id_1=order_spare_part_in.repair_order_id,
        id_2=order_spare_part_in.spare_part_id,
        field_1="repair_order_id",
        field_2="spare_part_id"
    )
    if validation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"No puedes añadir a la orden #{order_spare_part_in.repair_order_id} el mismo repuesto"
        )
    return crud_order_spare_part.create(db, obj_in=order_spare_part_in)

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
    if q and q.strip():
        return crud_order_spare_part.search_ilike(
            db=db,
            query=q,
            search_fields=[cast(OrderSparePart.id, String)],
            limit=limit,
        )
    return crud_order_spare_part.get_multi(db, skip=skip, limit=limit)


@router.patch(
    "/{order_spare_part_id}",
    response_model=OrderSparePartResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_order_spare_part(
    order_spare_part_id: int,
    order_spare_part_in: OrderSparePartUpdate,
    db: Session = Depends(get_db),
):
    """Update a order spare parts partially or completely."""
    db_order_spare_part = crud_order_spare_part.get_by_id(db, id=order_spare_part_id)
    if not db_order_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repuesto de orden no encontrado",
        )
    
    changing_spare = (
        order_spare_part_in.spare_part_id
        and order_spare_part_in.spare_part_id != db_order_spare_part.spare_part_id
    )

    if changing_spare:
        validation = crud_order_spare_part.search_where_by_IDs(
            db=db,
            id_1=db_order_spare_part.repair_order_id,
            id_2=order_spare_part_in.spare_part_id,
            field_1="repair_order_id",
            field_2="spare_part_id",
        )
        if validation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No puedes añadir a la orden #{db_order_spare_part.repair_order_id} el mismo repuesto",
            )
    
    return crud_order_spare_part.update(
        db, db_obj=db_order_spare_part, obj_in=order_spare_part_in
    )


@router.delete(
    "/{order_spare_part_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_order_spare_part(order_spare_part_id: int, db: Session = Depends(get_db)):
    try:
        deleted_order_spare_part = crud_order_spare_part.delete(
            db, id=order_spare_part_id
        )
        if not deleted_order_spare_part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repuesto de orden no encontrado",
            )
        db_spare_part = crud_spare_part.get_by_id(
                    db, deleted_order_spare_part.spare_part_id
                )
        spare_part_name = db_spare_part.name if db_spare_part else "Desconocido"
        return {
            "message": f"Repuesto '{spare_part_name}' de la orden #{deleted_order_spare_part.repair_order_id} eliminado correctamente"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )