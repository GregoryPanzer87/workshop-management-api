import datetime
import random
import string
from sqlalchemy.orm import Session
from app import crud_device_type, crud_employee, crud_user



def generate_device_type_prefix(type_name: str, db: Session):
    """Generate an unique prefix by devices types"""
    words = type_name.replace("-", " ").split()

    if len(words) == 1:
        base_prefix = words[0][:4].upper()
    elif len(words) == 2:
        base_prefix = f"{words[0][0]}{words[1][:2]}".upper()
    else:
        base_prefix = "".join([w[0] for w in words[:4]]).upper()

    prefix = base_prefix
    counter = 1

    while True:
        existing_device = crud_device_type.get_by_other(
            db, value=prefix, field="prefix"
        )

        if existing_device is None:
            break

        if len(words) == 2 and counter < len(words[0]):
            prefix = f"{words[0][: counter + 1]}{words[1][: counter - (counter // 2)]}".upper()
        else:
            prefix = f"{words[0][: counter]}"

        counter += 1

    return prefix

def generate_custom_serial(prefix: str) -> str:
    """Generate an internal serial number for devices"""
    now = datetime.datetime.now()
    y = now.strftime("%y")
    m = now.strftime("%m")
    d = now.strftime("%d")

    charset = string.ascii_uppercase + string.digits

    r1 = random.choice(charset)
    r2 = "".join(random.choices(charset, k=2))
    r3 = "".join(random.choices(charset, k=2))

    return f"{prefix}{y}{r1}{m}-{r2}{d}{r3}"

def generate_employee_code(occupation: str, db: Session):
    """Generate an unique prefix by devices types"""
    now = datetime.datetime.now()
    y = now.strftime("%y")

    parts = [p.strip().upper() for p in occupation.replace("-", " ").split() if p.strip()]

    if len(parts) >= 2:
        occ_prefix = f"{parts[0][:3]}-{parts[-1][:3]}"
    elif parts:
        occ_prefix = f"{parts[0][:4]}"
    else:
        occ_prefix = "EMP"

    counter = 1 

    while True:
        code = f"{occ_prefix}-{y}-{counter:04d}"
        existing = crud_employee.get_by_other(db, value=code, field="employee_code")
        if existing is None:
            return code
        counter += 1

def generate_user_credentials(full_name: str, occupation: str, db: Session) -> dict:
    """Genera credenciales iniciales para el usuario basándose en su nombre y ocupación."""
    now = datetime.datetime.now()
    y = now.strftime("%y")
    m = now.strftime("%m")

    names = [n.strip().lower() for n in full_name.replace("-", " ").split() if n.strip()]
    occ_parts = [o.strip().lower() for o in occupation.replace("-", " ").split() if o.strip()]

    first_name = names[0] if names else "emp"
    last_name = names[-1] if len(names) > 1 else "user"
    occ_prefix = occ_parts[0][:4] if occ_parts else "staff"

    base_username = f"{occ_prefix}_{first_name[:4]}{last_name[:1]}.{m}"
    username = base_username
    counter = 1

    while crud_user.get_by_other(db, value=username, field="username"):
        username = f"{base_username}{counter}"
        counter += 1

    password = f"{first_name[:4].capitalize()}{last_name[:2].capitalize()}{y}{m}!"

    return {
        "username": username,
        "password": password
    }
