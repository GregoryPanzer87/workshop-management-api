from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app import Client, ClientCreate, ClientResponse, ClientUpdate, crud_client, get_db
from app.api.deps import require_roles
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_client(client_in: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client in the database."""
    errors = []
    if client_in.national_id:
        if crud_client.get_by_other(db, value=client_in.national_id, field="national_id"):
            errors.append("La Cédula/RIF ya está vinculado a otro cliente")
    
    if client_in.phone:
        if crud_client.get_by_other(db, value=client_in.phone, field="phone"):
            errors.append("El número de teléfono ya está vinculado a otro cliente")

    if client_in.mail:
        if crud_client.get_by_other(db, value=client_in.mail, field="mail"):
            errors.append("El correo electrónico ya está vinculado a otro cliente")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors
        )
        
    return crud_client.create(db, obj_in=client_in)

@router.get("/", response_model=List[ClientResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_clients(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of customers or performs a real-time search by sending 'q'."""
    if q and q.strip():
        return crud_client.search_ilike(
            db=db, 
            query=q, 
            search_fields=[Client.name, cast(Client.national_id, String), Client.phone, Client.short_address], 
            limit=limit
        )
    return crud_client.get_multi(db, skip=skip, limit=limit)

@router.patch("/{client_id}", response_model=ClientResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_client(client_id: int, client_in: ClientUpdate, db: Session = Depends(get_db)):
    """Update a client partially or completely."""
    db_client = crud_client.get_by_id(db, id=client_id)
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Cliente no encontrado"
        )

    errors = []
    
    if client_in.national_id:
        val_nat = crud_client.get_by_other(db, value=client_in.national_id, field="national_id")
        if val_nat and val_nat.id != client_id:
            errors.append("La Cédula/RIF ya está vinculado a otro cliente")

    if client_in.phone:
        val_phone = crud_client.get_by_other(db, value=client_in.phone, field="phone")
        if val_phone and val_phone.id != client_id:
            errors.append("El número de teléfono ya está vinculado a otro cliente")

    if client_in.mail:
        val_mail = crud_client.get_by_other(db, value=client_in.mail, field="mail")
        if val_mail and val_mail.id != client_id:
            errors.append("El correo electrónico ya está vinculado a otro cliente")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors
        )
        
    return crud_client.update(db, db_obj=db_client, obj_in=client_in)

@router.delete("/{client_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_client(client_id: int, db: Session = Depends(get_db)):
        db_client = crud_client.get_by_id(db, client_id)
        if not db_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Cliente no encontrado"
                )
        crud_client.delete(db, db_client)
        return {"message": f"Cliente '{db_client.name}' eliminado correctamente"}