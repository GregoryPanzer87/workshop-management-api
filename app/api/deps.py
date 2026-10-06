from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt
from pydantic import ValidationError

from app.core.security import SECRET_KEY, ALGORITHM
from app import User, UserRole, Technician, crud_user, crud_technician, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id_int = int(user_id)
    except (jwt.PyJWTError, ValidationError, ValueError):
        raise credentials_exception

    user = crud_user.get_by_id(db, id=user_id_int)
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Usuario inactivo"
        )

    return user
    
def require_roles(allowed_roles: List[UserRole]):
    """Permite el acceso si el rol del usuario está incluido en 'allowed_roles'."""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción."
            )
        return current_user

    return role_checker

def get_current_technician(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Technician:
    """
    Obtiene e identifica la entidad 'Technician' asociada al usuario autenticado.
    
    Casos soportados:
    1. Técnico contratista/externo (asociado directamente por user.technician_id)
    2. Empleado o Jefe/Admin que opera como técnico (asociado vía user.employee_id -> technician.employee_id)
    """
    # Caso 1: Contratista / Técnico sin ficha de empleado (FK directa)
    if current_user.technician_id:
        tech = crud_technician.get_by_id(db, id=current_user.technician_id)
        if tech and tech.is_active:
            return tech

    # Caso 2: Empleado o Admin registrado también como Técnico
    if current_user.employee_id:
        tech = crud_technician.get_by_other(db, value=current_user.employee_id, field="employee_id")
        if tech and tech.is_active:
            return tech

    # Caso 3: No tiene perfil activo en la tabla 'technicians'
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=["El usuario autenticado no tiene un perfil de técnico activo asignado."]
    )