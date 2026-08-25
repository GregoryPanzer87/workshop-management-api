from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_current_user, require_roles
from app import Client, ClientCreate, ClientResponse, ClientUpdate, User, crud_client, get_db
from app.utils import (
    validate_unique_fields_by_create,
    validate_unique_fields_by_update, 
    build_audit_change_details,
)
from app.services import log_action
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_client(client_in: ClientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new client in the database."""
    create_data = client_in.model_dump(exclude_unset=True)

    unique_fields = [
        ("national_id", "La Cédula/RIF ya está vinculado a otro cliente"),
        ("phone_number", "El número de teléfono ya está vinculado a otro cliente"),
        ("email", "El correo electrónico ya está vinculado a otro cliente"),
    ]

    errors_409 = validate_unique_fields_by_create(
        db, 
        crud_repo=crud_client, 
        create_data=create_data, 
        unique_fields=unique_fields
    )

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    try:
        db_client = crud_client.create(db, obj_in=create_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el cliente. Verifique los datos ingresados."]
        )
    
    log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        entity="clients",
        entity_id=db_client.id,
        details=f"Cliente registrado: {db_client.name} (ID: {db_client.id})",
    )
        
    return db_client

@router.get("/", response_model=List[ClientResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_clients(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of customers or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_client.search_ilike(
            db=db, 
            query=q, 
            search_fields=[Client.name, cast(Client.national_id, String), Client.phone_number, Client.short_address], 
            limit=limit
        )
    return crud_client.get_multi(db, skip=skip, limit=limit)

@router.get("/{client_id}", response_model=ClientResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_client_by_id(client_id: int, db: Session = Depends(get_db)):
    """Retrieves a single client by ID."""
    db_client = crud_client.get_by_id(db, client_id)
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Cliente no encontrado"]
        )
    return db_client

@router.patch("/{client_id}", response_model=ClientResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_client(client_id: int, client_in: ClientUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update a client partially or completely."""
    db_client = crud_client.get_by_id(db, id=client_id)
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Cliente no encontrado"]
        )

    update_data = client_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_client

    unique_fields = [
        ("national_id", "La Cédula/RIF ya está vinculado a otro cliente"),
        ("phone_number", "El número de teléfono ya está vinculado a otro cliente"),
        ("email", "El correo electrónico ya está vinculado a otro cliente"),
    ]

    errors = validate_unique_fields_by_update(
        db, 
        crud_repo=crud_client, 
        db_obj=db_client, 
        update_data=update_data, 
        unique_fields=unique_fields
    )

    if errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors
        )

    audit_details = build_audit_change_details(
        db_obj=db_client,
        update_data=update_data,
        entity_name="Cliente",
    )

    try: 
        db_client = crud_client.update(db, db_obj=db_client, obj_in=update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió uno o varios conflictos al registrar el cliente"]
        )

    if audit_details:
        log_action(
            db,
            user_id=current_user.id,
            action="UPDATE",
            entity="clients",
            entity_id=client_id,
            details=audit_details
        )

    return db_client

@router.delete("/{client_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_client(client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Deletes a client by ID."""
    db_client = crud_client.get_by_id(db, client_id)
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=["Cliente no encontrado"]
        )
        
    try:
        crud_client.delete(db, db_obj=db_client)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el cliente porque tiene equipos u otros registros asociados."]
        )

    log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        entity="clients",
        entity_id=client_id,
        details=f"Cliente eliminado: {db_client.name} (ID: {db_client.id})",
    )
    
    return {"message": f"Cliente '{db_client.name}' eliminado correctamente"}