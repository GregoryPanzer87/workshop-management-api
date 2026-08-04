from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app import SparePart, SparePartCreate, SparePartResponse, SparePartUpdate, crud_spare_part, get_db
from app.api.deps import require_roles
from app.core import LEVEL_BASIC, LEVEL_MEDIUM

router = APIRouter(prefix="/spare_parts", tags=["Spare Parts"])

@router.post("/", response_model=SparePartResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def create_spare_part(spare_part_in: SparePartCreate, db: Session = Depends(get_db)):
    """Create a new spare part in the database."""
    validation = crud_spare_part.get_by_other(db, value=spare_part_in.name, field="name")
    if validation:
        raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, 
                    detail="No puedes crear un componente con un nombre ya existente"
                )
    return crud_spare_part.create(db, obj_in=spare_part_in)

@router.get("/", response_model=List[SparePartResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_spare_parts(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of spare parts or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_spare_part.search(
            db=db, 
            query=q, 
            search_fields=[cast(SparePart.id, String), SparePart.name, SparePart.brand, SparePart.component_type], 
            limit=limit
        )
    return crud_spare_part.get_multi(db, skip=skip, limit=limit)

@router.get("/{spare_part_id}", response_model=SparePartResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_spare_part_by_id(spare_part_id: int, db: Session = Depends(get_db)):
    """Retrieves a single spare part by its ID."""
    db_spare_part = crud_spare_part.get_by_id(db, id=spare_part_id)
    if not db_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Componente no encontrado"
        )
    return db_spare_part

@router.patch("/{spare_part_id}", response_model=SparePartResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_spare_part(spare_part_id: int, spare_part_in: SparePartUpdate, db: Session = Depends(get_db)):
    """Update a spare part partially or completely."""
    db_spare_part = crud_spare_part.get_by_id(db, id=spare_part_id)
    if not db_spare_part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Componente no encontrado"
        )
    if spare_part_in.name is not None:
        validation = crud_spare_part.get_by_other(db, value=spare_part_in.name, field="name")
        if validation and validation.id != spare_part_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="No puedes cambiar el nombre del componente a uno ya existente"
            )
    return crud_spare_part.update(db, db_obj=db_spare_part, obj_in=spare_part_in)