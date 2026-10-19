from .database import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,
    DATABASE_URL, SessionLocal, Base, get_db
)

from .models_repairs import (
    Customer, DeviceType, DeviceBrand, DeviceModel, Device, Technician, RepairOrder, SparePart, 
    OrderSparePart, Service, OrderService, Storage
)

from .models_others import (
    EmployeeDirectory, User, AuditLog, Expense, Attendance, ExchangeRate
)

from .schemas_repairs import (
    # Clients
    CustomerBase, CustomerCreate, CustomerResponse, CustomerUpdate, CustomerMinResponse, OrderCustomerResponse,
    # Devices Types
    DeviceTypeBase, DeviceTypeCreate, DeviceBatchCreate, DeviceTypeResponse, DeviceTypeUpdate,
    # Devices Brands
    DeviceBrandBase, DeviceBrandCreate, DeviceBrandResponse, DeviceBrandUpdate,
    # Devices Brands
    DeviceModelBase, DeviceModelCreate, DeviceModelResponse, DeviceModelMinResponse, DeviceModelUpdate,
    # Devices
    DeviceBase, DeviceCreate, DeviceBaseResponse, DeviceResponse, DeviceUpdate, DeviceMinResponse,
    # Repair Orders
    RepairOrderBase, StatusOrder, RepairOrderCreate, RepairOrderBatchCreate, 
    RepairOrderResponse, RepairOrderDetailResponse, RepairOrderUpdate,
    RepairOrderUpdateStatus, RepairOrderUpdateDescription, RepairOrderUpdateTechnician,
    # Technician
    TechnicianBase, TechnicianCreate, TechnicianResponse, TechnicianUpdate,
    # Spare Parts & Services
    SparePartBase, SparePartCreate, SparePartResponse, SparePartUpdate,
    OrderSparePartBase, OrderSparePartCreate, OrderSparePartBatchCreate, OrderSparePartResponse, OrderSparePartUpdate,
    ServiceBase, ServiceCreate, ServiceResponse, ServiceUpdate,
    OrderServiceBase, OrderServiceCreate, OrderServiceBatchCreate, OrderServiceResponse, OrderServiceUpdate,
    # Storage
    StorageBase, StorageCreate, StorageResponse, StorageUpdate
)

from .schemas_others import (
    # Users
    UserRole, UserBase, UserCreate, UserResponse, UserLowResponse, UserUpdate,
    # Employee Directory
    EmployeeDirectoryBase, EmployeeDirectoryCreate, EmployeeDirectoryResponse, EmployeeDirectoryUpdate,
    # Expense
    ExpenseBase, ExpenseCreate, ExpenseResponse, ExpenseUpdate,
    # Attendance
    AttendanceBase, AttendanceCreate, AttendanceResponse, AttendanceUpdate,
    # Audit Log
    AuditLogBase, AuditLogCreate, AuditLogResponse, AuditLogUpdate,
    # Exchange Rate
    ExchangeRateBase, ExchangeRateCreate, ExchangeRateBatchCreate, ExchangeRateResponse, ExchangeRateUpdate
)

from .crud import (
    crud_customer, crud_device_type, crud_device_brand, crud_device_model, crud_device, crud_employee, 
    crud_technician, crud_repair_order, crud_spare_part, crud_order_spare_part, 
    crud_service, crud_order_service, crud_expense, crud_attendance,
    crud_user, crud_audit, crud_storage, crud_exchange_rate, ModelType, CRUDBase
)

from .config import (
    EmptyStrToNone, EmptyEmailToNone, EmptyFloatToNone, EmptyIntToNone,
    EmptyDateToNone, EmptyBoolToNone
)