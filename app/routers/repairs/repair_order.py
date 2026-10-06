from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError
from collections import defaultdict

from app.database import get_db
from app import (
    RepairOrder, RepairOrderCreate, RepairOrderResponse, 
    RepairOrderDetailResponse, RepairOrderUpdate, 
    RepairOrderUpdateStatus, RepairOrderBatchCreate, 
    RepairOrderUpdateDescription, RepairOrderUpdateTechnician, UserRole,
    User, Device, Customer, Technician,
    crud_repair_order, crud_customer, crud_device, crud_technician
)
from app.utils import (
    build_audit_change_details,
    validate_exists_by_create, validate_exists_by_update,
    generate_order_number, generate_order_numbers_batch
)
from app.services import log_action
from app.api.deps import require_roles, get_current_user, get_current_technician
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/repairs_orders", tags=["Repairs Orders"])

REPAIR_ORDER_LOAD_OPTIONS = [
    joinedload(RepairOrder.customer),
    joinedload(RepairOrder.device).joinedload(Device.device_type),
    joinedload(RepairOrder.device).joinedload(Device.device_brand),
    joinedload(RepairOrder.technician)
]
NOT_FOUND_REPAIR_ORDER = ["Orden de reparación no encontrada"]
INTEGRITY_ERROR = ["Ocurrió un conflicto al crear la orden de reparación. Verifique los datos ingresados."]

def get_current_technician_safe(current_user: User, db: Session):
    """Resuelve de forma segura el técnico actual sin fallar si el usuario es administrador puro."""
    try:
        if getattr(current_user, "technician_id", None):
            return crud_technician.get_by_id(db, current_user.technician_id)
        if getattr(current_user, "employee_id", None):
            return crud_technician.get_by_other(db, value=current_user.employee_id, field="employee_id")
    except Exception:
        pass
    return None

@router.post("/", response_model=RepairOrderResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_repair_order(repair_order_in: RepairOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new repair order in the database."""
    create_data = repair_order_in.model_dump(exclude_unset=True)

    if current_user.role not in LEVEL_ADVANCE and 'legacy_order_number' in create_data and create_data['legacy_order_number']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=["No tienes permisos para crear una orden de reparación antigua"]
        )

    existence_checks = [
        (crud_customer, "customer_id", "El cliente especificado no existe"),
        (crud_device, "device_id", "El equipo especificado no existe"),
        (crud_technician, "technician_id", "El técnico especificado no existe"),
    ]

    errors_404 = validate_exists_by_create(db, create_data, existence_checks)
    if errors_404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors_404
        )

    if create_data.get("legacy_order_number"):
        existing_legacy = crud_repair_order.get_by_other(
            db=db, value=create_data["legacy_order_number"], field="legacy_order_number"
        )
        if existing_legacy:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=["El número de orden antigua ya se encuentra registrado."]
            )

    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            if not create_data.get("legacy_order_number"):
                create_data["order_number"] = generate_order_number(db=db, target_date=create_data.get("entry_date"))

            db_repair_order = crud_repair_order.create(db, obj_in=create_data)
            log_action(
                db,
                user_id=current_user.id,
                action="CREATE",
                entity="repair_orders",
                entity_id=db_repair_order.id,
                details=f"Orden creada: (ID: {db_repair_order.id})",
            )
            db.commit()
            db.refresh(db_repair_order)
            break
        except IntegrityError:
            db.rollback()   
            if attempt == MAX_RETRIES - 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=INTEGRITY_ERROR
                )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=[str(e)]
            )

    return crud_repair_order.get_by_id(db, id=db_repair_order.id, options=REPAIR_ORDER_LOAD_OPTIONS)


@router.post("/batch", response_model=List[RepairOrderResponse], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_repair_orders_batch(
    batch_in: RepairOrderBatchCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Creates multiple repair orders in a single atomic transaction."""
    if not batch_in.orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["La lista de órdenes de reparación no puede estar vacía."]
        )

    orders_data = [order.model_dump(exclude_unset=True) for order in batch_in.orders]

    if current_user.role not in LEVEL_ADVANCE:
        if any(item.get("legacy_order_number") for item in orders_data):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=["No tienes permisos para crear órdenes de reparación antiguas."]
            )

    legacy_numbers = [item["legacy_order_number"] for item in orders_data if item.get("legacy_order_number")]
    if len(legacy_numbers) != len(set(legacy_numbers)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Existen números de orden antigua duplicados en la misma petición."]
        )

    existence_checks = [
        (crud_customer, "customer_id", "El cliente especificado no existe"),
        (crud_device, "device_id", "El equipo especificado no existe"),
        (crud_technician, "technician_id", "El técnico especificado no existe"),
    ]

    for index, data in enumerate(orders_data):
        errors_404 = validate_exists_by_create(db, data, existence_checks)
        if errors_404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=[f"Error en el elemento {index + 1}: {err}" for err in errors_404]
            )

        if data.get("legacy_order_number"):
            existing_legacy = crud_repair_order.get_by_other(
                db=db, value=data["legacy_order_number"], field="legacy_order_number"
            )
            if existing_legacy:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=[f"El número de orden antigua '{data['legacy_order_number']}' ya se encuentra registrado."]
                )

    grouped_by_date = defaultdict(list)
    for idx, item in enumerate(orders_data):
        if not item.get("legacy_order_number"):
            entry_dt = item.get("entry_date")
            grouped_by_date[entry_dt].append(idx)

    for target_date, indices in grouped_by_date.items():
        generated_nums = generate_order_numbers_batch(db=db, count=len(indices), target_date=target_date)
        for idx, gen_num in zip(indices, generated_nums):
            orders_data[idx]["order_number"] = gen_num

    created_ids = []
    try:
        for data in orders_data:
            db_repair_order = crud_repair_order.create(db, obj_in=data)
            created_ids.append(db_repair_order.id)

            log_action(
                db,
                user_id=current_user.id,
                action="CREATE",
                entity="repair_orders",
                entity_id=db_repair_order.id,
                details=f"Orden creada en lote: (ID: {db_repair_order.id})",
            )
            db.refresh(db_repair_order)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=[str(e)]
        )

    db_repair_orders = crud_repair_order.get_multi(db=db, identities=created_ids, options=REPAIR_ORDER_LOAD_OPTIONS)
    return db_repair_orders


@router.get("/", response_model=List[RepairOrderResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_repairs_orders(
    q: Optional[str] = None,
    status: Optional[str] = None,
    only_mine: bool = False,
    customer_id: Optional[int] = None,
    device_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a paginated list of repairs orders with role and technician ownership rules."""
    current_tech = get_current_technician_safe(current_user, db)

    force_own_orders = False
    if current_user.role == UserRole.TECHNICIAN:
        force_own_orders = True
    elif only_mine and current_tech:
        force_own_orders = True

    filters_eq = {}
    if status:
        filters_eq["status"] = status
    if force_own_orders and current_tech:
        filters_eq["technician_id"] = current_tech.id

    filters_eq_arg = filters_eq if filters_eq else None
    clean_q = q.strip() if q and q.strip() else None

    if clean_q or filters_eq_arg:
        return crud_repair_order.search_ilike(
            db=db, 
            query=clean_q if clean_q else "", 
            search_fields=[
                RepairOrder.order_number,
                RepairOrder.legacy_order_number,
                cast(RepairOrder.entry_date, String),
                cast(RepairOrder.exit_date, String),
                RepairOrder.status,
                Device.serial_number,
                Customer.name,
                Customer.national_id,
                Customer.phone_number,
                Technician.name
            ],
            filters_eq=filters_eq_arg,
            joins=[Device, Customer, Technician],
            options=REPAIR_ORDER_LOAD_OPTIONS,      
            limit=limit,
            skip=skip
        )

    if customer_id is not None:
        return crud_repair_order.list_get_by_other(db=db, value=customer_id, field="customer_id", options=REPAIR_ORDER_LOAD_OPTIONS, skip=skip, limit=limit)

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

@router.get(
    "/my_orders",
    response_model=List[RepairOrderResponse],
    dependencies=[Depends(require_roles(LEVEL_BASIC))]
)
def read_my_repair_orders(
    db: Session = Depends(get_db),
    current_tech: Technician = Depends(get_current_technician),
):
    """Retrieves the repair orders assigned to the authenticated technician."""
    return crud_repair_order.list_get_by_other(
        db=db, 
        value=current_tech.id, 
        field="technician_id"
    )

@router.patch("/{repair_order_id}", response_model=RepairOrderResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
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

    errors_403 = []

    if current_user.role not in LEVEL_ADVANCE:
        if db_repair_order.legacy_order_number:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=["No tienes permisos para modificar esta orden de reparación"]
            )
        if 'legacy_order_number' in update_data:
            errors_403.append("asignar un número de orden antigua")

    if errors_403:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=[f"No tienes permisos para: {', '.join(errors_403)}"]
        )
    
    existence_checks = [
        (crud_customer, "customer_id", "El cliente especificado no existe"),
        (crud_device, "device_id", "El equipo especificado no existe"),
    ]

    errors_404 = validate_exists_by_update(db, update_data, existence_checks)
    if errors_404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors_404
        )

    if update_data.get("legacy_order_number"):
        existing_legacy = crud_repair_order.get_by_other(
            db=db, value=update_data["legacy_order_number"], field="legacy_order_number"
        )
        if existing_legacy and existing_legacy.id != repair_order_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=["El número de orden antigua ya se encuentra registrado en otra orden."]
            )

    if "entry_date" in update_data or "exit_date" in update_data:
        entry_date = update_data.get("entry_date", db_repair_order.entry_date)
        exit_date = update_data.get("exit_date", db_repair_order.exit_date)

        if (entry_date and exit_date) and (entry_date > exit_date):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=["No puedes actualizar los datos, la fecha de salida es anterior a la fecha de entrada."]
            )

    audit_details = build_audit_change_details(
        db_obj=db_repair_order,
        update_data=update_data,
        entity_name="Orden de Reparación",
    )

    try: 
        crud_repair_order.update(db, db_obj=db_repair_order, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="repair_orders",
                entity_id=repair_order_id,
                details=audit_details
            )

        db.commit()
        db.refresh(db_repair_order)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=[str(e)]
        )
    
    return db_repair_order


@router.patch("/status/{repair_order_id}", response_model=RepairOrderUpdateStatus, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def update_status_repair_order(repair_order_id: int, repair_order_in: RepairOrderUpdateStatus, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_repair_order = crud_repair_order.get_by_id(db, id=repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS)
    if not db_repair_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_REPAIR_ORDER
        )

    old_status = db_repair_order.status
    new_status = repair_order_in.status.value if hasattr(repair_order_in.status, 'value') else repair_order_in.status

    if old_status == new_status or not new_status:
        return db_repair_order

    try: 
        crud_repair_order.status(db, db_obj=db_repair_order, obj_in=repair_order_in)

        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="repair_orders",
            entity_id=repair_order_id,
            details=f"Estado de la orden: (ID: {repair_order_id}) {old_status} -> {new_status}",
        )

        db.commit()
        db.refresh(db_repair_order)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=[str(e)]
        )
    
    return db_repair_order


@router.patch(
    "/description/{repair_order_id}",
    response_model=RepairOrderResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_repair_order_description(
    repair_order_id: int,
    description_in: RepairOrderUpdateDescription,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update only the description field of a repair order."""
    db_repair_order = crud_repair_order.get_by_id(
        db, id=repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS
    )
    if not db_repair_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_REPAIR_ORDER,
        )

    old_description = db_repair_order.description
    new_description = description_in.description.strip() if description_in.description else None

    if old_description == new_description:
        return db_repair_order

    try:
        crud_repair_order.description(db, db_obj=db_repair_order, obj_in=description_in)

        audit_detail = (
            f"Descripción actualizada en la orden #{db_repair_order.order_number}: "
            f"'{new_description if new_description else 'Sin descripción'}'"
        )
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="repair_orders",
            entity_id=repair_order_id,
            details=audit_detail[:255],
        )

        db.commit()
        db.refresh(db_repair_order)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar la descripción de la orden."],
        )
    except Exception as e:
        db.rollback()
        raise e

    return crud_repair_order.get_by_id(
        db, repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS
    )

@router.patch(
    "/technician/{repair_order_id}",
    response_model=RepairOrderResponse,
    dependencies=[Depends(require_roles(LEVEL_MEDIUM))],
)
def update_repair_order_technician(
    repair_order_id: int,
    technician_in: RepairOrderUpdateTechnician,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assigns or updates a technician to the order directly."""
    db_repair_order = crud_repair_order.get_by_id(
        db, id=repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS
    )
    if not db_repair_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_REPAIR_ORDER,
        )

    old_technician = db_repair_order.technician_id
    new_technician = technician_in.technician_id

    if old_technician == new_technician:
        return db_repair_order

    try:
        crud_repair_order.technician(db, db_obj=db_repair_order, obj_in=technician_in)

        audit_detail = (
            f"Técnico asignado actualizado en la orden #{db_repair_order.order_number or repair_order_id} "
            f"(Técnico ID: {old_technician} -> {new_technician})"
        )
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="repair_orders",
            entity_id=repair_order_id,
            details=audit_detail[:255],
        )

        db.commit()
        db.refresh(db_repair_order)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar el técnico de la orden."],
        )
    except Exception as e:
        db.rollback()
        raise e

    return crud_repair_order.get_by_id(
        db, repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS
    )


@router.delete("/{repair_order_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_repair_order(repair_order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_repair_order = crud_repair_order.get_by_id(db, id=repair_order_id, options=REPAIR_ORDER_LOAD_OPTIONS)
    if not db_repair_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_REPAIR_ORDER
        )

    if db_repair_order.legacy_order_number:
        legacy_order_number = db_repair_order.legacy_order_number
        message = {"message": f"Orden de reparación antigua #{legacy_order_number} eliminada correctamente"}
    else:
        order_number = db_repair_order.order_number
        message = {"message": f"Orden de reparación #{order_number} eliminada correctamente"}

    try:
        crud_repair_order.delete(db, db_obj=db_repair_order)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="repair_orders",
            entity_id=repair_order_id,
            details=f"Orden de reparación eliminada: #{repair_order_id} (ID de equipo: {db_repair_order.device_id}) (ID de cliente: {db_repair_order.customer_id})",
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar la orden de reparación porque existen registros o detalles asociados a ella."]
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=[str(e)]
        )

    return message