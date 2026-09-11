from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app import (
    EmployeeDirectory, EmployeeDirectoryCreate, EmployeeDirectoryResponse, 
    EmployeeDirectoryUpdate, User, crud_employee
)
from app.utils import(
    generate_employee_code, 
    generate_user_credentials,
    validate_unique_fields_by_create,
    validate_unique_fields_by_update, 
    build_audit_change_details,
)
from app.services import log_action
from app.api.deps import require_roles, get_current_user
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/employees", tags=["Employee Directory"])

NOT_FOUND_EMPLOYEE = ["Empleado no encontrado"]
INTEGRITY_ERROR = ["Ocurrió un conflicto inesperado"]

@router.post("/", response_model=EmployeeDirectoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_employee(
    employee_in: EmployeeDirectoryCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new employee in the database and generates initial credentials suggestion."""
    create_data = employee_in.model_dump(exclude_unset=True)

    unique_fields = [
        ("national_id", "Ya existe un empleado con esta cédula"),
        ("tax_id", "Ya existe un empleado con este RIF"),
        ("national_id_doc", "Ya existe un empleado con esta foto de la cédula"),
        ("tax_id_doc", "Ya existe un empleado con este RIF digital"),
        ("profile_photo", "Ya existe un empleado con esta foto de perfil"),
    ]

    errors_409 = validate_unique_fields_by_create(
        db, 
        crud_repo=crud_employee, 
        create_data=create_data, 
        unique_fields=unique_fields
    )

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    occupation = create_data.get("occupation") or "Staff"
    create_data["occupation"] = occupation
    
    if not create_data.get("employee_code"):
        create_data["employee_code"] = generate_employee_code(occupation, db)

    try:
        db_employee = crud_employee.create(db, obj_in=create_data)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="employee_directory",
            entity_id=db_employee.id,
            details=f"Empleado registrado: {db_employee.full_name} (ID: {db_employee.id})",
        )

        credentials = generate_user_credentials(
            full_name=db_employee.full_name,
            occupation=db_employee.occupation,
            db=db
        )
    
        db.commit()
        db.refresh(db_employee)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )
    except Exception as e:
        db.rollback()
        raise e

    response = EmployeeDirectoryResponse.model_validate(db_employee)
    response.initial_credentials = credentials
    return response

@router.get("/", response_model=List[EmployeeDirectoryResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_employees(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of employees or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_employee.search_ilike(
            db=db, 
            query=q, 
            search_fields=[
                cast(EmployeeDirectory.entry_date, String), EmployeeDirectory.employee_code, 
                EmployeeDirectory.full_name, EmployeeDirectory.tax_id, EmployeeDirectory.national_id,
                EmployeeDirectory.short_address
            ], 
            limit=limit
        )
    return crud_employee.get_multi(db, skip=skip, limit=limit)

@router.get("/code/{employee_code}", response_model=EmployeeDirectoryResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_employee_by_code(employee_code: str, db: Session = Depends(get_db)):
    """Retrieves a employee by its employee code."""
    db_employee = crud_employee.get_by_other(db, value=employee_code, field="employee_code")
    if not db_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_EMPLOYEE
        )
    return db_employee

@router.get("/{employee_id}", response_model=EmployeeDirectoryResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_employee_by_id(employee_id: int, db: Session = Depends(get_db)):
    """Retrieves an employee by its ID."""
    db_employee = crud_employee.get_by_id(db, id=employee_id)
    if not db_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_EMPLOYEE
        )
    return db_employee

@router.patch("/{employee_id}", response_model=EmployeeDirectoryResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_employee(
    employee_id: int,
    employee_in: EmployeeDirectoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates an employee partially or completely."""
    db_employee = crud_employee.get_by_id(db, id=employee_id)
    if not db_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_EMPLOYEE
        )

    is_admin = current_user.role in LEVEL_ADVANCE
    
    if not db_employee.is_active and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=["No tiene permisos para modificar este empleado porque está inactivo."]
        )

    update_data = employee_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_employee

    unique_fields = [
        ("national_id", "Ya existe un empleado con esta cédula"),
        ("tax_id", "Ya existe un empleado con este RIF"),
        ("employee_code", "Ya existe un empleado con este código de empleado"),
        ("national_id_doc", "Ya existe un empleado con esta foto de la cédula"),
        ("tax_id_doc", "Ya existe un empleado con este RIF digital"),
        ("profile_photo", "Ya existe un empleado con esta foto de perfil"),
    ]

    errors_409 = validate_unique_fields_by_update(
        db, 
        crud_repo=crud_employee, 
        db_obj=db_employee, 
        update_data=update_data, 
        unique_fields=unique_fields
    )
    
    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    audit_details = build_audit_change_details(
        db_obj=db_employee,
        update_data=update_data,
        entity_name="Empleado",
    )

    try: 
        db_employee = crud_employee.update(db, db_obj=db_employee, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="employee_directory",
                entity_id=employee_id,
                details=audit_details
            )
    
        db.commit()
        db.refresh(db_employee)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )
    except Exception as e:
        db.rollback()
        raise e
    
    return db_employee

@router.patch("/{employee_id}/activate", response_model=EmployeeDirectoryResponse, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def activate_employee(
    employee_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Reactivates a deactivated employee record."""
    db_employee = crud_employee.get_by_id(db, id=employee_id)
    if not db_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_EMPLOYEE,
        )

    if db_employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["El técnico ya se encuentra activo."],
        )

    try:
        db_employee = crud_employee.activate(db, db_obj=db_employee)

        log_action(
            db,
            user_id=current_user.id,
            action="ACTIVATE",
            entity="employee_directory",
            entity_id=employee_id,
            details=f"Empleado reactivado: {db_employee.full_name} (ID: {employee_id})",
        )

        db.commit()
        db.refresh(db_employee)
    except Exception as e:
        db.rollback()
        raise e

    return db_employee

@router.delete("/{employee_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_employee(employee_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Soft delete / Deactivate an employee."""
    db_employee = crud_employee.get_by_id(db, employee_id)
    if not db_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_EMPLOYEE,
        )

    if not db_employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["El empleado ya se encuentra desactivado."],
        )

    try:
        crud_employee.deactivate(db, db_employee)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="employee_directory",
            entity_id=employee_id,
            details=f"Empleado desactivado: {db_employee.full_name} (ID: {db_employee.id})",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Error al eliminar el empleado, es posible que ya este eliminado."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return {"message": f"Empleado {db_employee.full_name} (ID: {db_employee.id}) desactivado correctamente"}