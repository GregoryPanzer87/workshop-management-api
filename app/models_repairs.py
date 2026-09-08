from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import Base

if TYPE_CHECKING:
    from app import User
    from app import EmployeeDirectory

# =========================================================================
# TABLE CLIENTS
# =========================================================================

class Client(Base):
    __tablename__ = "clients"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    short_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="client")
    repairs_orders: Mapped[List["RepairOrder"]] = relationship("RepairOrder", back_populates="client")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="client")

# =========================================================================
# TABLES DEVICES
# =========================================================================

class DeviceType(Base):
    __tablename__ = "device_types"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    prefix: Mapped[Optional[str]] = mapped_column(String(5), unique=True, nullable=True)
    
    # Relationships
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="device_type")

class DeviceBrand(Base):
    __tablename__ = "device_brands"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Relationships
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="device_brand")
    
class Device(Base):
    __tablename__ = "devices"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model: Mapped[str] = mapped_column(String(30), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # ForeignKeys corregidas (device_types y device_brands en singular)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    device_type_id: Mapped[int] = mapped_column(ForeignKey("device_types.id"), nullable=False)
    device_brand_id: Mapped[int] = mapped_column(ForeignKey("device_brands.id"), nullable=False)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="devices")
    device_type: Mapped["DeviceType"] = relationship("DeviceType", back_populates="devices")
    device_brand: Mapped["DeviceBrand"] = relationship("DeviceBrand", back_populates="devices")
    repairs_orders: Mapped[List["RepairOrder"]] = relationship("RepairOrder", back_populates="device")
    storage: Mapped[Optional["Storage"]] = relationship("Storage", back_populates="device")

# =========================================================================
# TABLE TECHNICIANS
# =========================================================================

class Technician(Base):
    __tablename__ = "technicians"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    commission: Mapped[Optional[int]] = mapped_column(nullable=True)

    # ForeignKeys
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employee_directory.id"), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    employee: Mapped[Optional["EmployeeDirectory"]] = relationship("EmployeeDirectory", back_populates="technicians")
    repairs_orders: Mapped[List["RepairOrder"]] = relationship("RepairOrder", back_populates="technician")

# =========================================================================
# TABLE REPAIRS ORDERS
# =========================================================================

class RepairOrder(Base):
    __tablename__ = "repairs_orders"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entry_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    is_warranty: Mapped[bool] = mapped_column(default=False)
    status: Mapped[Optional[str]] = mapped_column(String(30), nullable=False)
    exit_date: Mapped[Optional[datetime]] = mapped_column(Date,nullable=True)
    agreed_price: Mapped[Optional[float]] = mapped_column(nullable=True)
    legacy_order_id: Mapped[Optional[int]] = mapped_column(nullable=True)

    # ForeignKeys
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id"), nullable=False)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="repairs_orders")
    device: Mapped["Device"] = relationship("Device", back_populates="repairs_orders")
    order_spare_parts: Mapped[List["OrderSparePart"]] = relationship("OrderSparePart", back_populates="repair_order")
    order_services: Mapped[List["OrderService"]] = relationship("OrderService", back_populates="repair_order")
    technician: Mapped["Technician"] = relationship("Technician", back_populates="repairs_orders")

# =========================================================================
# TABLE SPARE PARTS
# =========================================================================

class SparePart(Base):
    __tablename__ = "spare_parts"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    component_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) 
    supplier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) 
    stock: Mapped[Optional[int]] = mapped_column(default=None, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    order_spare_parts: Mapped[List["OrderSparePart"]] = relationship("OrderSparePart", back_populates="spare_part")

# =========================================================================
# TABLE ORDER SPARE PARTS
# =========================================================================

class OrderSparePart(Base):
    __tablename__ = "order_spare_parts"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quantity: Mapped[Optional[int]] = mapped_column(nullable=True)

    # ForeignKeys
    repair_order_id: Mapped[int] = mapped_column(ForeignKey("repairs_orders.id"), nullable=False)
    spare_part_id: Mapped[int] = mapped_column(ForeignKey("spare_parts.id"), nullable=False)

    # Relationships
    repair_order: Mapped["RepairOrder"] = relationship("RepairOrder", back_populates="order_spare_parts")
    spare_part: Mapped["SparePart"] = relationship("SparePart", back_populates="order_spare_parts")  # Corregido singular

# =========================================================================
# TABLE SERVICES TYPES
# =========================================================================

class ServiceType(Base):
    __tablename__ = "service_types"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    order_services: Mapped[List["OrderService"]] = relationship("OrderService", back_populates="service_type")

# =========================================================================
# TABLE ORDER SERVICES
# =========================================================================

class OrderService(Base):
    __tablename__ = "order_services"

    # Table Columns
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ForeignKeys
    repair_order_id: Mapped[int] = mapped_column(ForeignKey("repairs_orders.id"), nullable=False)
    service_type_id: Mapped[int] = mapped_column(ForeignKey("service_types.id"), nullable=False)

    # Relationships
    repair_order: Mapped["RepairOrder"] = relationship("RepairOrder", back_populates="order_services")
    service_type: Mapped["ServiceType"] = relationship("ServiceType", back_populates="order_services")

# =========================================================================
# TABLE STORAGE
# =========================================================================

class Storage(Base):
    __tablename__ = "storage"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entry_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    column: Mapped[str] = mapped_column(String(3), nullable=False)

    # ForeignKeys
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="storage")
