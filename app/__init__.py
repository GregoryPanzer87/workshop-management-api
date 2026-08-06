from .database import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,
    DATABASE_URL, SessionLocal, Base, get_db
)

from .models_repairs import (
    Client, DeviceType, DeviceBrand, Device, Technician, RepairOrder, SparePart, 
    OrderSparePart, ServiceType, OrderService, Storage
)

from .models_others import (
    EmployeeDirectory, User, AuditLog, Expense, Attendance
)

from .schemas_repairs import (
    # Clients
    ClientBase, ClientCreate, ClientResponse, ClientUpdate, ClientMinResponse,
    # Devices Types
    DeviceTypeBase, DeviceTypeCreate, DeviceTypeResponse, DeviceTypeUpdate,
    # Devices Brands
    DeviceBrandBase, DeviceBrandCreate, DeviceBrandResponse, DeviceBrandUpdate,
    # Devices
    DeviceBase, DeviceCreate, DeviceResponse, DeviceUpdate, DeviceMinResponse,
    # Repair Orders
    RepairOrderBase, RepairOrderCreate, RepairOrderResponse, RepairOrderDetailResponse, RepairOrderUpdate,
    # Technician
    TechnicianBase, TechnicianCreate, TechnicianResponse, TechnicianUpdate,
    # Spare Parts & Services
    SparePartBase, SparePartCreate, SparePartResponse, SparePartUpdate,
    OrderSparePartBase, OrderSparePartCreate, OrderSparePartResponse, OrderSparePartUpdate,
    ServiceTypeBase, ServiceTypeCreate, ServiceTypeResponse, ServiceTypeUpdate,
    OrderServiceBase, OrderServiceCreate, OrderServiceResponse, OrderServiceUpdate,
    # Storage
    StorageBase, StorageCreate, StorageResponse, StorageUpdate
)

from .schemas_others import (
    # Users
    UserRole, UserBase, UserCreate, UserResponse, UserUpdate,
    # Employee Directory
    EmployeeDirectoryBase, EmployeeDirectoryCreate, EmployeeDirectoryResponse, EmployeeDirectoryUpdate,
    # Expense
    ExpenseBase, ExpenseCreate, ExpenseResponse, ExpenseUpdate,
    # Attendance
    AttendanceBase, AttendanceCreate, AttendanceResponse, AttendanceUpdate,
    # Audit Log
    AuditLogBase, AuditLogCreate, AuditLogResponse, AuditLogUpdate
)

from .crud import (
    crud_client, crud_device_type, crud_device_brand, crud_device, crud_employee, 
    crud_technician, crud_repair_order, crud_spare_part, crud_order_spare_part, 
    crud_service_type, crud_order_service, crud_expense, crud_attendance,
    crud_user, crud_audit, crud_storage
)

from .config import (
    EmptyStrToNone, EmptyEmailToNone, EmptyFloatToNone, EmptyIntToNone,
    EmptyDateToNone, EmptyBoolToNone
)