from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_current_user, require_roles
from app import Customer, CustomerCreate, CustomerResponse, CustomerUpdate, User, crud_customer, get_db
from app.utils import (
    validate_unique_fields_by_create,
    validate_unique_fields_by_update, 
    build_audit_change_details,
)
from app.services import log_action
from app.core import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE

router = APIRouter(prefix="/customers", tags=["customers"])

NOT_FOUND_CUSTOMER = ["Cliente no encontrado"]

@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def create_customer(customer_in: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new customer in the database."""
    create_data = customer_in.model_dump(exclude_unset=True)

    unique_fields = [
        ("national_id", "La Cédula/RIF ya está vinculado a otro cliente"),
        ("phone_number", "El número de teléfono ya está vinculado a otro cliente"),
        ("email", "El correo electrónico ya está vinculado a otro cliente"),
    ]

    errors_409 = validate_unique_fields_by_create(
        db, 
        crud_repo=crud_customer, 
        create_data=create_data, 
        unique_fields=unique_fields
    )

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    try:
        db_customer = crud_customer.create(db, obj_in=create_data)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="customers",
            entity_id=db_customer.id,
            details=f"Cliente registrado: {db_customer.name} (ID: {db_customer.id})",
        )

        db.commit()
        db.refresh(db_customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el cliente. Verifique los datos ingresados."]
        )
    except Exception as e:
        db.rollback()
        raise e
        
    return db_customer

@router.get("/", response_model=List[CustomerResponse], dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_customers(
    q: Optional[str] = None, 
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    """Retrieves a paginated list of customers or performs a real-time search by sending 'q'."""
    q = q.strip() if q else None
    if q:
        return crud_customer.search_ilike(
            db=db, 
            query=q, 
            search_fields=[Customer.name, cast(Customer.national_id, String), Customer.phone_number, Customer.short_address], 
            limit=limit
        )
    return crud_customer.get_multi(db, skip=skip, limit=limit)

@router.get("/{customer_id}", response_model=CustomerResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def read_customer_by_id(customer_id: int, db: Session = Depends(get_db)):
    """Retrieves a single customer by ID."""
    db_customer = crud_customer.get_by_id(db, customer_id)
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_CUSTOMER
        )
    return db_customer

@router.patch("/{customer_id}", response_model=CustomerResponse, dependencies=[Depends(require_roles(LEVEL_MEDIUM))])
def update_customer(customer_id: int, customer_in: CustomerUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update a customer partially or completely."""
    db_customer = crud_customer.get_by_id(db, id=customer_id)
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_CUSTOMER
        )

    update_data = customer_in.model_dump(exclude_unset=True)
    if not update_data:
        return db_customer

    unique_fields = [
        ("national_id", "La Cédula/RIF ya está vinculado a otro cliente"),
        ("phone_number", "El número de teléfono ya está vinculado a otro cliente"),
        ("email", "El correo electrónico ya está vinculado a otro cliente"),
    ]

    errors_409 = validate_unique_fields_by_update(
        db, 
        crud_repo=crud_customer, 
        db_obj=db_customer, 
        update_data=update_data, 
        unique_fields=unique_fields
    )

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    audit_details = build_audit_change_details(
        db_obj=db_customer,
        update_data=update_data,
        entity_name="Cliente",
    )

    try: 
        db_customer = crud_customer.update(db, db_obj=db_customer, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="customers",
                entity_id=customer_id,
                details=audit_details
            )

        db.commit()
        db.refresh(db_customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió uno o varios conflictos al registrar el cliente."]
        )
    except Exception as e:
        db.rollback()
        raise e

    return db_customer

@router.delete("/{customer_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_customer(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Deletes a customer by ID."""
    db_customer = crud_customer.get_by_id(db, customer_id)
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=NOT_FOUND_CUSTOMER
        )
        
    try:
        crud_customer.delete(db, db_obj=db_customer)

        log_action(
                db,
                user_id=current_user.id,
                action="DELETE",
                entity="customers",
                entity_id=customer_id,
                details=f"Cliente eliminado: {db_customer.name} (ID: {db_customer.id})",
            )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["No se puede eliminar el cliente porque tiene equipos u otros registros asociados."]
        )
    except Exception as e:
        db.rollback()
        raise e
    
    return {"message": f"Cliente '{db_customer.name}' eliminado correctamente"}