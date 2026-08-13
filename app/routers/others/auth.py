from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app import (
    User, UserCreate, UserResponse, UserUpdate, 
    crud_user, crud_client, crud_employee, get_db
)
from app.core.security import verify_password, create_access_token, get_password_hash
from app.api.deps import require_roles
from app.core.security import LEVEL_BASIC, LEVEL_ADVANCE

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login")
def login(
    db: Session = Depends(get_db), 
    user_in: OAuth2PasswordRequestForm = Depends()
):
    user = crud_user.get_by_other(db, value=user_in.username, field="username")
    
    if not user or not verify_password(user_in.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El usuario está desactivado."
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Create a new user in the database."""
    errors1 = []
    errors2 = []

    if user_in.client_id:
        db_client = crud_client.get_by_id(db, user_in.client_id)
        if not db_client:
            errors1.append(f"No existe un cliente con esta ID {user_in.client_id}.")
    
    if user_in.employee_id:
        db_employee = crud_employee.get_by_id(db, user_in.employee_id)
        if not db_employee:
            errors1.append(f"No existe un empleado con esta ID {user_in.employee_id}.")

    if errors1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors1,
        )
    
    existing_username = crud_user.get_by_other(db, value=user_in.username, field="username")
    if existing_username:
        errors2.append("Ya existe un usuario registrado con ese nombre de usuario.")

    existing_mail = crud_user.get_by_other(db, value=user_in.mail, field="mail")
    if existing_mail:
        errors2.append("Ya existe un usuario registrado con ese correo electrónico.")

    if errors2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors2,
        )
    
    user_in.password = get_password_hash(user_in.password) 
    
    return crud_user.create(db, obj_in=user_in)

@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_roles(LEVEL_BASIC))])
def update_user(user_id: int,user_in: UserUpdate,db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Updates a user profile with role and ownership checks."""
    db_user = crud_user.get_by_id(db, user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario No encontrado.",
        )

    errors1 = []
    errors2 = []
    is_self = (current_user.id == user_id)
    is_admin = (current_user.role >= LEVEL_ADVANCE)
    is_employee = (db_user.employee_id is not None)

    if not is_self:
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes modificar un usuario diferente al tuyo.",
            )

        if not is_employee:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes modificar un usuario de tipo cliente.",
            )

    if not is_admin:
        user_in.role = db_user.role
        user_in.is_active = db_user.is_active
        user_in.employee_id = db_user.employee_id
        user_in.client_id = db_user.client_id

    if user_in.password:
        user_in.password = get_password_hash(user_in.password)    
        
    if user_in.client_id and user_in.client_id != db_user.client_id:
        db_client = crud_client.get_by_id(db, user_in.client_id)
        if not db_client:
            errors1.append(f"No existe un cliente con esta ID {user_in.client_id}.")

    # Validar employee_id solo si cambió respecto al valor original en BD
    if user_in.employee_id and user_in.employee_id != db_user.employee_id:
        db_employee = crud_employee.get_by_id(db, user_in.employee_id)
        if not db_employee:
            errors1.append(f"No existe un empleado con esta ID {user_in.employee_id}.")
        
    if errors1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors1,
        )

    if user_in.username and user_in.username != db_user.username:
        existing_user = crud_user.get_by_other(db, value=user_in.username, field="username")
        if existing_user:
            errors2.append("Ya existe un usuario registrado con ese nombre de usuario.")
    
    if user_in.mail and user_in.mail != db_user.mail:
        existing_user = crud_user.get_by_other(db, value=user_in.mail, field="mail")
        if existing_user:
            errors2.append("Ya existe un usuario registrado con ese correo electrónico.")

    if errors2:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=errors2,
        )

    return crud_user.update(db, db_user, user_in)