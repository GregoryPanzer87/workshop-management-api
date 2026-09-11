from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from enum import Enum
from app.config import EmptyEmailToNone, EmptyStrToNone, EmptyIntToNone, EmptyBoolToNone, EmptyDateToNone

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
#---------------------------------EMPLOYEE DIRECTORY-----------------------
# =========================================================================

class EmployeeDirectoryBase(BaseModel):
    full_name: str
    national_id: str
    tax_id: str
    short_address: str
    occupation: str
    employee_code: EmptyStrToNone = None
    entry_date: date
    is_active: EmptyBoolToNone = None
    tax_id_doc: EmptyStrToNone = None
    national_id_doc: EmptyStrToNone = None
    profile_photo: EmptyStrToNone = None

class EmployeeDirectoryCreate(EmployeeDirectoryBase, ConfigCreate):
    pass

class UserCredentials(BaseModel):
    username: str
    password: str

class EmployeeDirectoryResponse(EmployeeDirectoryBase, ConfigResponse):
    id: int
    employee_code: str
    initial_credentials: Optional[UserCredentials] = None

class EmployeeDirectoryUpdate(BaseModel):
    full_name: EmptyStrToNone = None
    national_id: EmptyStrToNone = None
    tax_id: EmptyStrToNone = None
    short_address: EmptyStrToNone = None
    occupation: EmptyStrToNone = None
    employee_code: EmptyStrToNone = None
    entry_date: EmptyDateToNone = None
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
    BASE = "Base"
    CUSTOMER = "Customer"

class UserBase(BaseModel):
    username: str
    is_active: bool = True
    mail: EmptyEmailToNone = None
    role: Optional[UserRole] = UserRole.CUSTOMER
    
    employee_id: EmptyIntToNone = None
    client_id: EmptyIntToNone = None

class UserCreate(UserBase, ConfigCreate):
    password: str

class UserResponse(UserBase, ConfigResponse):
    id: int

class UserUpdate(BaseModel):
    username: EmptyStrToNone = None
    mail: EmptyEmailToNone = None
    role: Optional[UserRole] = None
    password: EmptyStrToNone = None

    employee_id: EmptyIntToNone = None
    customer_id: EmptyIntToNone = None
    
# =========================================================================
#---------------------------------EXPENSE----------------------------------
# =========================================================================

class ExpenseBase(BaseModel):
    description: str
    amount: int
    expense_date: date
    category: str

class ExpenseCreate(ExpenseBase, ConfigCreate):
    pass

class ExpenseResponse(ExpenseBase, ConfigResponse):
    id: int

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

class AttendanceCreate(AttendanceBase, ConfigCreate):
    pass

class AttendanceResponse(AttendanceBase, ConfigResponse):
    id: int

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
    entity_id: EmptyIntToNone = None
    details: EmptyStrToNone = None

    user_id: int

class AuditLogCreate(AuditLogBase, ConfigCreate):
    pass

class AuditLogResponse(AuditLogBase, ConfigResponse):
    id: int
    created_at: datetime

class AuditLogUpdate(BaseModel):
    pass