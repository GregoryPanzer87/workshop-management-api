from fastapi import FastAPI
from app.database import engine, Base
from app.routers import *

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Sistema de Gestión")

app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(devices_router)
app.include_router(repair_order_router)
app.include_router(spare_part_router)