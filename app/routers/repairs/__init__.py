from .clients import router as clients_router
from .devices import router as devices_router
from .repair_order import router as repair_order_router
from .device_types import router as device_types_router
from .device_brands import router as device_brands_router
from .spare_parts import router as spare_parts_router
from .service_types import router as service_types_router
from .order_spare_parts import router as order_spare_parts_router
from .order_services import router as order_services_router
from .technicians import router as technicians_router
from .storage import router as storage_router

__all__ = [
    "clients_router",
    "devices_router",
    "repair_order_router",
    "device_types_router",
    "device_brands_router",
    "technicians_router",
    "spare_parts_router",
    "order_spare_parts_router",
    "service_types_router",
    "order_services_router",
    "storage_router"
]