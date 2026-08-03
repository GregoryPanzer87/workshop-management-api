from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from enum import Enum

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