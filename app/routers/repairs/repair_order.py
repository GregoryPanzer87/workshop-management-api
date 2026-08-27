from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app import (
    RepairOrder, RepairOrderCreate, RepairOrderResponse, 
    RepairOrderDetailResponse, RepairOrderUpdate, 
    User, Device, Client, crud_repair_order, 
    crud_client, crud_device, crud_technician
)
from app.utils import (
    build_audit_change_details,
    validate_exists_by_create, validate_exists_by_update
)
from app.services import log_action
from app.api.deps import require_roles, get_current_user
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/repairs_orders", tags=["Repairs Orders"])

REPAIR_ORDER_LOAD_OPTIONS = [
    joinedload(RepairOrder.client),
    joinedload(RepairOrder.device).joinedload(Device.device_type),
    joinedload(RepairOrder.device).joinedload(Device.device_brand),
]
NOT_FOUND_REPAIR_ORDER = ["Orden de reparación no encontrada"]
INTEGRITY_ERROR = ["Ocurrió un conflicto al crear la orden de reparación. Verifique los datos ingresados."]

@router.post("/", response_model=RepairOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_repair_order(repair_order_in: RepairOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new repair order in the database."""
    create_data = repair_order_in.model_dump(exclude_unset=True)
    if current_user.role not in LEVEL_ADVANCE:
            create_data.pop('legacy_order_id', None)

    existence_checks = [
        (crud_client, "client_id", "El cliente especificado no existe"),
        (crud_device, "device_id", "El equipo especificado no existe"),
        (crud_technician, "technician_id", "El tecnico especificado no existe"),
    ]

    errors_404 = validate_exists_by_create(db, create_data, existence_checks)
    if errors_404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors_404
        )

    try: 
        db_repair_order = crud_repair_order.create(db, obj_in=create_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )

    log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        entity="repair_orders",
        entity_id=db_repair_order.id,
        details=f"Orden creada: (ID: {db_repair_order.id})",
    )

    return crud_repair_order.get_by_id(db, id=db_repair_order.id, options=REPAIR_ORDER_LOAD_OPTIONS)

@router.get("/", response_model=List[RepairOrderResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_repairs_orders(
    q: Optional[str] = None,
    client_id: Optional[int] = None,
    device_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of repairs orders or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_repair_order.search_ilike(
            db=db, 
            query=q, 
            search_fields=[cast(RepairOrder.id, String), 
                           cast(RepairOrder.entry_date, String),
                           cast(RepairOrder.exit_date, String),
                           RepairOrder.status,
                           Device.serial_number,
                           Client.name,
                           Client.national_id
            ],
            joins=[Device, Client],
            options=REPAIR_ORDER_LOAD_OPTIONS,      
            limit=limit
        )
    if client_id is not None:
        if not crud_client.get_by_id(db, client_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=["El cliente especificado no existe"]
            )
        return crud_repair_order.list_get_by_other(db=db, value=client_id, field="client_id", options=REPAIR_ORDER_LOAD_OPTIONS, skip=skip, limit=limit)

    if device_id is not None:
        if not crud_device.get_by_id(db, device_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=["El equipo especificado no existe"]
            )
        return crud_repair_order.list_get_by_other(db=db, value=device_id, field="device_id", options=REPAIR_ORDER_LOAD_OPTIONS, skip=skip, limit=limit)
    
    return crud_repair_order.get_multi(db, options=REPAIR_ORDER_LOAD_OPTIONS, skip=skip, limit=limit)


@router.get("/{repair_order_id}", response_model=RepairOrderDetailResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_repair_order_by_id(repair_order_id: int, db: Session = Depends(get_db)):
    """Retrieves a single repair order by its ID."""
    db_repair_order = crud_repair_order.get_by_id(db, id=repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS)
    if not db_repair_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_REPAIR_ORDER
        )
    return db_repair_order

@router.patch("/{repair_order_id}", response_model=RepairOrderResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def update_repair_order(repair_order_id: int, repair_order_in: RepairOrderUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update a repair order partially or completely."""
    db_repair_order = crud_repair_order.get_by_id(db, id=repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS)
    if not db_repair_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_REPAIR_ORDER
        )

    update_data = repair_order_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_repair_order

    if current_user.role not in LEVEL_ADVANCE:
        update_data.pop('legacy_order_id', None)
    if current_user.role not in LEVEL_MEDIUM:
        update_data.pop('client_id', None)
        update_data.pop('device_id', None)
        update_data.pop('technician_id', None)
    else:
        existence_checks = [
            (crud_client, "client_id", "El cliente especificado no existe"),
            (crud_device, "device_id", "El equipo especificado no existe"),
            (crud_technician, "technician_id", "El tecnico especificado no existe"),
        ]

        errors_404 = validate_exists_by_update(db, update_data, existence_checks)
        if errors_404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=errors_404
            )

    if not update_data:
            return db_repair_order

    audit_details = build_audit_change_details(
        db_obj=db_repair_order,
        update_data=update_data,
        entity_name="Orden de Reparación",
    )

    try: 
        crud_repair_order.update(db, db_obj=db_repair_order, obj_in=update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )

    if audit_details:
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="repair_orders",
            entity_id=repair_order_id,
            details=audit_details
        )
    
    return crud_repair_order.get_by_id(db, id=repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS)

@router.delete("/{repair_order_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_repair_order(repair_order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_repair_order = crud_repair_order.get_by_id(db, id=repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS)
    if not db_repair_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_REPAIR_ORDER
        )

    try:
        crud_repair_order.delete(db, db_obj=db_repair_order)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar la orden de reparación porque tiene equipos u otros registros asociados."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        entity="repair_orders",
        entity_id=repair_order_id,
        details=f"Orden de reparación eliminada: (ID de equipo: {db_repair_order.device.id}) (ID de cliente: {db_repair_order.client.id})",
    )

    return {"message": f"Orden de reparación #{repair_order_id} eliminada correctamente"}