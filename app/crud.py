from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from app.models import (
    Client, Device, EmployeeDirectory, Technician, RepairOrder, 
    SparePart, OrderSparePart, ServiceType, OrderService, 
    Expense, Attendance, User, AuditLog, Storage
    )
from app.schemas import (
    ClientCreate, DeviceCreate, EmployeeDirectoryCreate, TechnicianCreate, RepairOrderCreate, 
    SparePartCreate, OrderSparePartCreate, ServiceTypeCreate, OrderServiceCreate, 
    ExpenseCreate, AttendanceCreate, UserCreate, AuditLogCreate, StorageCreate
)

from app.schemas import (
    ClientUpdate, DeviceUpdate, EmployeeDirectoryUpdate, TechnicianUpdate, RepairOrderUpdate, 
    SparePartUpdate, OrderSparePartUpdate, ServiceTypeUpdate, OrderServiceUpdate, 
    ExpenseUpdate, AttendanceUpdate, UserUpdate, AuditLogUpdate, StorageUpdate
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

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get a record by its ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    #---------------------------------------------------------------------------------------

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieves a list of paginated records"""
        return db.query(self.model).offset(skip).limit(limit).all()

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

    def search(
        self, 
        db: Session, 
        query: str, 
        search_fields: List[Any], 
        limit: int = 20
    ) -> List[ModelType]:
        """Busca clientes por nombre, identificación o teléfono."""
        if not query or not query.strip():
            return self.get_multi(db, limit=limit)

        # 2. Limpiamos el texto ingresado
        clean_query = query.strip()
        search_pattern = f"%{clean_query}%"
        
        # 3. Construimos los filtros solo con los campos válidos
        filters = [field.ilike(search_pattern) for field in search_fields if field is not None]

        # 4. Si por alguna razón no hay filtros válidos, no ejecutamos or_()
        if not filters:
            return self.get_multi(db, limit=limit)

        # 5. Ejecutamos la consulta con or_
        return db.query(self.model).filter(or_(*filters)).limit(limit).all()

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
        db_delete = self.get(db, id)

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
        db_client = self.get(db, id)
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
        db_device = self.get(db, id=device_id)

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
        db_order_repair = self.get(db, id)
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
    def deactivate(self, db: Session, employee_id: int):
        """Deactivate an employee (is_active = False) instead of deleting it"""
        db_employee = self.get(db, employee_id)
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
        return db.query(Technician).\
            join(EmployeeDirectory).\
            filter(EmployeeDirectory.employee_code == employee_code).first()

# --- STORAGE CRUD (DELETE) ---
class StorageCRUD(CRUDBase[Storage, StorageCreate, StorageUpdate]):
    def remove_safely(self, db: Session, device_id: int):
        db_storage = self.get(db, device_id)
        if not db_storage:
            return None

        db.delete(db_storage)
        db.commit()
        return db_storage

# --- USER CRUD ---
class UserCRUD(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_user = User(
            username=obj_in.username,
            hashed_password=get_password_hash(obj_in.password),
            permission=obj_in.permission,
            is_active=obj_in.is_active,
            employee_id=obj_in.employee_id
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def get_by_user(self, db: Session, user: str) -> Optional[User]:
        """Get a record by its username"""
        return db.query(User).filter(User.username == user).first()

# =========================================================================
# 3. READY-TO-USE INSTANCES FOR MAIN
# =========================================================================

crud_client = ClientCRUD(Client)
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