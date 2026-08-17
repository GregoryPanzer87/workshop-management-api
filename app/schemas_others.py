from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from enum import Enum
from app.config import EmptyEmailToNone, EmptyStrToNone, EmptyIntToNone, EmptyBoolToNone, EmptyDateToNone

# =========================================================================
#---------------------------------EMPLOYEE DIRECTORY-----------------------
# =========================================================================

class EmployeeDirectoryBase(BaseModel):
    full_name: str
    national_id: str
    tax_id: str
    short_address: str
    occupation: str
    employee_code: str = None
    entry_date: date
    is_active: EmptyBoolToNone = None
    tax_id_doc: EmptyStrToNone = None
    national_id_doc: EmptyStrToNone = None
    profile_photo: EmptyStrToNone = None

class EmployeeDirectoryCreate(EmployeeDirectoryBase):
    pass

class UserCredentials(BaseModel):
    username: str
    password: str

class EmployeeDirectoryResponse(EmployeeDirectoryBase):
    id: int
    employee_code: str
    initial_credentials: Optional[UserCredentials]

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class EmployeeDirectoryUpdate(BaseModel):
    full_name: EmptyStrToNone = None
    national_id: EmptyStrToNone = None
    tax_id: EmptyStrToNone = None
    short_address: EmptyStrToNone = None
    occupation: EmptyStrToNone = None
    employee_code: EmptyStrToNone = None
    entry_date: EmptyDateToNone = None
    is_active: EmptyBoolToNone = None
    tax_id_doc: EmptyStrToNone = None
    national_id_doc: EmptyStrToNone = None
    profile_photo: EmptyStrToNone = None

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
    mail: EmptyEmailToNone = None
    role: Optional[UserRole] = UserRole.CLIENT
    
    employee_id: EmptyIntToNone = None
    client_id: EmptyIntToNone = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class UserUpdate(BaseModel):
    username: EmptyStrToNone = None
    is_active: EmptyBoolToNone = None
    mail: EmptyEmailToNone = None
    role: Optional[UserRole] = None
    password: EmptyStrToNone = None

    employee_id: EmptyIntToNone = None
    client_id: EmptyIntToNone = None
    
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

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class ExpenseUpdate(BaseModel):
    description: EmptyStrToNone = None
    amount: EmptyIntToNone = None
    expense_date: EmptyDateToNone = None
    category: EmptyStrToNone = None

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

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class AttendanceUpdate(BaseModel):
    date_now: EmptyDateToNone = None
    status: Optional[StatusAttendance] = None

    employee_id: EmptyIntToNone = None

# =========================================================================
#---------------------------------AUDITLOG---------------------------------
# =========================================================================

class AuditLogBase(BaseModel):
    action: str
    entity: str
    entity_id: int
    details: EmptyStrToNone = None

    user_id: int

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True, "str_strip_whitespace": True}

class AuditLogUpdate(BaseModel):
    pass