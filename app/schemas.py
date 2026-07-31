from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from enum import Enum


# =========================================================================
#---------------------------------CLIENTS----------------------------------
# =========================================================================

class ClientBase(BaseModel):
    national_id: Optional[str] = None
    name: str
    phone: Optional[str] = None
    mail: Optional[EmailStr] = None
    short_address: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: int

    model_config = {"from_attributes": True}

class ClientUpdate(BaseModel):
    national_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    mail: Optional[EmailStr] = None
    short_address: Optional[str] = None

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

    model_config = {"from_attributes": True}

class DeviceUpdate(BaseModel):
    client_id: Optional[int] = None
    device_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None

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
    is_active: Optional[bool] = True
    tax_id_doc: Optional[str] = None
    national_id_doc: Optional[str] = None
    profile_photo: Optional[str] = None

class EmployeeDirectoryCreate(EmployeeDirectoryBase):
    pass

class EmployeeDirectoryResponse(EmployeeDirectoryBase):
    id: int

    model_config = {"from_attributes": True}

class EmployeeDirectoryUpdate(BaseModel):
    full_name: Optional[str] = None
    national_id: Optional[str] = None
    tax_id: Optional[str] = None
    short_address: Optional[str] = None
    occupation: Optional[str] = None
    employee_code: Optional[str] = None
    entry_date: Optional[date] = None
    is_active: Optional[bool] = None
    tax_id_doc: Optional[str] = None
    national_id_doc: Optional[str] = None
    profile_photo: Optional[str] = None

# =========================================================================
#---------------------------------TECHNICIAN-------------------------------
# =========================================================================

class TechnicianBase(BaseModel):
    commission: Optional[int] = None

    employee_id: int

class TechnicianCreate(TechnicianBase):
    pass

class TechnicianResponse(TechnicianBase):
    id: int

    model_config = {"from_attributes": True}

class TechnicianUpdate(BaseModel):
    commission: Optional[int] = None

    employee_id: Optional[int] = None

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
    agreed_price: Optional[int] = None
    exit_date: Optional[date] = None

    client_id: int
    device_id: int
    technician_id: int

class RepairOrderCreate(RepairOrderBase):
    pass

class RepairOrderResponse(RepairOrderBase):
    id: int
    client: Optional[ClientResponse] = None
    device: Optional[DeviceResponse] = None

    model_config = {"from_attributes": True}

class RepairOrderUpdate(BaseModel):
    entry_date: Optional[date] = None
    is_warranty: Optional[bool] = None
    status: Optional[StatusOrder] = None
    agreed_price: Optional[int] = None
    exit_date: Optional[date] = None

    client_id: Optional[int] = None
    device_id: Optional[int] = None
    technician_id: Optional[int] = None

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

    model_config = {"from_attributes": True}

class SparePartUpdate(BaseModel):
    name: Optional[str] = None
    stock: Optional[int] = None
    price: Optional[int] = None

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

    model_config = {"from_attributes": True}

class OrderSparePartUpdate(BaseModel):
    quantity: Optional[int] = None
    repair_order_id: Optional[int] = None
    spare_part_id: Optional[int] = None

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

    model_config = {"from_attributes": True}

class ServiceTypeUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None

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

    model_config = {"from_attributes": True}

class OrderServiceUpdate(BaseModel):
    repair_order_id: Optional[int] = None
    service_types_id: Optional[int] = None

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

    model_config = {"from_attributes": True}

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[int] = None
    expense_date: Optional[date] = None
    category: Optional[str] = None

# =========================================================================
#---------------------------------ATTENDANCE-------------------------------
# =========================================================================

class StatusAttendance(str, Enum):
    PRESENT = "Presente"
    ABSENT = "Ausente"
    PERMISSION = "Permiso"
    HEALTH = "Salud"

class AttendanceBase(BaseModel):
    date_now: date
    status: Optional[StatusAttendance] = StatusAttendance.ABSENT

    employee_id: int

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceResponse(AttendanceBase):
    id: int

    model_config = {"from_attributes": True}

class AttendanceUpdate(BaseModel):
    date_now: Optional[date] = None
    status: Optional[StatusAttendance] = None

    employee_id: Optional[int] = None

# =========================================================================
#-----------------------------------USERS----------------------------------
# =========================================================================

class UserRole(str, Enum):
    ADMIN = "Admin"
    DIRECTOR = "Director"
    OPERATOR = "Operator"
    TECHNICIAN = "Technician"
    CLIENT = "Client"

class UserBase(BaseModel):
    username: str
    is_active: bool = True
    mail: Optional[EmailStr] = None
    role: Optional[UserRole] = UserRole.CLIENT
    
    employee_id: Optional[int] = None
    client_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    username: Optional[str] = None
    is_active: Optional[bool] = None
    mail: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None

    employee_id: Optional[int] = None
    client_id: Optional[int] = None

# =========================================================================
#---------------------------------AUDITLOG---------------------------------
# =========================================================================

class AuditLogBase(BaseModel):
    action: str
    entity: str
    entity_id: int
    details: Optional[str] = None

    user_id: int

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

class AuditLogUpdate(BaseModel):
    pass

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

    model_config = {"from_attributes": True}

class StorageUpdate(BaseModel):
    entry_date: Optional[date] = None
    column: Optional[str] = None

    device_id: Optional[int] = None