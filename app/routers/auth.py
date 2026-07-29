from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.models import User
from app.schemas import UserCreate, UserResponse, UserUpdate
from app.crud import crud_user

from app.api.deps import get_db
from app.core.security import verify_password, create_access_token
from app.api.deps import require_roles
from app.core.security import LEVEL_BASIC, LEVEL_MEDIUM, LEVEL_ADVANCE, LEVEL_PROFESSIONAL

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login")
def login(
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El usuario está desactivado"
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Create a new user in the database."""
    db_user = crud_user.get_by_user(db, user=user_in.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con ese nombre de usuario"
        )
    return crud_user.create(db, obj_in=user_in)