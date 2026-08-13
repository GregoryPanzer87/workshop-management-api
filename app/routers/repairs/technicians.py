from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app import Technician, TechnicianCreate, TechnicianResponse, TechnicianUpdate, crud_technician, crud_employee, get_db
from app.api.deps import require_roles
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/technicians", tags=["Technicians"])

@router.post("/", response_model=TechnicianResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_technician(technician_in: TechnicianCreate, db: Session = Depends(get_db)):
    """Creates a new technician record (linked to an employee or external)."""
    if technician_in.employee_id is not None:
        db_employee = crud_employee.get_by_id(db, technician_in.employee_id)

        if not db_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El empleado especificado no existe",
            )

        existing_tech = crud_technician.get_other_id(
            db, id=technician_in.employee_id, field="employee_id"
        )
        if existing_tech:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este empleado ya tiene registro como técnico",
            )
        
    return crud_technician.create(db, obj_in=technician_in)

@router.get("/", response_model=List[TechnicianResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_technicians(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of technicians or performs a real-time search by sending 'q'."""
    if q and q.strip():
        search_query = q.strip()
        tech_by_code = crud_technician.get_by_code(db, employee_code=search_query)
        if tech_by_code:
            return [tech_by_code]

        return crud_technician.search_ilike(
            db=db, 
            query=search_query, 
            search_fields=[cast(Technician.id, String)],
            limit=limit
        )
    return crud_technician.get_multi(db, skip=skip, limit=limit)

@router.get("/employee/{employee_id}",response_model=TechnicianResponse,dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_technician_by_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get technician record using the internal Employee ID."""
    db_technician = crud_technician.get_other_id(
        db, id=employee_id, field="employee_id"
    )
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un técnico asociado a este ID de empleado",
        )
    return db_technician

@router.get("/{technician_id}", response_model=TechnicianResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_technician(technician_id: int, db: Session = Depends(get_db)):
    """Get a specific technician by its primary key (Technician ID)."""
    db_technician = crud_technician.get_by_id(db, id=technician_id)
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Técnico no encontrado",
        )
    return db_technician

@router.patch("/{technician_id}", response_model=TechnicianResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_technician(technician_id: int,technician_in: TechnicianUpdate,db: Session = Depends(get_db)):
    """Updates a technician's commission, active status, or assigned employee ID."""
    db_technician = crud_technician.get_by_id(db, id=technician_id)
    if not db_technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Técnico no encontrado"
        )

    if (technician_in.employee_id is not None
        and technician_in.employee_id != db_technician.employee_id 
    ):
        db_employee = crud_employee.get_by_id(db, id=technician_in.employee_id)
        if not db_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El empleado especificado no existe"
            )

        existing_tech = crud_technician.get_other_id(db, id=technician_in.employee_id, field="employee_id")
        if existing_tech and existing_tech.id != technician_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este empleado ya tiene registro como técnico"
            )
        
    return crud_technician.update(db, db_obj=db_technician, obj_in=technician_in)

@router.delete("/{technician_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_technician(technician_id: int, db: Session = Depends(get_db)):
    """Soft delete / Deactivate a technician."""
    deleted_tech = crud_technician.delete(db, technician_id)
    if not deleted_tech:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Técnico no encontrado",
        )
    return {"message": f"Técnico #{technician_id} desactivado correctamente"}