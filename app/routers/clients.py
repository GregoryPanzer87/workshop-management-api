from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app.database import get_db
from app.crud import crud_client
from app.models import Client
from app.schemas import ClientCreate, ClientResponse, ClientUpdate
from app.api.deps import require_roles
from app.core.security import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE, LEVEL_PROFESSIONAL

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_client(client_in: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client in the database."""
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
        search_result = crud_client.search(
            db=db, 
            query=q, 
            search_fields=[Client.name, cast(Client.national_id, String), Client.phone, Client.short_address], 
            limit=limit
        )
        if not search_result:
            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND, 
                                detail={
                                "message": f"No se encontraron coincidencias para '{q}'",
                                "query": q,
                                "search_fields": ["Nombre", "Telefono", "Cedula/RIF", "Direccion"]
                                }
                            )
        return search_result

    return crud_client.get_multi(db, skip=skip, limit=limit)

@router.patch("/{client_id}", response_model=ClientResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_client(client_id: int, client_in: ClientUpdate, db: Session = Depends(get_db)):
    """Update a client partially or completely."""
    db_client = crud_client.get(db, id=client_id)
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Cliente no encontrado"
        )
    return crud_client.update(db, db_obj=db_client, obj_in=client_in)

@router.delete("/{client_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_client(client_id: int, db: Session = Depends(get_db)):
    try:
        deleted_client = crud_client.delete(db, client_id=client_id)
        if not deleted_client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Cliente no encontrado"
            )
        return {"message": f"Cliente '{deleted_client.name}' eliminado correctamente"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )