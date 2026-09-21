from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session
import secrets
import string

from app import crud_device_type, crud_device, crud_employee, crud_user, crud_repair_order


def generate_device_type_prefix(type_name: str, db: Session) -> str:
    """Genera un prefijo único de máximo 5 caracteres para tipos de dispositivo."""
    words = type_name.replace("-", " ").split()
    if not words:
        words = ["DEV"]

    if len(words) == 1:
        base = words[0][:4].upper()
    elif len(words) == 2:
        base = f"{words[0][:2]}{words[1][:2]}".upper()
    else:
        base = "".join([w[0] for w in words[:4]]).upper()

    prefix = base
    counter = 1

    while counter < 9999:
        existing = crud_device_type.get_by_other(db, value=prefix, field="prefix")
        if existing is None:
            return prefix

        suffix = str(counter)
        prefix = f"{base[:5 - len(suffix)]}{suffix}"
        counter += 1
    
    raise ValueError("No se pudo generar un prefijo único.")


def generate_custom_serial(db: Session, prefix: str = "INN") -> str:
    """Generate a sequential internal serial number (e.g., SND-00042)"""
    count = crud_device.count_by_prefix(db, prefix=prefix) + 1
    return f"{prefix}-{count:05d}"


def generate_custom_serial_batch(
    db: Session, count: int, prefix: str = "INN"
) -> List[str]:
    """Generate sequential internal serial numbers"""
    base_count = crud_device.count_by_prefix(db, prefix=prefix)
    generated_serial_numbers = []
    for i in range(1, count + 1):
        serial_number = f"{prefix}-{(base_count + i):05d}"
        generated_serial_numbers.append(serial_number)

    return generated_serial_numbers


def generate_order_number(db: Session, target_date: Optional[date] = None) -> str:
    """Generate a sequential order number (e.g., 26-00069)"""
    ref_date = target_date or datetime.now().date()
    y = ref_date.strftime("%y")
    last_order_num = crud_repair_order.last_by_order_number(db, year=y)

    if not last_order_num:
        return f"{y}-00001"

    try:
        parts = last_order_num.split("-")
        current_seq = int(parts[1]) if len(parts) > 1 else 0
        next_seq = current_seq + 1
    except (IndexError, ValueError):
        next_seq = 1

    return f"{y}-{next_seq:05d}"

def generate_order_numbers_batch(db: Session, count: int, target_date: Optional[date] = None) -> List[str]:
    """Genera una lista de N números de orden correlativos continuos."""
    ref_date = target_date or date.today()
    y = ref_date.strftime("%y")

    last_order_num = crud_repair_order.last_by_order_number(db, year=y)

    current_seq = 0
    if last_order_num:
        try:
            parts = last_order_num.split("-")
            if len(parts) > 1:
                current_seq = int(parts[1])
        except (IndexError, ValueError):
            current_seq = 0

    generated_numbers = []
    for i in range(1, count + 1):
        next_seq = current_seq + i
        generated_numbers.append(f"{y}-{next_seq:05d}")

    return generated_numbers


def generate_employee_code(occupation: str, db: Session):
    """Generate an unique prefix by devices types"""
    now = datetime.now()
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
    date_str = datetime.now().strftime("%y%m")
    names = [n.strip().lower() for n in full_name.replace("-", " ").split() if n.strip()]
    occ_parts = [o.strip().lower() for o in occupation.replace("-", " ").split() if o.strip()]

    first_name = names[0] if names else "emp"
    last_name = names[-1] if len(names) > 1 else "user"
    occ_prefix = occ_parts[0][:4] if occ_parts else "staff"

    base_username = f"{occ_prefix}_{first_name[:4]}{last_name[:1]}.{date_str[2:]}"
    username = base_username
    counter = 1

    while crud_user.get_by_other(db, value=username, field="username"):
        username = f"{base_username}{counter}"
        counter += 1

    # Generación de contraseña aleatoria segura
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(12))

    return {
        "username": username,
        "password": password
    }
