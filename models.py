from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime


class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    category = Column(String)
    description = Column(String, default="")
    image_url = Column(String, default="")
    is_available = Column(Boolean, default=True)
    is_veg = Column(Boolean, default=True)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True, index=True)
    relation = Column(String, default="Regular")  # e.g. "Owner Friend", "VIP"
    discount_percent = Column(Float, default=0.0)  # e.g. 5.0 for 5%
    visit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(Integer)
    status = Column(String, default="Pending")

    # Financials
    subtotal = Column(Float, default=0.0)  # Price before discount
    discount_applied = Column(Float, default=0.0)  # Amount subtracted
    total_amount = Column(Float, default=0.0)  # Final price

    items_summary = Column(String)
    order_type = Column(String, default="Dine-in")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Link to Customer (Optional, can be null if guest)
    customer_phone = Column(String, ForeignKey("customers.phone"), nullable=True)

    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    item_name = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    is_veg = Column(Boolean, default=True)
    category = Column(String, default="General")

    order = relationship("Order", back_populates="items")


class InventoryRequest(Base):
    __tablename__ = "inventory_requests"
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)