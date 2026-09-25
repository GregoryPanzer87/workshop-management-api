from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app import (
    OrderSparePart, OrderSparePartCreate,
    OrderSparePartBatchCreate,
    OrderSparePartResponse, OrderSparePartUpdate,
    SparePart, User,RepairOrder,
    crud_order_spare_part, crud_spare_part, crud_repair_order, get_db,
)
from app.utils import build_audit_change_details
from app.services import log_action
from app.services.inventory_service import update_inventory_spare_part
from app.api.deps import get_current_user, require_roles
from app.core import LEVEL_ADVANCE, LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/order_spare_parts", tags=["Order Spare Parts"])

ORDER_SPARE_PARTS_LOAD_OPTIONS = [
    joinedload(OrderSparePart.spare_part),
    joinedload(OrderSparePart.repair_order)
]

NOT_FOUND_SPARE_PART = ["El repuesto especificado no existe."]
NOT_FOUND_ORDER_SPARE_PARTS = ["Repuesto no utilizado en la orden."]


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
    """Create an order spare part in the database and updates inventory if tracked."""
    if not crud_repair_order.get_by_id(db, id=order_spare_part_in.repair_order_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[f"La orden de reparación #{order_spare_part_in.repair_order_id} no existe"],
        )

    db_spare_part = crud_spare_part.get_by_id(db, id=order_spare_part_in.spare_part_id)
    if not db_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_SPARE_PART,
        )

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
    
    quantity = order_spare_part_in.quantity

    try:
        update_inventory_spare_part(
            db=db,
            delta=-quantity,
            user_id=current_user.id,
            db_obj=db_spare_part
        )

        db_order_spare_part = crud_order_spare_part.create(db, obj_in=order_spare_part_in)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="order_spare_parts",
            entity_id=db_order_spare_part.id,
            details=f"Repuesto '{db_spare_part.name}' agregado a la orden #{db_order_spare_part.repair_order_id} (Cant: {db_order_spare_part.quantity})",
        )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al asociar el repuesto a la orden. Verifique los datos ingresados."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return crud_order_spare_part.get_by_id(db, db_order_spare_part.id, options=ORDER_SPARE_PARTS_LOAD_OPTIONS)


@router.post(
    "/batch",
    response_model=List[OrderSparePartResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def create_order_spare_parts_batch(
    batch_in: OrderSparePartBatchCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Add multiple spare parts to repair orders in a single atomic transaction."""
    if not batch_in.order_spare_parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["La lista de repuestos no puede estar vacía."]
        )

    seen_pairs = set()
    for index, item in enumerate(batch_in.order_spare_parts):
        pair = (item.repair_order_id, item.spare_part_id)
        if pair in seen_pairs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=[f"El elemento {index + 1} contiene un repuesto duplicado dentro de la misma petición."]
            )
        seen_pairs.add(pair)

    order_ids = list({item.repair_order_id for item in batch_in.order_spare_parts})
    spare_part_ids = list({item.spare_part_id for item in batch_in.order_spare_parts})

    existing_orders = crud_repair_order.get_multi(db, identities=order_ids, limit=len(order_ids))
    existing_order_ids = {order.id for order in existing_orders}
    
    missing_orders = set(order_ids) - existing_order_ids
    if missing_orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[f"La(s) orden(es) de reparación con ID {list(missing_orders)} no existe(n)."]
        )

    existing_spare_part = crud_spare_part.get_multi(db, identities=spare_part_ids, limit=len(spare_part_ids))
    spare_part_cache = {srv.id: srv.name for srv in existing_spare_part}

    missing_spare_parts = set(spare_part_ids) - set(spare_part_cache.keys())
    if missing_spare_parts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[f"El/Los repuesto(s) con ID {list(missing_spare_parts)} no existe(n)."]
        )

    existing_pairs = crud_order_spare_part.existing_batch(db=db, order_ids=order_ids)

    for item in batch_in.order_spare_parts:
        if (item.repair_order_id, item.spare_part_id) in existing_pairs:
            sp_name = spare_part_cache.get(item.spare_part_id, "Desconocido")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=[f"El repuesto '{sp_name}' ya se encuentra registrado previamente en la orden (ID:{item.repair_order_id})."]
            )

    created_ids = []
    try:
        for item in batch_in.order_spare_parts:
            db_order_spare_part = crud_order_spare_part.create(db, obj_in=item)
            created_ids.append(db_order_spare_part.id)

            spare_part_name = spare_part_cache.get(item.spare_part_id, "Desconocido")

            log_action(
                db,
                user_id=current_user.id,
                action="CREATE",
                entity="order_spare_parts",
                entity_id=db_order_spare_part.id,
                details=f"Repuesto '{spare_part_name}' agregado en lote a la orden (ID:{item.repair_order_id}).",
            )
            
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto de integridad al asociar los repuestos a las órdenes."]
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=[str(e)]
        )

    return crud_order_spare_part.get_multi(
        db=db, 
        identities=created_ids, 
        limit=len(created_ids), 
        options=ORDER_SPARE_PARTS_LOAD_OPTIONS
    )

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
            search_fields=[
                RepairOrder.order_number,
                RepairOrder.legacy_order_number,
                SparePart.name
            ],
            joins=[RepairOrder, SparePart],
            options=ORDER_SPARE_PARTS_LOAD_OPTIONS,
            limit=limit,
        )
    return crud_order_spare_part.get_multi(db, options=ORDER_SPARE_PARTS_LOAD_OPTIONS, skip=skip, limit=limit)


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
            detail=NOT_FOUND_ORDER_SPARE_PARTS
        )
    return crud_order_spare_part.get_by_id(db, order_spare_part_id, options=ORDER_SPARE_PARTS_LOAD_OPTIONS)

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
    """Update an order spare part partially or completely and adjusts inventory."""
    db_order_spare_part = crud_order_spare_part.get_by_id(db, id=order_spare_part_id, options=ORDER_SPARE_PARTS_LOAD_OPTIONS)
    if not db_order_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_ORDER_SPARE_PARTS,
        )

    update_data = order_spare_part_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_order_spare_part

    old_quantity = db_order_spare_part.quantity
    old_spare_part_id = db_order_spare_part.spare_part_id

    new_quantity = update_data.get("quantity")
    new_spare_part_id = update_data.get("spare_part_id")

    target_quantity = new_quantity if new_quantity is not None else old_quantity
    is_new_spare_part = new_spare_part_id is not None and new_spare_part_id != old_spare_part_id

    if is_new_spare_part:
        target_spare_part = crud_spare_part.get_by_id(db, id=new_spare_part_id)
        if not target_spare_part:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=NOT_FOUND_SPARE_PART,
            )

        validation = crud_order_spare_part.search_where_by_fields(
            db=db,
            repair_order_id=db_order_spare_part.repair_order_id,
            spare_part_id=new_spare_part_id,
        )
        if validation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=[f"El repuesto '{target_spare_part.name}' ya se encuentra registrado en la orden #{db_order_spare_part.repair_order_id}"],
            )
    else:
        target_spare_part = db_order_spare_part.spare_part

    audit_details = build_audit_change_details(
        db_obj=db_order_spare_part,
        update_data=update_data,
        entity_name="Repuesto de Orden",
    )

    try:
        if is_new_spare_part:
            # Old Data
            update_inventory_spare_part(
                db=db, delta=old_quantity, user_id=current_user.id, spare_part_id=old_spare_part_id
            )
            # New Data
            update_inventory_spare_part(
                db=db, delta=-target_quantity, user_id=current_user.id, db_obj=target_spare_part
            )
        else:
            delta = old_quantity - target_quantity
            if delta != 0:
                update_inventory_spare_part(
                    db=db, delta=delta, user_id=current_user.id, db_obj=target_spare_part
                )

        crud_order_spare_part.update(db, db_obj=db_order_spare_part, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="order_spare_parts",
                entity_id=order_spare_part_id,
                details=audit_details,
            )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar el repuesto de la orden. Verifique los datos ingresados."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return crud_order_spare_part.get_by_id(db, order_spare_part_id, options=ORDER_SPARE_PARTS_LOAD_OPTIONS)


@router.delete(
    "/{order_spare_part_id}", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def delete_order_spare_part(
    order_spare_part_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes an order spare part by ID and returns item to inventory if tracked."""
    db_order_spare_part = crud_order_spare_part.get_by_id(db, id=order_spare_part_id, options=ORDER_SPARE_PARTS_LOAD_OPTIONS)
    if not db_order_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_ORDER_SPARE_PARTS,
        )
    
    spare_part_name = db_order_spare_part.spare_part.name if db_order_spare_part.spare_part else "Desconocido"
    repair_order_id = db_order_spare_part.repair_order_id

    try:
        update_inventory_spare_part(
            db=db,
            delta=db_order_spare_part.quantity,
            user_id=current_user.id,
            spare_part_id=db_order_spare_part.spare_part_id
        )

        crud_order_spare_part.delete(db, db_obj=db_order_spare_part)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="order_spare_parts",
            entity_id=order_spare_part_id,
            details=f"Repuesto '{spare_part_name}' eliminado de la orden #{repair_order_id}",
        )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el repuesto de la orden debido a dependencias asociadas."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return {"message": f"Repuesto '{spare_part_name}' de la orden #{repair_order_id} eliminado correctamente"}