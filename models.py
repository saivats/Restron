from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
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

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(Integer)
    status = Column(String, default="Pending")
    total_amount = Column(Float, default=0.0)
    items_summary = Column(String)
    order_type = Column(String, default="Dine-in")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# --- THIS IS THE MISSING TABLE ---
class InventoryRequest(Base):
    __tablename__ = "inventory_requests"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)