from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app.database import get_db
from app import (
    EmployeeDirectory, EmployeeDirectoryCreate, EmployeeDirectoryResponse, 
    EmployeeDirectoryUpdate, UserCreate, crud_employee, crud_user
)
from app.utils import generate_employee_code, generate_user_credentials
from app.api.deps import require_roles
from app.core import LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/employees", tags=["Employee Directory"])

@router.post("/", response_model=EmployeeDirectoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_employee(employee_in: EmployeeDirectoryCreate, db: Session = Depends(get_db)):
    """Creates a new employee in the database."""
    errors = []

    fields_to_validate = [
        ("national_id", "Ya existe un empleado con esta cédula"),
        ("tax_id", "Ya existe un empleado con este RIF"),
        ("national_id_doc", "Ya existe un empleado con esta foto de la cédula"),
        ("tax_id_doc", "Ya existe un empleado con este RIF digital"),
        ("profile_photo", "Ya existe un empleado con esta foto de perfil"),
    ]

    for field, error_msg in fields_to_validate:
        new_val = getattr(employee_in, field, None)

        if new_val:
            if crud_employee.get_by_other(db, value=str(new_val), field=field):
                errors.append(error_msg)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=errors,
        )
    
    if not employee_in.occupation:
        employee_in.occupation = "Staff"
    
    if not employee_in.employee_code:
        employee_in.employee_code = generate_employee_code(employee_in.occupation, db)
        
    db_employee = crud_employee.create(db, obj_in=employee_in)

    credentials = generate_user_credentials(
        full_name=db_employee.full_name,
        occupation=db_employee.occupation,
        db=db
    )

    user_in = UserCreate(
        username=credentials["username"],
        password=credentials["password"],
        employee_id=db_employee.id,
        role=LEVEL_BASIC,
        is_active=True
    )
    crud_user.create(db, obj_in=user_in)

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
                cast(EmployeeDirectory.id, String), EmployeeDirectory.employee_code, 
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
            detail="Empleado no encontrado"
        )
    return db_employee

@router.get("/{employee_id}", response_model=EmployeeDirectoryResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_employee_by_id(employee_id: int, db: Session = Depends(get_db)):
    """Retrieves an employee by its ID."""
    db_employee = crud_employee.get_by_id(db, id=employee_id)
    if not db_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Empleado no encontrado"
        )
    return db_employee

@router.patch("/{employee_id}", response_model=EmployeeDirectoryResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_employee(
    employee_id: int,
    employee_in: EmployeeDirectoryUpdate,
    db: Session = Depends(get_db)
):
    """Updates an employee partially or completely."""
    db_employee = crud_employee.get_by_id(db, id=employee_id)
    if not db_employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Empleado no encontrado"
        )

    errors = []

    fields_to_validate = [
        ("national_id", "Ya existe un empleado con esta cédula"),
        ("tax_id", "Ya existe un empleado con este RIF"),
        ("employee_code", "Ya existe un empleado con este código de empleado"),
        ("national_id_doc", "Ya existe un empleado con esta foto de la cédula"),
        ("tax_id_doc", "Ya existe un empleado con este RIF digital"),
        ("profile_photo", "Ya existe un empleado con esta foto de perfil"),
    ]

    for field, error_msg in fields_to_validate:
        new_val = getattr(employee_in, field, None)
        current_val = getattr(db_employee, field, None)

        if new_val and new_val != current_val:
            if crud_employee.get_by_other(db, value=str(new_val), field=field):
                errors.append(error_msg)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=errors,
        )
        
    return crud_employee.update(db, db_obj=db_employee, obj_in=employee_in)