from .auth import router as auth_router
from .clients import router as clients_router
from .devices import router as devices_router
from .repair_order import router as repair_order_router

__all__ = [
    "auth_router",
    "clients_router",
    "devices_router",
    "repair_order_router",
]