from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date
from enum import Enum
from app.config import EmptyEmailToNone, EmptyStrToNone, EmptyFloatToNone, EmptyIntToNone, EmptyBoolToNone, EmptyDateToNone

class ConfigCreate():
    model_config = ConfigDict(
        str_strip_whitespace=True
    )

class ConfigResponse():
    model_config = ConfigDict(
        from_attributes=True,
    )
    
# =========================================================================
#---------------------------------CLIENTS----------------------------------
# =========================================================================

class ClientBase(BaseModel):
    national_id: EmptyStrToNone = None
    name: str
    phone_number: EmptyStrToNone = None
    email: EmptyEmailToNone = None
    short_address: EmptyStrToNone = None

class ClientCreate(ClientBase, ConfigCreate):
    pass

class ClientResponse(ConfigResponse, ClientBase):
    id: int

class ClientMinResponse(ConfigResponse, BaseModel):
    id: int
    name: str

class OrderClientResponse(ConfigResponse, ClientMinResponse):
    national_id: EmptyStrToNone = None
    phone_number: EmptyStrToNone = None

class ClientUpdate(BaseModel):
    national_id: EmptyStrToNone = None
    name: EmptyStrToNone = None
    phone_number: EmptyStrToNone = None
    email: EmptyEmailToNone = None
    short_address: EmptyStrToNone = None

# =========================================================================
#------------------------------DEVICES TYPES-------------------------------
# =========================================================================

class DeviceTypeBase(BaseModel):
    name: str
    prefix: str

class DeviceTypeCreate(DeviceTypeBase, ConfigCreate):
    pass

class DeviceTypeResponse(ConfigResponse, DeviceTypeBase):
    id: int

class DeviceTypeUpdate(BaseModel):
    name: EmptyStrToNone = None
    prefix: EmptyStrToNone = None


# =========================================================================
#------------------------------DEVICES BRAND-------------------------------
# =========================================================================

class DeviceBrandBase(BaseModel):
    name: str

class DeviceBrandCreate(DeviceBrandBase, ConfigCreate):
    pass

class DeviceBrandResponse(ConfigResponse, DeviceBrandBase):
    id: int

class DeviceBrandUpdate(BaseModel):
    name: EmptyStrToNone = None

# =========================================================================
#---------------------------------DEVICES---------------------------------
# =========================================================================

class DeviceBase(BaseModel):
    client_id: int
    model: str
    serial_number: EmptyStrToNone = None
    description: EmptyStrToNone = None

    device_type_id: int
    device_brand_id: int

class DeviceCreate(DeviceBase, ConfigCreate):
    pass

class DeviceBaseResponse(ConfigResponse, DeviceBase):
    id: int
    model: str
    serial_number: EmptyStrToNone = None
    description: EmptyStrToNone = None

class DeviceResponse(ConfigResponse, DeviceBase):
    client_id: ClientMinResponse
    device_type_id: DeviceTypeResponse
    device_brand_id: DeviceBrandResponse

class DeviceMinResponse(ConfigResponse, DeviceBaseResponse):
    device_type_id: DeviceTypeResponse
    device_brand_id: DeviceBrandResponse

class DeviceUpdate(BaseModel):
    model: EmptyStrToNone = None
    serial_number: EmptyStrToNone = None
    description: EmptyStrToNone = None
    device_type_id: EmptyIntToNone = None
    device_brand_id: EmptyIntToNone = None

# =========================================================================
#---------------------------------TECHNICIAN-------------------------------
# =========================================================================

class TechnicianBase(BaseModel):
    name: EmptyStrToNone = None
    commission: EmptyIntToNone = None
    is_active: bool = True

    employee_id: EmptyIntToNone = None

class TechnicianCreate(TechnicianBase, ConfigCreate):
    pass

class TechnicianResponse(ConfigResponse, TechnicianBase):
    id: int

class TechnicianMinResponse(ConfigResponse, BaseModel):
    id: int
    name: str

class TechnicianUpdate(BaseModel):
    commission: EmptyIntToNone = None
    is_active: EmptyBoolToNone = None

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

class RepairOrderCreate(RepairOrderBase, ConfigCreate):
    pass

class RepairOrderResponse(ConfigResponse, RepairOrderBase):
    id: int
    client_id: Optional[OrderClientResponse] = None
    device_id: Optional[DeviceMinResponse] = None
    technician_id: Optional[TechnicianMinResponse] = None

class RepairOrderDetailResponse(ConfigResponse, RepairOrderResponse):
    client_id: ClientResponse
    device_id: DeviceResponse
    technician_id: TechnicianResponse

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
    brand: EmptyStrToNone = None
    stock: EmptyIntToNone = 0
    price: EmptyFloatToNone = None

class SparePartCreate(SparePartBase, ConfigCreate):
    pass

class SparePartResponse(ConfigResponse, SparePartBase):
    id: int

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

class OrderSparePartCreate(OrderSparePartBase, ConfigCreate):
    pass

class OrderSparePartResponse(ConfigResponse, OrderSparePartBase):
    id: int

class OrderSparePartUpdate(BaseModel):
    quantity: EmptyIntToNone = None
    spare_part_id: EmptyIntToNone = None

# =========================================================================
#---------------------------------SERVICE TYPES----------------------------
# =========================================================================

class ServiceTypeBase(BaseModel):
    name: str
    price: EmptyFloatToNone = None

class ServiceTypeCreate(ServiceTypeBase, ConfigCreate):
    pass

class ServiceTypeResponse(ConfigResponse, ServiceTypeBase):
    id: int

class ServiceTypeUpdate(BaseModel):
    name: EmptyStrToNone = None
    price: EmptyFloatToNone = None

# =========================================================================
#---------------------------------ORDER SERVICES----------------------------
# =========================================================================

class OrderServiceBase(BaseModel):
    repair_order_id: int
    service_type_id: int

class OrderServiceCreate(OrderServiceBase, ConfigCreate):
    pass

class OrderServiceResponse(ConfigResponse, OrderServiceBase):
    id: int

class OrderServiceUpdate(BaseModel):
    service_type_id: EmptyIntToNone = None

# =========================================================================
#----------------------------------STORAGE---------------------------------
# =========================================================================

class StorageBase(BaseModel):
    entry_date: date
    column: str

    device_id: int

class StorageCreate(StorageBase, ConfigCreate):
    pass

class StorageResponse(ConfigResponse, StorageBase):
    id: int

class StorageUpdate(BaseModel):
    entry_date: EmptyDateToNone = None
    column: EmptyStrToNone = None

    device_id: EmptyIntToNone = None