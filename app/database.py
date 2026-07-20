import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase  # Importamos DeclarativeBase

# Cargamos las variables del archivo .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Construimos la URL de conexión para MariaDB/MySQL usando pymysql
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# El "Engine" se encarga de gestionar las conexiones físicas a la BD
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True  # Verifica si la conexión sigue viva antes de usarla
)

# "SessionLocal" nos dará una sesión de base de datos cada vez que la API la necesite
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# La forma moderna de declarar la clase base en SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass

# Función auxiliar para obtener la sesión de BD (Dependency Injection en FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()