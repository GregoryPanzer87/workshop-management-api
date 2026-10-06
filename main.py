from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers.others import *
from app.routers.repairs import *

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Sistema de Gestión")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(audit_log_router)
app.include_router(customers_router)
app.include_router(device_types_router)
app.include_router(device_brands_router)
app.include_router(devices_router)
app.include_router(employee_directory_router)
app.include_router(technicians_router)
app.include_router(repair_order_router)
app.include_router(spare_parts_router)
app.include_router(order_spare_parts_router)
app.include_router(services_router)
app.include_router(order_services_router)
app.include_router(storage_router)
app.include_router(exchange_rates_router)