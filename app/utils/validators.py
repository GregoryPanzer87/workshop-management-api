from typing import Any, List, Tuple, Union, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

def validate_unique_fields_by_create(
    db: Session,
    crud_repo: Any,
    create_data: dict,
    unique_fields: List[Tuple[str, str]]
) -> List[str]:
    """Validates field uniqueness when creating a new record."""
    errors = []
    for field, error_msg in unique_fields:
        if field in create_data:
            new_val = create_data[field]
            new_val_str = str(new_val).strip() if new_val is not None else ""
            if new_val_str:
                existing = crud_repo.get_by_other(db, value=new_val_str, field=field)
                if existing:
                    errors.append(error_msg)
    return errors

#----------------------------------------------------------------------------------------------

def validate_unique_fields_by_update(
    db: Session,
    crud_repo: Any,
    db_obj: Any,
    update_data: dict,
    unique_fields: List[Tuple[str, str]]
) -> List[str]:
    """Validates field uniqueness when updating an existing record."""
    errors = []
    for field, error_msg in unique_fields:
        if field in update_data:
            new_val = update_data[field]
            current_val = getattr(db_obj, field, None)

            new_val_str = str(new_val).strip() if new_val is not None else ""
            current_val_str = str(current_val).strip() if current_val is not None else ""

            if new_val_str != "" and new_val_str != current_val_str:
                existing = crud_repo.get_by_other(db, value=new_val_str, field=field)
                if existing and existing.id != db_obj.id:
                    errors.append(error_msg)
    return errors

#----------------------------------------------------------------------------------------------

def validate_exists_by_create(
    db: Session,
    data: Union[BaseModel, dict],
    existence_checks: List[Tuple[Any, str, str]]
) -> List[str]:
    """
    Validates the existence of related foreign key entities when creating a record.
    Accepts either a Pydantic model instance or a plain dictionary.
    """
    errors = []
    for crud_repo, field_name, error_msg in existence_checks:
        
        if isinstance(data, dict):
            fk_id = data.get(field_name)
        else:
            fk_id = getattr(data, field_name, None)
            
        if fk_id is not None:
            if not crud_repo.get_by_id(db, id=fk_id):
                errors.append(error_msg)
    return errors

#----------------------------------------------------------------------------------------------

def validate_exists_by_update(
    db: Session,
    update_data: dict,
    existence_checks: List[Tuple[Any, str, str]]
) -> List[str]:
    """
    Validates the existence of related foreign key entities when updating a record.
    Only performs database checks for foreign key fields explicitly included in the update payload.
    """
    errors = []
    for crud_repo, field_name, error_msg in existence_checks:
        if field_name in update_data:
            fk_id = update_data[field_name]
            if fk_id is not None and not crud_repo.get_by_id(db, id=fk_id):
                errors.append(error_msg)
    return errors

#----------------------------------------------------------------------------------------------

def build_audit_change_details(
    db_obj: Any,
    update_data: dict,
    entity_name: str,
    max_length: int = 250
) -> Optional[str]:
    """
    Compares current object values with new values and generates a formatted audit detail string."""
    changes = []
    for field, new_val in update_data.items():
        old_val = getattr(db_obj, field, None)
        if old_val != new_val:
            changes.append(f"{field}: '{old_val}' -> '{new_val}'")

    if not changes:
        return None

    changes_str = "; ".join(changes)
    if entity_name == "Orden de Reparación":
        details = f"{entity_name} #{db_obj.id} modificado: {changes_str}"
    else:
        details = f"{entity_name} (ID: {db_obj.id}) modificado: {changes_str}"

    if len(details) > max_length:
        return details[: max_length - 3] + "..."

    return details