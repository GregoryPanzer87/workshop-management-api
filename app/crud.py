from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from pydantic import BaseModel
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
    ServiceType, ServiceTypeCreate, ServiceTypeUpdate,
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

    def get_by_id(self, db: Session, id: int) -> Optional[ModelType]:
        """Get a record by its ID"""
        return db.get(self.model, id)

    #---------------------------------------------------------------------------------------
    
    def get_by_other(self, db: Session, value: str, field: str) -> Optional[ModelType]:
        """Get a record by other values"""
        column = getattr(self.model, field)
        stmt = select(self.model).where(column == value)
        return db.scalar(stmt)

    #---------------------------------------------------------------------------------------

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieves a list of paginated records"""
        stmt = select(self.model).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    #---------------------------------------------------------------------------------------
    
    def get_other_id(self, db: Session, id: int, field: str, skip: int = 0, limit: int = 20) -> List[ModelType]:
        column = getattr(self.model, field)
        stmt = select(self.model).where(column == id).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    #---------------------------------------------------------------------------------------

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record using Pydantic v2 (model_dump)"""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    #---------------------------------------------------------------------------------------
    
    def search_where(
        self,
        db: Session,
        value_1: str,
        value_2: str,
        field_1: str,
        field_2: str
    ) -> Optional[ModelType]:
        column_1 = getattr(self.model, field_1)
        column_2 = getattr(self.model, field_2)
        stmt = select(self.model).where(
            column_1 == value_1,
            column_2 == value_2
        )
        return db.scalar(stmt)

    #---------------------------------------------------------------------------------------

    def search_where_by_IDs(
            self,
            db: Session,
            id_1: int,
            id_2: int,
            field_1: str,
            field_2: str
    ) -> Optional[ModelType]:
        column_1 = getattr(self.model, field_1)
        column_2 = getattr(self.model, field_2)
        stmt = select(self.model).where(
            column_1 == id_1,
            column_2 == id_2
        )
        return db.scalar(stmt)

    #---------------------------------------------------------------------------------------

    def search_ilike(
        self, 
        db: Session, 
        query: str, 
        search_fields: List[Any], 
        limit: int = 20
    ) -> List[ModelType]:
        """Search in tables by datebase"""
        if not query or not query.strip():
            return self.get_multi(db, limit=limit)

        clean_query = query.strip()
        search_pattern = f"%{clean_query}%"
        
        filters = [field.ilike(search_pattern) for field in search_fields if field is not None]

        if not filters:
            return self.get_multi(db, limit=limit)

        stmt = select(self.model).where(or_(*filters)).limit(limit)
        return list(db.scalars(stmt).all())

    #---------------------------------------------------------------------------------------
    
    def update(self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def delete(self, db: Session, id: int) -> Optional[ModelType]:
        db_delete = self.get_by_id(db, id)

        if not db_delete:
            return None
        
        db.delete(db_delete)
        db.commit()

        return db_delete
        
# =========================================================================
# SPECIALIST CLASS (INHERITANCE CRUDBase)
# =========================================================================

# --- CLIENT CRUD (SAFE DELETE) ---
class ClientCRUD(CRUDBase[Client, ClientCreate, ClientUpdate]):
    def delete(self, db: Session, id: int) :
        """Attempt to delete a client safely"""
        db_client = self.get_by_id(db, id)
        if not db_client:
            return None
        
        # Validación defensiva si tiene ordenes asociadas
        if hasattr(db_client, 'repairs_orders') and db_client.repairs_orders:
            raise ValueError("No se puede eliminar un cliente con historial de reparaciones.")
            
        db.delete(db_client)
        db.commit()
        return db_client

# --- DEVICE CRUD (CHANGE OWNER) ---
class DeviceCRUD(CRUDBase[Device, DeviceCreate, DeviceUpdate]):
    def update_owner(self, db: Session, device_id: int, new_client_id: int) -> Device:
        """Assign id_client to a new client without changes to the history"""
        db_device = self.get_by_id(db, id=device_id)

        if not db_device:
            return None
        
        db_device.client_id = new_client_id
        db.commit()
        db.refresh(db_device)
        return db_device

# --- REPAIR ORDER CRUD (SAFE DELETE) ---
class RepairOrderCRUD(CRUDBase[RepairOrder, RepairOrderCreate, RepairOrderUpdate]):
    def delete(self, db: Session, id: int) -> Optional[RepairOrder]:
        """Attempt to delete a order repair safely"""
        db_order_repair = self.get_by_id(db, id)
        if not db_order_repair:
            return None
            
        # Validación defensiva si tiene ordenes asociadas
        if (hasattr(db_order_repair, 'order_spare_parts') and db_order_repair.order_spare_parts) or (hasattr(db_order_repair, 'order_services') and db_order_repair.order_services):
            raise ValueError("No se puede eliminar una orden con repuestos o servicios realizados.")
                
        db.delete(db_order_repair)
        db.commit()
        return db_order_repair

# --- EMPLOYEE CRUD (LOGIC DELETE) ---
class EmployeeCRUD(CRUDBase[EmployeeDirectory, EmployeeDirectoryCreate, EmployeeDirectoryUpdate]):
    def delete(self, db: Session, id: int):
        """Deactivate an employee (is_active = False) instead of deleting it"""
        db_employee = self.get_by_id(db, id)
        if db_employee:
            db_employee.is_active = False
            db.commit()
            db.refresh(db_employee)
            return db_employee
        return None


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

    def delete(self, db: Session, id: int):
        """Deactivate an technician (is_active = False) instead of deleting it"""
        db_technician = self.get_by_id(db, id)
        if db_technician:
            db_technician.is_active = False
            db.commit()
            db.refresh(db_technician)
            return db_technician
        return None

# --- STORAGE CRUD (DELETE) ---
class StorageCRUD(CRUDBase[Storage, StorageCreate, StorageUpdate]):
    def get_by_serial_number(self, db: Session, serial_number: str):
        """Search a device using the serial_number"""
        stmt =  (
            select(Storage)
            .join(Device)
            .where(Device.serial_number == serial_number)
        )
        return db.scalar(stmt)

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
        db.commit()
        db.refresh(db_user)
        return db_user

    def get_by_user(self, db: Session, user: str) -> Optional[User]:
        """Get a record by its username"""
        stmt = select(User).where(User.username == user)
        return db.scalar(stmt)

# =========================================================================
# 3. READY-TO-USE INSTANCES FOR MAIN
# =========================================================================

crud_client = ClientCRUD(Client)
crud_device_type = CRUDBase[DeviceType, DeviceTypeCreate, DeviceTypeUpdate](DeviceType)
crud_device_brand = CRUDBase[DeviceBrand, DeviceBrandCreate, DeviceBrandUpdate](DeviceBrand)
crud_device = DeviceCRUD(Device)
crud_employee = EmployeeCRUD(EmployeeDirectory)
crud_technician = TechnicianCRUD(Technician)
crud_repair_order = RepairOrderCRUD(RepairOrder)
crud_spare_part = CRUDBase[SparePart, SparePartCreate, SparePartUpdate](SparePart)
crud_order_spare_part = CRUDBase[OrderSparePart, OrderSparePartCreate, OrderSparePartUpdate](OrderSparePart)
crud_service_type = CRUDBase[ServiceType, ServiceTypeCreate, ServiceTypeUpdate](ServiceType)
crud_order_service = CRUDBase[OrderService, OrderServiceCreate, OrderServiceUpdate](OrderService)
crud_expense = CRUDBase[Expense, ExpenseCreate, ExpenseUpdate](Expense)
crud_attendance = CRUDBase[Attendance, AttendanceCreate, AttendanceUpdate](Attendance)
crud_user = UserCRUD(User)
crud_audit = CRUDBase[AuditLog, AuditLogCreate, AuditLogUpdate](AuditLog)
crud_storage = StorageCRUD(Storage)