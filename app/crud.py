from typing import (
    Generic, TypeVar,
    Type, Optional,
    List, Any, Union,
    Dict, Sequence
)
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from pydantic import BaseModel
from sqlalchemy.orm import joinedload
from app import (
    # Client
    Client, ClientCreate, ClientUpdate,
    # Device Type
    DeviceType, DeviceTypeCreate, DeviceTypeUpdate,
    # Device Brand
    DeviceBrand, DeviceBrandCreate, DeviceBrandUpdate,
    # Device
    Device, DeviceCreate, DeviceUpdate,
    # Employee
    EmployeeDirectory, EmployeeDirectoryCreate, EmployeeDirectoryUpdate,
    # Technician
    Technician, TechnicianCreate, TechnicianUpdate,
    # Repair Order
    RepairOrder, RepairOrderCreate, RepairOrderUpdate,
    # Spare Part
    SparePart, SparePartCreate, SparePartUpdate,
    # Order Spare Part
    OrderSparePart, OrderSparePartCreate, OrderSparePartUpdate,
    # Service Type
    Service, ServiceCreate, ServiceUpdate,
    # Order Service
    OrderService, OrderServiceCreate, OrderServiceUpdate,
    # Expense
    Expense, ExpenseCreate, ExpenseUpdate,
    # Attendace
    Attendance, AttendanceCreate, AttendanceUpdate,
    # User
    User, UserCreate, UserUpdate,
    # AuditLog
    AuditLog, AuditLogCreate, AuditLogUpdate,
    #Storage
    Storage, StorageCreate, StorageUpdate,
    )
from app.core.security import get_password_hash

# =========================================================================
# GENERIC CLASS (CRUDBase)
# =========================================================================

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    #---------------------------------------------------------------------------------------

    def get_by_id(self, db: Session, id: int, options: Optional[Sequence[Any]] = None) -> Optional[ModelType]:
        """Get a record by its ID"""
        stmt = select(self.model).where(self.model.id == id)

        if options:
            stmt = stmt.options(*options)

        return db.scalar(stmt)

    #---------------------------------------------------------------------------------------
    
    def get_by_other(self, db: Session, value: Any, field: str, options: Optional[Sequence[Any]] = None) -> Optional[ModelType]:
        """Get a record by other values"""
        column = getattr(self.model, field)
        stmt = select(self.model).where(column == value)
        
        if options:
            stmt = stmt.options(*options)

        return db.scalar(stmt)

    #---------------------------------------------------------------------------------------

    def get_multi(self, db: Session, options: Optional[Sequence[Any]] = None, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieves a list of paginated records"""
        stmt = select(self.model).offset(skip).limit(limit)

        if options:
            stmt = stmt.options(*options)

        return list(db.scalars(stmt).all())

    #---------------------------------------------------------------------------------------
    
    def list_get_by_other(self, db: Session, value: int, field: Any, options: Optional[Sequence[Any]] = None, skip: int = 0, limit: int = 20) -> List[ModelType]:
        column = getattr(self.model, field)
        stmt = select(self.model).where(column == value).offset(skip).limit(limit)

        if options:
            stmt = stmt.options(*options)

        return list(db.scalars(stmt).all())

    #---------------------------------------------------------------------------------------

    def create(self, db: Session, *, obj_in: Union[CreateSchemaType, Dict[str, Any]]) -> ModelType:
        """Create a new record using Pydantic v2 (model_dump) or a dictionary."""
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.model_dump()

        db_obj = self.model(**create_data)
        db.add(db_obj)
        db.flush()
        return db_obj

    #---------------------------------------------------------------------------------------

    def search_where_by_fields(self, db: Session, **filters) -> Optional[ModelType]:
        if not filters:
            return None

        conditions = [
            getattr(self.model, field) == value 
            for field, value in filters.items() 
            if hasattr(self.model, field) and value is not None
        ]
        
        if not conditions:
            return None

        stmt = select(self.model).where(*conditions)
        return db.scalar(stmt)

    #---------------------------------------------------------------------------------------

    def search_ilike(
        self, 
        db: Session, 
        query: str, 
        search_fields: List[Any],
        joins: Optional[List[Any]] = None, 
        options: Optional[List[Any]] = None,  # <- Agregamos options
        limit: int = 20
    ) -> List[ModelType]:
        """Search in tables by database with support for eager loading."""
        if not query or not query.strip():
            return self.get_multi(db, limit=limit, options=options)

        clean_query = query.strip()
        search_pattern = f"%{clean_query}%"

        filters = [field.ilike(search_pattern) for field in search_fields if field is not None]
        if not filters:
            return self.get_multi(db, limit=limit, options=options)

        stmt = select(self.model)

        if joins:
            for join_model in joins:
                stmt = stmt.join(join_model)

        if options:
            for option in options:
                stmt = stmt.options(option)

        stmt = stmt.where(or_(*filters)).distinct().limit(limit)
        
        return list(db.scalars(stmt).all())

    #---------------------------------------------------------------------------------------
    
    def update(
        self, 
        db: Session, 
        db_obj: ModelType, 
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.flush()

        return db_obj

    def delete(self, db: Session, db_obj:  ModelType) -> Optional[ModelType]:   
        db.delete(db_obj)
        db.flush()

        return db_obj
        
# =========================================================================
# SPECIALIST CLASS (INHERITANCE CRUDBase)
# =========================================================================

# --- DEVICE CRUD (CHANGE OWNER) ---
class DeviceCRUD(CRUDBase[Device, DeviceCreate, DeviceUpdate]):
    def update_owner(self, db: Session, device_id: int, new_client_id: int) -> Device:
        """Assign id_client to a new client without changes to the history"""
        db_device = self.get_by_id(db, id=device_id)
        db_device.client_id = new_client_id
        db.flush()
        return db_device

# --- REPAIR ORDER CRUD (SAFE DELETE) ---
class RepairOrderCRUD(CRUDBase[RepairOrder, RepairOrderCreate, RepairOrderUpdate]):
    def delete(self, db: Session, db_obj: RepairOrder) -> RepairOrder:
        """Attempt to delete a order repair safely"""
        # Validación defensiva si tiene ordenes asociadas
        if (
        (hasattr(db_obj, 'order_spare_parts') and db_obj.order_spare_parts) or 
        (hasattr(db_obj, 'order_services') and db_obj.order_services)
        ):
            raise ValueError("No se puede eliminar una orden con repuestos o servicios realizados.")
                
        db.delete(db_obj)
        db.flush()
        return db_obj

# --- EMPLOYEE CRUD (LOGIC DELETE) ---
class EmployeeCRUD(CRUDBase[EmployeeDirectory, EmployeeDirectoryCreate, EmployeeDirectoryUpdate]):
    def delete(self, db: Session, db_obj: EmployeeDirectory) -> EmployeeDirectory:
        """Deactivate an employee (is_active = False) instead of deleting it"""
        db_obj.is_active = False
        db.flush()
        return db_obj


# --- TECHNICIAN CRUD (JOIN) ---
class TechnicianCRUD(CRUDBase[Technician, TechnicianCreate, TechnicianUpdate]):
    def get_by_code(self, db: Session, employee_code: str):
        """Search a technician using the employee code"""
        stmt =  (
            select(Technician)
            .join(EmployeeDirectory)
            .where(EmployeeDirectory.employee_code == employee_code)
        )
        return db.scalar(stmt)

    def delete(self, db: Session, db_obj: Technician) -> Technician:
        """Deactivate an technician (is_active = False) instead of deleting it"""
        db_obj.is_active = False
        db.flush()
        return db_obj

# --- USER CRUD ---
class UserCRUD(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        emp_id = obj_in.employee_id if obj_in.employee_id != 0 else None
        cli_id = obj_in.client_id if obj_in.client_id != 0 else None

        db_user = User(
            username=obj_in.username,
            password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active,
            mail=obj_in.mail,
            role=obj_in.role,

            employee_id=emp_id,
            client_id=cli_id
        )
        db.add(db_user)
        db.flush()
        return db_user

# =========================================================================
# 3. READY-TO-USE INSTANCES FOR MAIN
# =========================================================================

crud_client = CRUDBase[Client, ClientCreate, ClientUpdate](Client)
crud_device_type = CRUDBase[DeviceType, DeviceTypeCreate, DeviceTypeUpdate](DeviceType)
crud_device_brand = CRUDBase[DeviceBrand, DeviceBrandCreate, DeviceBrandUpdate](DeviceBrand)
crud_device = DeviceCRUD(Device)
crud_employee = EmployeeCRUD(EmployeeDirectory)
crud_technician = TechnicianCRUD(Technician)
crud_repair_order = RepairOrderCRUD(RepairOrder)
crud_spare_part = CRUDBase[SparePart, SparePartCreate, SparePartUpdate](SparePart)
crud_order_spare_part = CRUDBase[OrderSparePart, OrderSparePartCreate, OrderSparePartUpdate](OrderSparePart)
crud_services = CRUDBase[Service, ServiceCreate, ServiceUpdate](Service)
crud_order_service = CRUDBase[OrderService, OrderServiceCreate, OrderServiceUpdate](OrderService)
crud_expense = CRUDBase[Expense, ExpenseCreate, ExpenseUpdate](Expense)
crud_attendance = CRUDBase[Attendance, AttendanceCreate, AttendanceUpdate](Attendance)
crud_user = UserCRUD(User)
crud_audit = CRUDBase[AuditLog, AuditLogCreate, AuditLogUpdate](AuditLog)
crud_storage = CRUDBase[Storage, StorageCreate, StorageUpdate](Storage)