from sqlalchemy import Column, Integer, Float, String, Boolean, Date, DateTime, ForeignKey
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app import Base

# =========================================================================
# TABLE CLIENTS
# =========================================================================

class Client(Base):
    __tablename__ = "clients"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    national_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    mail = Column(String(100), unique=True, nullable=True)
    short_address = Column(String(50), nullable=True)

    #Relationships
    devices = relationship("Device", back_populates="client")
    repairs_orders = relationship("RepairOrder", back_populates="client")
    user = relationship("User", back_populates="client")

# =========================================================================
# TABLE DEVICES
# =========================================================================

class Device(Base):
    __tablename__ = "devices"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_type = Column(String(20), nullable=False)
    brand = Column(String(30), nullable=False)
    model = Column(String(30), nullable=False)
    serial_number = Column(String(30), unique=True, nullable=False)

    #ForeingKeys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    #Relationships
    client = relationship("Client", back_populates="devices")
    repairs_orders = relationship("RepairOrder", back_populates="device")
    storage = relationship("Storage", back_populates="device")

# =========================================================================
# TABLE TECHNICIANS
# =========================================================================

class Technician(Base):
    __tablename__ = "technicians"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    commission = Column(Integer, nullable=True)

    #ForeingKeys
    employee_id = Column(Integer, ForeignKey("employee_directory.id"), nullable=False)

    #Relationships
    employee = relationship("EmployeeDirectory", back_populates="technicians")
    repairs_orders = relationship("RepairOrder", back_populates="technician")

# =========================================================================
# TABLE REPAIRS ORDERS
# =========================================================================

class RepairOrder(Base):
    __tablename__ = "repairs_orders"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entry_date = Column(Date, nullable=False)
    is_warranty = Column(Boolean, default=False)
    status = Column(String(30), default="Pendiente", nullable=False)
    exit_date = Column(Date, nullable=True)
    agreed_price = Column(Float, nullable=True)

    #ForeingKeys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)

    #Relationships
    client = relationship("Client", back_populates="repairs_orders")
    device = relationship("Device", back_populates="repairs_orders")
    order_spare_parts = relationship("OrderSparePart", back_populates="repair_order")
    order_services = relationship("OrderService", back_populates="repair_order")
    technician = relationship("Technician", back_populates="repairs_orders")

# =========================================================================
# TABLE SPARE PARTS
# =========================================================================

class SparePart(Base):
    __tablename__ = "spare_parts"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    component_type = Column(String(50), nullable=True)
    brand = Column(String(50), nullable=True) 
    stock = Column(Integer, default=0)
    price = Column(Float, nullable=True)

    #Relationships
    order_spare_parts = relationship("OrderSparePart", back_populates="spare_part")

# =========================================================================
# TABLE ORDER SPARE PARTS
# =========================================================================

class OrderSparePart(Base):
    __tablename__ = "order_spare_parts"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quantity = Column(Integer, nullable=True)

    #ForeingKeys
    repair_order_id = Column(Integer, ForeignKey("repairs_orders.id"), nullable=False)
    spare_part_id = Column(Integer, ForeignKey("spare_parts.id"), nullable=False)

    #Relationships
    repair_order = relationship("RepairOrder", back_populates="order_spare_parts")
    spare_part = relationship("SparePart", back_populates="order_spare_parts")

# =========================================================================
# TABLE SERVICES TYPES
# =========================================================================

class ServiceType(Base):
    __tablename__ = "service_types"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=True)

    #Relationships
    order_services = relationship("OrderService", back_populates="service_type")

# =========================================================================
# TABLE ORDER SERVICES
# =========================================================================

class OrderService(Base):
    __tablename__ = "order_services"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    #ForeingKeys
    repair_order_id = Column(Integer, ForeignKey("repairs_orders.id"), nullable=False)
    service_types_id = Column(Integer, ForeignKey("service_types.id"), nullable=False)

    #Relationships
    repair_order = relationship("RepairOrder", back_populates="order_services")
    service_type = relationship("ServiceType", back_populates="order_services")

# =========================================================================
# TABLE STORAGE
# =========================================================================

class Storage(Base):
    __tablename__ = "storage"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entry_date = Column(Date, nullable=False)
    column = Column(String(3), nullable=False)

    #ForeingKeys
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    #Relationships
    device = relationship("Device", back_populates="storage")