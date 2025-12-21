from sqlalchemy import Column, Integer, String, Boolean, Float
from database import Base

# Table 1: Menu Items
class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)            # e.g., "Cheese Burger"
    price = Column(Float)                        # e.g., 150.0
    category = Column(String)                    # e.g., "Starters"
    is_available = Column(Boolean, default=True) # Out of Stock toggle

# Table 2: Orders
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(Integer)               # e.g., 5
    status = Column(String, default="Pending")   # Pending -> Cooking -> Served
    total_amount = Column(Float, default=0.0)    # e.g., 450.0
    items_summary = Column(String)               # e.g., "2x Burger, 1x Coke"