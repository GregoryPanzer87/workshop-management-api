from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, List, Self
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
        str_strip_whitespace=True
    )
    
# =========================================================================
#---------------------------------CUSTOMER---------------------------------
# =========================================================================

class CustomerBase(BaseModel):
    national_id: EmptyStrToNone = None
    name: str
    phone_number: EmptyStrToNone = None
    email: EmptyEmailToNone = None
    short_address: EmptyStrToNone = None

class CustomerCreate(ConfigCreate, CustomerBase):
    pass

class CustomerResponse(ConfigResponse, CustomerBase):
    id: int

class CustomerMinResponse(ConfigResponse, BaseModel):
    id: int
    name: str

class OrderCustomerResponse(CustomerMinResponse):
    national_id: EmptyStrToNone = None
    phone_number: EmptyStrToNone = None

class CustomerUpdate(BaseModel):
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
    prefix: EmptyStrToNone = None

class DeviceTypeCreate(ConfigCreate, DeviceTypeBase):
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

class DeviceBrandCreate(ConfigCreate, DeviceBrandBase):
    pass

class DeviceBrandResponse(ConfigResponse, DeviceBrandBase):
    id: int

class DeviceBrandUpdate(BaseModel):
    name: EmptyStrToNone = None

# =========================================================================
#---------------------------------DEVICES---------------------------------
# =========================================================================

class DeviceBase(BaseModel):
    customer_id: int
    model: str
    serial_number: EmptyStrToNone = None
    description: EmptyStrToNone = None

    device_type_id: int
    device_brand_id: int

class DeviceCreate(ConfigCreate, DeviceBase):
    pass

class DeviceBaseResponse(ConfigResponse, DeviceBase):
    id: int

class DeviceResponse(DeviceBaseResponse):
    customer: CustomerMinResponse
    device_type: DeviceTypeResponse
    device_brand: DeviceBrandResponse

class DeviceMinResponse(DeviceBaseResponse):
    device_type: DeviceTypeResponse
    device_brand: DeviceBrandResponse

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
    commission: EmptyFloatToNone = None
    is_active: bool = True

    employee_id: EmptyIntToNone = None

class TechnicianCreate(ConfigCreate, TechnicianBase):
    pass

class TechnicianResponse(ConfigResponse, TechnicianBase):
    id: int

class TechnicianMinResponse(ConfigResponse, BaseModel):
    id: int
    name: str

class TechnicianUpdate(BaseModel):
    commission: EmptyFloatToNone = None

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
    entry_date: date = Field(default_factory=date.today)
    legacy_order_number: EmptyStrToNone = None
    is_warranty: bool
    status: Optional[StatusOrder] = StatusOrder.PENDING
    agreed_price: EmptyFloatToNone = None
    exit_date: EmptyDateToNone = None

    customer_id: int
    device_id: int
    technician_id: int

    @model_validator(mode='after')
    def check_dates(self) -> Self:
        if self.exit_date is not None and self.exit_date < self.entry_date:
            raise ValueError('La fecha de salida no puede ser anterior a la fecha de entrada.')
        return self

class RepairOrderCreate(ConfigCreate, RepairOrderBase):
    order_number: EmptyStrToNone = None

class RepairOrderBatchCreate(BaseModel):
    orders: List[RepairOrderCreate]

class RepairOrderResponse(ConfigResponse,RepairOrderBase):
    id: int
    order_number: EmptyStrToNone = None
    customer: Optional[OrderCustomerResponse] = None
    device: Optional[DeviceMinResponse] = None
    technician: Optional[TechnicianMinResponse] = None

class RepairOrderDetailResponse(RepairOrderResponse):
    customer: CustomerResponse
    device: DeviceResponse
    technician: TechnicianResponse

class RepairOrderUpdate(BaseModel):
    legacy_order_number: EmptyStrToNone = None
    entry_date: EmptyDateToNone = None
    is_warranty: EmptyBoolToNone = None
    agreed_price: EmptyFloatToNone = None
    exit_date: EmptyDateToNone = None

    customer_id: EmptyIntToNone = None
    device_id: EmptyIntToNone = None
    technician_id: EmptyIntToNone = None

class RepairOrderUpdateStatus(BaseModel):
    status: StatusOrder

# =========================================================================
#---------------------------------SPARE PARTS------------------------------
# =========================================================================

class SparePartBase(BaseModel):
    name: str
    component_type: str
    brand: EmptyStrToNone = None
    supplier: EmptyStrToNone = None
    stock: EmptyIntToNone = None
    price: EmptyFloatToNone = None

class SparePartCreate(ConfigCreate, SparePartBase):
    pass

class SparePartResponse(ConfigResponse, SparePartBase):
    id: int

class SparePartOrderResponse(ConfigResponse, BaseModel):
    id: int
    name: str
    component_type: str

class SparePartUpdate(BaseModel):
    name: EmptyStrToNone = None
    component_type: EmptyStrToNone = None
    brand: EmptyStrToNone = None
    supplier: EmptyStrToNone = None
    stock: EmptyIntToNone = None
    price: EmptyFloatToNone = None

# =========================================================================
#---------------------------------ORDER SPARE PARTS------------------------
# =========================================================================

class OrderSparePartBase(BaseModel):
    quantity: int

    repair_order_id: int
    spare_part_id: int

class OrderSparePartCreate(ConfigCreate, OrderSparePartBase):
    pass

class OrderSparePartResponse(ConfigResponse, OrderSparePartBase):
    id: int
    spare_part: SparePartBase

class OrderSparePartUpdate(BaseModel):
    quantity: EmptyIntToNone = None
    spare_part_id: EmptyIntToNone = None

# =========================================================================
#---------------------------------SERVICE----------------------------
# =========================================================================

class ServiceBase(BaseModel):
    name: str
    price: EmptyFloatToNone = None

class ServiceCreate(ConfigCreate, ServiceBase):
    pass

class ServiceResponse(ConfigResponse, ServiceBase):
    id: int

class ServiceUpdate(BaseModel):
    name: EmptyStrToNone = None
    price: EmptyFloatToNone = None

# =========================================================================
#---------------------------------ORDER SERVICES----------------------------
# =========================================================================

class OrderServiceBase(BaseModel):
    repair_order_id: int
    service_id: int

class OrderServiceCreate(ConfigCreate, OrderServiceBase):
    pass

class OrderServiceResponse(ConfigResponse, OrderServiceBase):
    id: int
    services: ServiceResponse

class OrderServiceUpdate(BaseModel):
    service_id: EmptyIntToNone = None

# =========================================================================
#----------------------------------STORAGE---------------------------------
# =========================================================================

class StorageBase(BaseModel):
    entry_date: date
    column: str

    device_id: int

class StorageCreate(ConfigCreate, StorageBase):
    pass

class StorageResponse(ConfigResponse, StorageBase):
    id: int
    device: DeviceBaseResponse

class StorageUpdate(BaseModel):
    entry_date: EmptyDateToNone = None
    column: EmptyStrToNone = None

    device_id: EmptyIntToNone = None