import os
import json
from dotenv import load_dotenv
from pydantic import EmailStr, BeforeValidator
from typing import Annotated, Optional

load_dotenv()

raw_permisos = os.getenv("PERMISOS_MAP", "{}")
PERMISOS_MAP = {int(k): v for k, v in json.loads(raw_permisos).items()}

def empty_to_none(v):
    if isinstance(v, str) and not v.strip():
        return None
    return v

EmptyStrToNone = Annotated[Optional[str], BeforeValidator(empty_to_none)]
EmptyEmailToNone = Annotated[Optional[EmailStr], BeforeValidator(empty_to_none)]
EmptyIntToNone = Annotated[Optional[int], BeforeValidator(empty_to_none)]
EmptyFloatToNone = Annotated[Optional[float], BeforeValidator(empty_to_none)]
EmptyBoolToNone = Annotated[Optional[bool], BeforeValidator(empty_to_none)]
EmptyDateToNone = Annotated[Optional[float], BeforeValidator(empty_to_none)]