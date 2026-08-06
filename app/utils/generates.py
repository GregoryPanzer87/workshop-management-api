import datetime
import random
import string
from sqlalchemy.orm import Session
from app import crud_device_type

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