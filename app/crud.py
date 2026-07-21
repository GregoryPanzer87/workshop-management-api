from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models import (
    Client, Device, EmployeeDirectory, Technician, RepairOrder, 
    SparePart, OrderSparePart, ServiceType, OrderService, 
    Expense, Attendance, User, AuditLog
    )
from app.schemas import (
    ClientCreate, DeviceCreate, EmployeeDirectoryCreate, TechnicianCreate, RepairOrderCreate, 
    SparePartCreate, OrderSparePartCreate, ServiceTypeCreate, OrderServiceCreate, 
    ExpenseCreate, AttendanceCreate, UserCreate, AuditLogCreate
)

# =========================================================================
# GENERIC CLASS (CRUDBase)
# =========================================================================

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get a record by its ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieves a list of paginated records"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record using Pydantic v2 (model_dump)"""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
# =========================================================================
# SPECIALIST CLASS (INHERITANCE CRUDBase)
# =========================================================================

# --- CLIENT CRUD (SAFE DELETE) ---
class ClientCRUD(CRUDBase[Client, ClientCreate]):
    def remove_safely(self, db: Session, client_id: int):
        """Attempt to delete a client safely"""
        db_client = self.get(db, client_id)
        if not db_client:
            return None
        
        # Validación defensiva si tiene ordenes asociadas
        if hasattr(db_client, 'repair_orders') and db_client.repair_orders:
            raise ValueError("No se puede eliminar un cliente con historial de reparaciones.")
            
        db.delete(db_client)
        db.commit()
        return db_client


# --- EMPLOYEE CRUD (LOGIC DELETE) ---
class EmployeeCRUD(CRUDBase[EmployeeDirectory, EmployeeDirectoryCreate]):
    def deactivate(self, db: Session, employee_id: int):
        """Deactivate an employee (is_active = False) instead of deleting it"""
        db_employee = self.get(db, employee_id)
        if db_employee:
            db_employee.is_active = False
            db.commit()
            db.refresh(db_employee)
            return db_employee
        return None


# --- TECHNICAL CRUD (JOIN) ---
class TechnicianCRUD(CRUDBase[Technician, TechnicianCreate]):
    def get_by_code(self, db: Session, employee_code: str):
        """Search a technician using the employee code"""
        return db.query(Technician).\
            join(EmployeeDirectory).\
            filter(EmployeeDirectory.employee_code == employee_code).first()


# =========================================================================
# 3. READY-TO-USE INSTANCES FOR MAIN
# =========================================================================

crud_client = ClientCRUD(Client)
crud_device = CRUDBase[Device, DeviceCreate](Device)
crud_employee = EmployeeCRUD(EmployeeDirectory)
crud_technician = TechnicianCRUD(Technician)
crud_repair_order = CRUDBase[RepairOrder, RepairOrderCreate](RepairOrder)
crud_spare_part = CRUDBase[SparePart, SparePartCreate](SparePart)
crud_order_spare_part = CRUDBase[OrderSparePart, OrderSparePartCreate](OrderSparePart)
crud_service_type = CRUDBase[ServiceType, ServiceTypeCreate](ServiceType)
crud_order_service = CRUDBase[OrderService, OrderServiceCreate](OrderService)
crud_expense = CRUDBase[Expense, ExpenseCreate](Expense)
crud_attendance = CRUDBase[Attendance, AttendanceCreate](Attendance)
crud_user = CRUDBase[User, UserCreate](User)
crud_audit = CRUDBase[AuditLog, AuditLogCreate](AuditLog)