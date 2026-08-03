from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app import Base

# =========================================================================
# TABLE EMPLOYEE DIRECTORY
# =========================================================================

class EmployeeDirectory(Base):
    __tablename__ = "employee_directory"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(80), nullable=False)
    national_id = Column(String(20), nullable=False)
    tax_id = Column(String(20), nullable=False)
    short_address = Column(String(30), nullable=False)
    occupation = Column(String(30), nullable=False)
    employee_code = Column(String(15), nullable=True)
    entry_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    tax_id_doc = Column(String(150), nullable=True)
    national_id_doc = Column(String(150), nullable=True)
    profile_photo = Column(String(150), nullable=True)

    #Relationships
    technicians = relationship("Technician", back_populates="employee")
    attendances = relationship("Attendance", back_populates="employee")
    user = relationship("User", back_populates="employee", uselist=False)

# =========================================================================
# TABLE USERS
# =========================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    mail = Column(String(100), unique=True, nullable=True)
    role = Column(String(60), nullable=False)
    
    # Llaves foráneas opcionales
    employee_id = Column(Integer, ForeignKey("employee_directory.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)

    #Relationships
    employee = relationship("EmployeeDirectory", back_populates="user")
    client = relationship("Client", back_populates="user")
    logs = relationship("AuditLog", back_populates="user")

# =========================================================================
# TABLE AUDITLOGS
# =========================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    entity = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    details = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    #Relationships
    user = relationship("User", back_populates="logs")

# =========================================================================
# TABLE EXPENSES
# =========================================================================

class Expense(Base):
    __tablename__ = "expenses"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    description = Column(String(100), nullable=False)
    amount = Column(Integer, nullable=False)
    expense_date = Column(Date, nullable=False)
    category = Column(String(30), nullable=False)

# =========================================================================
# TABLE ATTENDANCE
# =========================================================================

class Attendance(Base):
    __tablename__ = "attendances"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date_now = Column(Date, nullable=False)
    status = Column(String(15), nullable=False)

    #ForeingKeys
    employee_id = Column(Integer, ForeignKey("employee_directory.id"), nullable=False)

    #Relationships
    employee = relationship("EmployeeDirectory", back_populates="attendances")