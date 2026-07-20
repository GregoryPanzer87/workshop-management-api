from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from enum import Enum


# =========================================================================
#---------------------------------CLIENTS----------------------------------
# =========================================================================

class ClientBase(BaseModel):
    national_id_type: str
    national_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    mail: Optional[EmailStr] = None
    short_address: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: int

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------DEVICES---------------------------------
# =========================================================================

class DeviceBase(BaseModel):
    client_id: int
    device_type: str
    brand: str
    model: str
    serial_number: str

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: int

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------EMPLOYEE DIRECTORY-----------------------
# =========================================================================

class EmployeeDirectoryBase(BaseModel):
    full_name: str
    national_id: str
    tax_id: str
    short_address: str
    occupation: str
    employee_code: str
    entry_date: date
    tax_id_doc: Optional[str] = None
    national_id_doc: Optional[str] = None
    profile_photo: Optional[str] = None

class EmployeeDirectoryCreate(EmployeeDirectoryBase):
    pass

class EmployeeDirectoryResponse(EmployeeDirectoryBase):
    id: int

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------TECHNICALS-------------------------------
# =========================================================================

class TechnicalBase(BaseModel):
    commission: Optional[int] = None

    employee_id: int

class TechnicalCreate(TechnicalBase):
    pass

class TechnicalResponse(TechnicalBase):
    id: int

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------REPAIRS ORDERS---------------------------
# =========================================================================

class StatusOrderEnum(str, Enum):
    PENDING = "Pendiente"
    IN_PROGRESS = "En proceso"
    READY = "Listo"
    DELIVERED = "Entregado"

class RepairOrderBase(BaseModel):
    entry_date: date
    status: Optional[StatusOrderEnum] = StatusOrderEnum.PENDING
    agreed_price: Optional[int] = None
    exit_date: Optional[date] = None

    client_id: int
    device_id: int
    technical_id: int

class RepairOrderCreate(RepairOrderBase):
    pass

class RepairOrderResponse(RepairOrderBase):
    id: int

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------SPARE PARTS------------------------------
# =========================================================================

class SparePartBase(BaseModel):
    name: str
    stock: Optional[int] = 0
    price: Optional[int] = None

class SparePartCreate(SparePartBase):
    pass

class SparePartResponse(SparePartBase):
    id: int

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------OORDER SPARE PARTS------------------------
# =========================================================================

class OrderSparePartBase(BaseModel):
    quantity: int

    repair_order_id: int
    spare_part_id: int

class OrderSparePartCreate(OrderSparePartBase):
    pass

class OrderSparePartResponse(OrderSparePartBase):
    id: int

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------SERVICE TYPES----------------------------
# =========================================================================

class ServiceTypeBase(BaseModel):
    name: str
    price: Optional[int] = None

class ServiceTypeCreate(ServiceTypeBase):
    pass

class ServiceTypeResponse(ServiceTypeBase):
    id: int

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------EXPENSE----------------------------------
# =========================================================================

class ExpenseBase(BaseModel):
    description: str
    amount: int
    expense_date: date
    category: str

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseResponse(ExpenseBase):
    id: int

    class Config:
        from_attributes = True

# =========================================================================
#---------------------------------ATTENDANCE-------------------------------
# =========================================================================

class StatusAttendanceEnum(str, Enum):
    PRESENT = "Presente"
    ABSENT = "Ausente"
    PERMISSION = "Permiso"
    HEALT = "Salud"

class AttendanceBase(BaseModel):
    date_now: date
    status: Optional[StatusAttendanceEnum] = StatusAttendanceEnum.ABSENT

    employee_id: int

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceResponse(AttendanceBase):
    id: int

    class Config:
        from_attributes = True