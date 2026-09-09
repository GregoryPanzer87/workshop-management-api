# app/models_others.py
from datetime import date, datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import Base

if TYPE_CHECKING:
    from app import Customer, Technician

# =========================================================================
# TABLE EMPLOYEE DIRECTORY
# =========================================================================

class EmployeeDirectory(Base):
    __tablename__ = "employee_directory"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(250), nullable=False)
    national_id: Mapped[str] = mapped_column(String(20), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(20), nullable=False)
    short_address: Mapped[str] = mapped_column(String(30), nullable=False)
    occupation: Mapped[str] = mapped_column(String(50), nullable=False)
    employee_code: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    entry_date: Mapped[date] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    tax_id_doc: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    national_id_doc: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    profile_photo: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Relationships
    technicians: Mapped[List["Technician"]] = relationship("Technician", back_populates="employee")
    attendances: Mapped[List["Attendance"]] = relationship("Attendance", back_populates="employee")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="employee", uselist=False)

# =========================================================================
# TABLE USERS
# =========================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    mail: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(60), nullable=False)
    
    # ForaingKeys
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employee_directory.id"), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)

    # Relationships
    employee: Mapped[Optional["EmployeeDirectory"]] = relationship("EmployeeDirectory", back_populates="user")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="user")
    logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")

# =========================================================================
# TABLE AUDITLOGS
# =========================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    details: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="logs")

# =========================================================================
# TABLE EXPENSES
# =========================================================================

class Expense(Base):
    __tablename__ = "expenses"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)
    expense_date: Mapped[date] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)

# =========================================================================
# TABLE ATTENDANCE
# =========================================================================

class Attendance(Base):
    __tablename__ = "attendances"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    date_now: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False)

    # ForeignKeys
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee_directory.id"), nullable=False)

    # Relationships
    employee: Mapped["EmployeeDirectory"] = relationship("EmployeeDirectory", back_populates="attendances")