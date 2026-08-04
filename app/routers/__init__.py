from .auth import router as auth_router
from .clients import router as clients_router
from .devices import router as devices_router
from .repair_order import router as repair_order_router
from .spare_part import router as spare_part_router

__all__ = [
    "auth_router",
    "clients_router",
    "devices_router",
    "repair_order_router",
    "spare_part_router"
]