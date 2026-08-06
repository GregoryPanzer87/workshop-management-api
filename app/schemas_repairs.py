from pydantic import BaseModel
from typing import Optional
from datetime import date
from enum import Enum
from app.config import EmptyEmailToNone, EmptyStrToNone, EmptyFloatToNone, EmptyIntToNone, EmptyBoolToNone, EmptyDateToNone

# =========================================================================
#---------------------------------CLIENTS----------------------------------
# =========================================================================

class ClientBase(BaseModel):
    national_id: EmptyStrToNone = None
    name: str
    phone: EmptyStrToNone = None
    mail: EmptyEmailToNone = None
    short_address: EmptyStrToNone = None

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class ClientMinResponse(BaseModel):
    id: int
    name: str
    national_id: EmptyStrToNone = None

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class ClientUpdate(BaseModel):
    national_id: EmptyStrToNone = None
    name: EmptyStrToNone = None
    phone: EmptyStrToNone = None
    mail: EmptyEmailToNone = None
    short_address: EmptyStrToNone = None

# =========================================================================
#------------------------------DEVICES TYPES-------------------------------
# =========================================================================

class DeviceTypeBase(BaseModel):
    name: str

class DeviceTypeCreate(DeviceTypeBase):
    pass

class DeviceTypeResponse(DeviceTypeBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class DeviceTypeUpdate(BaseModel):
    name: EmptyStrToNone = None


# =========================================================================
#------------------------------DEVICES BRAND-------------------------------
# =========================================================================

class DeviceBrandBase(BaseModel):
    name: str

class DeviceBrandCreate(DeviceBrandBase):
    pass

class DeviceBrandResponse(DeviceBrandBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class DeviceBrandUpdate(BaseModel):
    name: EmptyStrToNone = None

# =========================================================================
#---------------------------------DEVICES---------------------------------
# =========================================================================

class DeviceBase(BaseModel):
    client_id: int
    model: str
    serial_number: EmptyStrToNone = None
    description: str

    device_type_id: int
    device_brand_id: int

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class DeviceMinResponse(BaseModel):
    id: int
    model: str
    description: EmptyStrToNone = None
    serial_number: EmptyStrToNone = None
    device_type_id: DeviceTypeResponse
    device_brand_id: DeviceBrandResponse

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class DeviceUpdate(BaseModel):
    client_id: EmptyIntToNone = None
    model: EmptyStrToNone = None
    serial_number: EmptyStrToNone = None
    description: EmptyStrToNone = None
    device_type_id: EmptyIntToNone = None
    device_brand_id: EmptyIntToNone = None

# =========================================================================
#---------------------------------TECHNICIAN-------------------------------
# =========================================================================

class TechnicianBase(BaseModel):
    commission: EmptyIntToNone = None

    employee_id: int

class TechnicianCreate(TechnicianBase):
    pass

class TechnicianResponse(TechnicianBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class TechnicianUpdate(BaseModel):
    commission: EmptyIntToNone = None

    employee_id: EmptyIntToNone = None

# =========================================================================
#---------------------------------REPAIRS ORDERS---------------------------
# =========================================================================

class StatusOrder(str, Enum):
    PENDING = "Pendiente"
    IN_PROGRESS = "En proceso"
    READY = "Listo"
    DELIVERED = "Entregado"

class RepairOrderBase(BaseModel):
    entry_date: date
    is_warranty: bool
    status: Optional[StatusOrder] = StatusOrder.PENDING
    agreed_price: EmptyFloatToNone = None
    exit_date: EmptyDateToNone = None

    client_id: int
    device_id: int
    technician_id: int

class RepairOrderCreate(RepairOrderBase):
    pass

class RepairOrderResponse(RepairOrderBase):
    id: int
    client: Optional[ClientMinResponse] = None
    device: Optional[DeviceMinResponse] = None

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class RepairOrderDetailResponse(RepairOrderResponse):
    client: ClientResponse
    device: DeviceResponse

class RepairOrderUpdate(BaseModel):
    entry_date: EmptyDateToNone = None
    is_warranty: EmptyBoolToNone = None
    status: Optional[StatusOrder] = None
    agreed_price: EmptyFloatToNone = None
    exit_date: EmptyDateToNone = None
    legacy_order_id: EmptyIntToNone = None

    client_id: EmptyIntToNone = None
    device_id: EmptyIntToNone = None
    technician_id: EmptyIntToNone = None

# =========================================================================
#---------------------------------SPARE PARTS------------------------------
# =========================================================================

class SparePartBase(BaseModel):
    name: str
    component_type: str
    brand: EmptyStrToNone = "Generico"
    stock: EmptyIntToNone = 0
    price: EmptyFloatToNone = None

class SparePartCreate(SparePartBase):
    pass

class SparePartResponse(SparePartBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class SparePartUpdate(BaseModel):
    name: EmptyStrToNone = None
    stock: EmptyIntToNone = None
    price: EmptyFloatToNone = None

# =========================================================================
#---------------------------------ORDER SPARE PARTS------------------------
# =========================================================================

class OrderSparePartBase(BaseModel):
    quantity: int

    repair_order_id: int
    spare_part_id: int

class OrderSparePartCreate(OrderSparePartBase):
    pass

class OrderSparePartResponse(OrderSparePartBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class OrderSparePartUpdate(BaseModel):
    quantity: EmptyIntToNone = None
    repair_order_id: EmptyIntToNone = None
    spare_part_id: EmptyIntToNone = None

# =========================================================================
#---------------------------------SERVICE TYPES----------------------------
# =========================================================================

class ServiceTypeBase(BaseModel):
    name: str
    price: EmptyFloatToNone = None

class ServiceTypeCreate(ServiceTypeBase):
    pass

class ServiceTypeResponse(ServiceTypeBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class ServiceTypeUpdate(BaseModel):
    name: EmptyStrToNone = None
    price: EmptyFloatToNone = None

# =========================================================================
#---------------------------------ORDER SERVICES----------------------------
# =========================================================================

class OrderServiceBase(BaseModel):
    repair_order_id: int
    service_types_id: int

class OrderServiceCreate(OrderServiceBase):
    pass

class OrderServiceResponse(OrderServiceBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class OrderServiceUpdate(BaseModel):
    repair_order_id: EmptyIntToNone = None
    service_types_id: EmptyIntToNone = None

# =========================================================================
#----------------------------------STORAGE---------------------------------
# =========================================================================

class StorageBase(BaseModel):
    entry_date: date
    column: str

    device_id: int

class StorageCreate(StorageBase):
    pass

class StorageResponse(StorageBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class StorageUpdate(BaseModel):
    entry_date: EmptyDateToNone = None
    column: EmptyStrToNone = None

    device_id: EmptyIntToNone = None