from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from app import (
    Technician, TechnicianCreate, 
    TechnicianResponse, TechnicianUpdate, 
    EmployeeDirectory, User,
    crud_technician, crud_employee, get_db
)
from app.utils import build_audit_change_details
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

NOT_FOUND_TECHNICIAN = ["Técnico no encontrado."]
NOT_FOUND_EMPLOYEE = ["El emplado especificado no existe."]

@router.post("/", response_model=TechnicianResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_technician(technician_in: TechnicianCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Creates a new technician record (linked to an employee or external)."""
    create_data = technician_in.model_dump(exclude_unset=True)

    if technician_in.employee_id is not None:
        db_employee = crud_employee.get_by_id(db, technician_in.employee_id)

        if not db_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=NOT_FOUND_EMPLOYEE,
            )

        if not db_employee.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=["Este empleado no es válido. Elija otro empleado."],
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

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="technicians",
            entity_id=db_technician.id,
            details=f"Técnico registrado: {create_data.get('name')} (ID: {db_technician.id})",
        )

        db.commit()
        db.refresh(db_technician)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el técnico. Es posible que ya lo hayan registrado."]
        )
    except Exception as e:
        db.rollback()
        raise e
        
    return db_technician

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
        return crud_technician.search_ilike(
            db=db, 
            query=q, 
            search_fields=[
                cast(Technician.id, String),
                cast(Technician.commission, String), 
                Technician.name,
                EmployeeDirectory.national_id,
                EmployeeDirectory.employee_code
            ],
            joins=[EmployeeDirectory],
            limit=limit
        )
    return crud_technician.get_multi(db, skip=skip, limit=limit)

@router.get("/employee/{employee_id}", response_model=TechnicianResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
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
            detail=NOT_FOUND_TECHNICIAN,
        )
    return db_technician

@router.patch("/{technician_id}", response_model=TechnicianResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_technician(
    technician_id: int,
    technician_in: TechnicianUpdate,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Updates a technician's commission or assigned employee ID."""
    db_technician = crud_technician.get_by_id(db, id=technician_id)
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_TECHNICIAN
        )

    is_admin = current_user.role in LEVEL_ADVANCE

    if db_technician.employee and not db_technician.employee.is_active and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=["No tiene permisos para modificar un técnico cuyo empleado está inactivo."]
        )

    update_data = technician_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_technician

    if "employee_id" in update_data:
        new_employee_id = update_data["employee_id"]

        if new_employee_id is not None and new_employee_id != db_technician.employee_id:
            db_employee = crud_employee.get_by_id(db, id=new_employee_id)
            if not db_employee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=NOT_FOUND_EMPLOYEE
                )
            
            if not db_employee.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=["El nuevo empleado no está activo. Elija un empleado activo."],
                )

            existing_tech = crud_technician.get_by_other(db, value=new_employee_id, field="employee_id")
            if existing_tech and existing_tech.id != technician_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=["Este empleado ya tiene un registro activo como técnico."]
                )

            update_data["name"] = format_short_name(db_employee.full_name)

    audit_details = build_audit_change_details(
        db_obj=db_technician,
        update_data=update_data,
        entity_name="Técnico",
    )

    try:
        db_technician = crud_technician.update(db, db_obj=db_technician, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="technicians",
                entity_id=technician_id,
                details=audit_details
            )

        db.commit()
        db.refresh(db_technician)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al actualizar el técnico."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return db_technician

@router.patch("/{technician_id}/activate", response_model=TechnicianResponse, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def activate_technician(
    technician_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Reactivates a deactivated technician record."""
    db_technician = crud_technician.get_by_id(db, id=technician_id)
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_TECHNICIAN,
        )

    if db_technician.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["El técnico ya se encuentra activo."],
        )

    if db_technician.employee and not db_technician.employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["No se puede activar el técnico porque su empleado asociado está inactivo."],
        )

    try:
        db_technician = crud_technician.activate(db, db_obj=db_technician)

        log_action(
            db,
            user_id=current_user.id,
            action="ACTIVATE",
            entity="technicians",
            entity_id=technician_id,
            details=f"Técnico reactivado: {db_technician.name} (ID: {technician_id})",
        )

        db.commit()
        db.refresh(db_technician)
    except Exception as e:
        db.rollback()
        raise e

    return db_technician

@router.delete("/{technician_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_technician(technician_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Soft delete / Deactivate a technician."""
    db_technician = crud_technician.get_by_id(db, technician_id)
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_TECHNICIAN,
        )

    if not db_technician.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=["El técnico ya se encuentra desactivado."],
        )

    tech_name = db_technician.name

    try:
        crud_technician.deactivate(db, db_technician)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="technicians",
            entity_id=technician_id,
            details=f"Técnico desactivado: {tech_name} (ID: {technician_id})",
        )

        db.commit()
        db.refresh(db_technician)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Error al eliminar el técnico. Intente nuevamente"]
        )
    except Exception as e:
        db.rollback()
        raise e

    return {"message": f"Técnico {tech_name} (ID: {technician_id}) desactivado correctamente"}