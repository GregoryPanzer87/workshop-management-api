from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import (
    User, UserCreate, UserResponse, UserUpdate, 
    crud_user, crud_client, crud_employee, get_db
)
from app.utils import (
    build_audit_change_details, 
    validate_exists_by_create,
    validate_unique_fields_by_create,
)
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api.deps import require_roles, get_current_user
from app.services import log_action
from app.core import LEVEL_BASIC, LEVEL_ADVANCE

router = APIRouter(prefix="/auth", tags=["Autenticación"])

NOT_FOUND_USER = ["Usuario no encontrado."]
INTEGRITY_ERROR = ["Ocurrió un conflicto al procesar la solicitud de usuario. Verifique los datos ingresados."]


@router.post("/login")
def login(
    db: Session = Depends(get_db), 
    user_in: OAuth2PasswordRequestForm = Depends()
):
    """Authenticates a user and returns a JWT token."""
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


@router.post(
    "/", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED, 
    dependencies=[Depends(require_roles(LEVEL_ADVANCE))]
)
def create_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
):
    """Creates a new user in the database."""
    create_data = user_in.model_dump(exclude_unset=True)

    existence_checks = [
        (crud_client, "client_id", "El cliente especificado no existe"),
        (crud_employee, "employee_id", "El empleado especificado no existe"),
    ]

    errors404 = validate_exists_by_create(db, create_data, existence_checks)
    if errors404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=errors404
        )

    unique_fields = [
        ("username", "El nombre de usuario ya está en uso"),
        ("mail", "El correo electrónico ya está en uso"),
        ("client_id", "Este cliente ya tiene un usuario"),
        ("employee_id", "Este empleado ya tiene un usuario"),
    ]

    errors_409 = validate_unique_fields_by_create(
        db, 
        crud_repo=crud_user, 
        create_data=create_data, 
        unique_fields=unique_fields
    )

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=errors_409
        )

    try:
        db_user = crud_user.create(db, obj_in=create_data)

        log_action(
            db,
            user_id=current_user.id,
            action="CREATE",
            entity="users",
            entity_id=db_user.id,
            details=f"Usuario registrado: {db_user.username} (ID: {db_user.id})",
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Ocurrió un conflicto al registrar el usuario. Verifique los datos ingresados."]
        )
    except Exception:
        db.rollback()
        raise

    return crud_user.get_by_id(db, db_user.id)


@router.patch(
    "/{user_id}", 
    response_model=UserResponse, 
    dependencies=[Depends(require_roles(LEVEL_BASIC))]
)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Updates a user profile with role and ownership checks."""
    db_user = crud_user.get_by_id(db, id=user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_USER,
        )

    is_self = (current_user.id == user_id)
    is_admin = (current_user.role in LEVEL_ADVANCE)
    is_employee = (db_user.employee_id is not None)

    if not is_self:
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=["No puedes modificar un usuario diferente al tuyo."],
            )

        if not is_employee:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=["No puedes modificar un usuario de tipo cliente."],
            )

    update_data = user_in.model_dump(exclude_unset=True)

    if not is_admin:
        update_data.pop("role", None)
        update_data.pop("is_active", None)
        update_data.pop("employee_id", None)
        update_data.pop("client_id", None)

    if not update_data:
        return db_user

    new_client_id = update_data.get("client_id")
    if new_client_id and new_client_id != db_user.client_id:
        if not crud_client.get_by_id(db, id=new_client_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=[f"No existe un cliente con la ID {new_client_id}."],
            )

    new_employee_id = update_data.get("employee_id")
    if new_employee_id and new_employee_id != db_user.employee_id:
        if not crud_employee.get_by_id(db, id=new_employee_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=[f"No existe un empleado con la ID {new_employee_id}."],
            )

    plain_password = update_data.get("password")
    if isinstance(plain_password, str) and plain_password.strip():
        update_data["password"] = get_password_hash(plain_password)
    else:
        update_data.pop("password", None)

    errors_409 = []
    new_username = update_data.get("username")
    if new_username and new_username != db_user.username:
        if crud_user.get_by_other(db, value=new_username, field="username"):
            errors_409.append("Ya existe un usuario registrado con ese nombre de usuario.")

    new_mail = update_data.get("mail")
    if new_mail and new_mail != db_user.mail:
        if crud_user.get_by_other(db, value=new_mail, field="mail"):
            errors_409.append("Ya existe un usuario registrado con ese correo electrónico.")

    if errors_409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=errors_409,
        )

    audit_details = build_audit_change_details(
        db_obj=db_user,
        update_data=update_data,
        entity_name="Usuario",
    )

    try:
        db_user = crud_user.update(db, db_obj=db_user, obj_in=update_data)

        if audit_details:
            log_action(
                db,
                user_id=current_user.id,
                action="UPDATE",
                entity="users",
                entity_id=user_id,
                details=audit_details
            )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=INTEGRITY_ERROR
        )
    except Exception:
        db.rollback()
        raise

    return crud_user.get_by_id(db, user_id)


@router.delete("/{user_id}", dependencies=[Depends(require_roles(LEVEL_ADVANCE))])
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Soft delete / Deactivate an user."""
    db_user = crud_user.get_by_id(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=NOT_FOUND_USER,
        )

    try:
        crud_user.deactivate(db, db_user)

        log_action(
            db,
            user_id=current_user.id,
            action="DELETE",
            entity="users",
            entity_id=user_id,
            details=f"Usuario desactivado: {db_user.username} (ID: {user_id})",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=["Error al eliminar el usuario, es posible que ya esté eliminado."]
        )
    except Exception:
        db.rollback()
        raise

    return {"message": f"Usuario '{db_user.username}' (ID: {user_id}) desactivado correctamente"}