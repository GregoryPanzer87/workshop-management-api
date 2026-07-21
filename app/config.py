import os
import json
from dotenv import load_dotenv

load_dotenv()

raw_permisos = os.getenv("PERMISOS_MAP", "{}")
PERMISOS_MAP = {int(k): v for k, v in json.loads(raw_permisos).items()}