from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from app import (
    Technician, TechnicianCreate, 
    TechnicianResponse, TechnicianUpdate, 
    EmployeeDirectory, User,
    crud_technician, crud_employee, get_db
    )
from app.utils import (
    validate_unique_fields_by_create,
    validate_unique_fields_by_update, 
    build_audit_change_details,
)
from app.api.deps import get_current_user, require_roles
from app.services import log_action
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/technicians", tags=["Technicians"])

def format_short_name(full_name: str) -> str:
    """Extrae primer nombre y primer apellido si es un nombre completo largo."""
    parts = full_name.strip().split()
    if len(parts) >= 4:
        return f"{parts[0]} {parts[2]}"
    elif len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return full_name

@router.post("/", response_model=TechnicianResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_technician(technician_in: TechnicianCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Creates a new technician record (linked to an employee or external)."""
    create_data = technician_in.model_dump(exclude_unset=True)

    if technician_in.employee_id is not None:
        db_employee = crud_employee.get_by_id(db, technician_in.employee_id)

        if not db_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=["El empleado especificado no existe."],
            )
        
        full_name = db_employee.full_name
        create_data["name"] = format_short_name(full_name)

        existing_tech = crud_technician.get_by_other(
            db, value=technician_in.employee_id, field="employee_id"
        )
        if existing_tech:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=["Este empleado ya tiene registro como técnico."],
            )

    try:
        db_technician = crud_technician.create(db, obj_in=create_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el técnico. Es posible que ya lo hayan registrado."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        entity="technicians",
        entity_id=db_technician.id,
        details=f"Tecnico registrado: {create_data.get('name')} (ID: {db_technician.id})",
    )
        
    return crud_technician.get_by_id(db, id=db_technician.id)

@router.get("/", response_model=List[TechnicianResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_technicians(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of technicians or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        search_query = q
        tech_by_code = crud_technician.get_by_code(db, employee_code=search_query)
        if tech_by_code:
            return [tech_by_code]

        return crud_technician.search_ilike(
            db=db, 
            query=search_query, 
            search_fields=[
                cast(Technician.id, String),
                cast(Technician.commission, String), 
                Technician.name,
                EmployeeDirectory.national_id
            ],
            joins=[EmployeeDirectory],
            limit=limit
        )
    return crud_technician.get_multi(db, skip=skip, limit=limit)

@router.get("/employee/{employee_id}",response_model=TechnicianResponse,dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_technician_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get technician record using the internal Employee ID."""
    db_technician = crud_technician.get_by_other(
        db, value=employee_id, field="employee_id"
    )
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["No existe un técnico asociado a este ID de empleado."],
        )
    return db_technician

@router.get("/{technician_id}", response_model=TechnicianResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_technician(technician_id: int, db: Session = Depends(get_db)):
    """Get a specific technician by its primary key (Technician ID)."""
    db_technician = crud_technician.get_by_id(db, id=technician_id)
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Técnico no encontrado."],
        )
    return db_technician

@router.patch("/{technician_id}", response_model=TechnicianResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_technician(technician_id: int,technician_in: TechnicianUpdate,db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Updates a technician's commission, active status, or assigned employee ID."""
    db_technician = crud_technician.get_by_id(db, id=technician_id)
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Técnico no encontrado."]
        )

    update_data = technician_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_technician
    
    if (technician_in.employee_id is not None
        and technician_in.employee_id != db_technician.employee_id 
    ):
        employee_id = update_data.get("employee_id")
        db_employee = crud_employee.get_by_id(db, id=employee_id)
        if not db_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=["El empleado especificado no existe."]
            )

        full_name = db_employee.full_name
        update_data["name"] = format_short_name(full_name)

        existing_tech = crud_technician.get_by_other(db, value=employee_id, field="employee_id")
        if existing_tech and existing_tech.id != technician_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=["Este empleado ya tiene registro como técnico."]
            )

    audit_details = build_audit_change_details(
        db_obj=db_technician,
        update_data=update_data,
        entity_name="Técnico",
    )

    try:
        db_technician = crud_technician.update(db, db_obj=db_technician, obj_in=update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el técnico. Es posible que ya lo hayan registrado."]
            )

    if audit_details:
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="technicians",
            entity_id=technician_id,
            details=audit_details
        )
        
    return crud_technician.get_by_id(db, id=technician_id)

@router.delete("/{technician_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_technician(technician_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Soft delete / Deactivate a technician."""
    db_technician = crud_technician.get_by_id(db, technician_id)
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=["Técnico no encontrado"],
        )

    try:
        crud_technician.delete(db, db_technician)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Error al eliminar el técnico, es posible que ya este eliminado."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        entity="technicians",
        entity_id=technician_id,
        details=f"Técnico desactivado: {db_technician.name} (ID: {db_technician.id})",
    )

    return {"message": f"Técnico {db_technician.name} #(ID: {db_technician.id}) desactivado correctamente"}