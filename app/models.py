from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

# =========================================================================
# TABLE CLIENTS
# =========================================================================

class Client(Base):
    __tablename__ = "clients"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    national_id_type = Column(String(2), nullable=False)
    national_id = Column(String(15), nullable=False)
    name = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=True)
    mail = Column(String(50), nullable=True)
    short_address = Column(String(50), nullable=True)

    #Relationships
    devices = relationship("Device", back_populates="client")
    repairs_orders = relationship("RepairOrder", back_populates="client")

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
    serial_number = Column(String(30), nullable=False)

    #ForeingKeys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    #Relationships
    client = relationship("Client", back_populates="devices")
    repairs_orders = relationship("RepairOrder", back_populates="device")

# =========================================================================
# TABLE EMPLOYEE DIRECTORY
# =========================================================================

class EmployeeDirectory(Base):
    __tablename__ = "employee_directory"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(80), nullable=False)
    national_id = Column(String(12), nullable=False)
    tax_id = Column(String(11), nullable=False)
    short_address = Column(String(30), nullable=False)
    occupation = Column(String(30), nullable=False)
    employee_code = Column(String(15), nullable=False)
    entry_date = Column(Date, nullable=False)
    tax_id_doc = Column(String(150), nullable=True)
    national_id_doc = Column(String(150), nullable=True)
    profile_photo = Column(String(150), nullable=True)

    #Relationships
    technicals = relationship("Technical", back_populates="employee")
    attendances = relationship("Attendance", back_populates="employee")

# =========================================================================
# TABLE TECHNICALS
# =========================================================================

class Technical(Base):
    __tablename__ = "technicals"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    commission = Column(Integer, nullable=True)

    #ForeingKeys
    employee_id = Column(Integer, ForeignKey("employee_directory.id"), nullable=False)

    #Relationships
    employee = relationship("EmployeeDirectory", back_populates="technicals")
    repairs_orders = relationship("RepairOrder", back_populates="technical")

# =========================================================================
# TABLE REPAIRS ORDERS
# =========================================================================

class RepairOrder(Base):
    __tablename__ = "repairs_orders"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entry_date = Column(Date, nullable=False)
    status = Column(String(30), default="Pendiente", nullable=False)
    exit_date = Column(Date, nullable=True)
    agreed_price = Column(Integer, nullable=True)

    #ForeingKeys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    technical_id = Column(Integer, ForeignKey("technicals.id"), nullable=False)

    #Relationships
    client = relationship("Client", back_populates="repairs_orders")
    device = relationship("Device", back_populates="repairs_orders")
    order_spare_parts = relationship("OrderSparePart", back_populates="repair_order")
    order_services = relationship("OrderService", back_populates="repair_order")
    technical = relationship("Technical", back_populates="repairs_orders")

# =========================================================================
# TABLE SPARE PARTS
# =========================================================================

class SparePart(Base):
    __tablename__ = "spare_parts"

    #Table Columns
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(30), nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    price = Column(Integer, nullable=True)

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
    price = Column(Integer, nullable=True)

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