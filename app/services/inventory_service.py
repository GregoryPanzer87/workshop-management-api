from typing import Optional
from sqlalchemy.orm import Session
from app.services import log_action
from app import SparePart, SparePartUpdate, crud_spare_part

def update_inventory_spare_part(
    db: Session,
    delta: int,
    user_id: int,
    db_obj: Optional[SparePart] = None,
    spare_part_id: Optional[int] = None
) -> Optional[SparePart]:
    """Updates stock count if tracked (stock is not None) without blocking the order flow."""
    if delta == 0 and db_obj:
        return db_obj
    
    if spare_part_id and not db_obj:
        db_obj = crud_spare_part.get_by_id(db, id=spare_part_id)

    if not db_obj or db_obj.stock is None:
        return db_obj

    current_stock = db_obj.stock
    new_stock = current_stock + delta

    action_text = "incrementado" if delta > 0 else "disminuido"
    warning_text = " [ALERTA: STOCK BAJO/DESCUADRE]" if new_stock <= 0 else ""

    spare_part_in = SparePartUpdate(stock=new_stock)
    db_obj = crud_spare_part.update(db=db, db_obj=db_obj, obj_in=spare_part_in)

    log_action(
        db,
        user_id=user_id,
        action="UPDATE",
        entity="spare_parts",
        entity_id=db_obj.id,
        details=(
            f"Stock de '{db_obj.name}' (ID: {db_obj.id}) {action_text} en {abs(delta)} unid. "
            f"Nuevo stock: {new_stock}{warning_text}"
        )
    )
         
    return db_obj