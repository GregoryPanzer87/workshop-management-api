from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app.database import get_db
from app import RepairOrder, RepairOrderCreate, RepairOrderResponse, RepairOrderUpdate, crud_repair_order
from app.api.deps import require_roles
from app.core.security import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE, LEVEL_PROFESSIONAL

router = APIRouter(prefix="/repairs_orders", tags=["repairs_orders"])

@router.post("/", response_model=RepairOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_repiar_order(repair_order_in: RepairOrderCreate, db: Session = Depends(get_db)):
    """Create a new repair order in the database."""
    return crud_repair_order.create(db, obj_in=repair_order_in)

@router.get("/", response_model=List[RepairOrderResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_repairs_orders(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of repairs orders or performs a real-time search by sending 'q'."""
    if q and q.strip():
        search_result = crud_repair_order.search(
            db=db, 
            query=q, 
            search_fields=[cast(RepairOrder.id, String), cast(RepairOrder.entry_date, String), 
                           RepairOrder.status, cast(RepairOrder.exit_date, String)], 
            limit=limit
        )
        if not search_result:
            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND, 
                                detail={
                                "message": f"No se encontraron coincidencias para '{q}'",
                                "query": q,
                                "search_fields": ["ID", "Fecha de Entrada", "Estado", "Fecha de Salida"]
                                }
                            )
        return search_result

    return crud_repair_order.get_multi(db, skip=skip, limit=limit)

@router.get("/client/{client_id}", response_model=List[RepairOrderResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_repair_orders_by_client(
    client_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of repair orders for a specific client."""
    orders = crud_repair_order.get_other_id(db=db, id=client_id, field="client_id", skip=skip, limit=limit)
    return orders

@router.get("/device/{device_id}", response_model=List[RepairOrderResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_repair_orders_by_device(
    device_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of repair orders for a specific device."""
    orders = crud_repair_order.get_other_id(db=db, id=device_id, field="device_id", skip=skip, limit=limit)
    return orders

@router.patch("/{repair_order_id}", response_model=RepairOrderResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def update_repair_order(repair_order_id: int, repair_order_in: RepairOrderUpdate, db: Session = Depends(get_db)):
    """Update a repair order partially or completely."""
    db_repair_order = crud_repair_order.get(db, id=repair_order_id)
    if not db_repair_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Orden de reparacion no encontrada"
        )
    return crud_repair_order.update(db, db_obj=db_repair_order, obj_in=repair_order_in)

@router.delete("/{repair_order_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_repair_order(repair_order_id: int, db: Session = Depends(get_db)):
    try:
        deleted_repair_order = crud_repair_order.delete(db, repair_order_id=repair_order_id)
        if not deleted_repair_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Orden de reparacion no encontrada"
            )
        return {"message": f"Orden de reparacion '{repair_order_id}' eliminada correctamente"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )