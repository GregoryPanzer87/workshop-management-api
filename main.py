from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routers import auth, clients, devices

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Sistema de Gestión")

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(devices.router)