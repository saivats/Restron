from datetime import timezone
import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


def utc_now():
    return datetime.datetime.now(timezone.utc)


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Restron POS")
    slug = Column(String, unique=True, index=True, nullable=True)
    owner_email = Column(String, nullable=True)
    address = Column(String, default="")
    phone = Column(String, default="")
    gstin = Column(String, default="")
    logo_url = Column(String, default="")
    table_count = Column(Integer, default=10)
    gst_rate = Column(Float, default=5.0)
    currency_symbol = Column(String, default="₹")
    timezone = Column(String, default="Asia/Kolkata")
    currency = Column(String, default="INR")
    plan_id = Column(String, default="free")
    plan = Column(String, default="trial")
    plan_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    upi_id = Column(String, default="")
    menu_pdf_url = Column(String, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geofence_radius_meters = Column(Integer, default=50)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class SuperAdmin(Base):
    __tablename__ = "superadmins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, index=True)
    is_active = Column(Boolean, default=True, nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("restaurant_id", "role", "permission", name="uq_role_permission"),)

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    role = Column(String, index=True, nullable=False)
    permission = Column(String, index=True, nullable=False)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    name = Column(String, index=True)
    hindi_name = Column(String, default="")
    price = Column(Float)
    category = Column(String, index=True)
    description = Column(String, default="")
    image_url = Column(String, default="")
    is_available = Column(Boolean, default=True)
    is_veg = Column(Boolean, default=True)
    gst_rate = Column(Float, default=5.0)
    hsn_code = Column(String, default="")


class ItemModifier(Base):
    __tablename__ = "item_modifiers"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    modifier_type = Column(String, default="addon")
    price_delta = Column(Float, default=0.0)
    percent_delta = Column(Float, default=0.0)
    is_available = Column(Boolean, default=True)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("phone", "restaurant_id", name="uq_customer_phone_restaurant"),)

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    name = Column(String, nullable=True)
    phone = Column(String, index=True)
    relation = Column(String, default="Regular")
    discount_percent = Column(Float, default=0.0)
    visit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)


class Table(Base):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("restaurant_id", "table_number", name="uq_restaurant_table"),)

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    table_number = Column(Integer, index=True)
    name = Column(String, default="")
    status = Column(String, default="Available", index=True)
    covers = Column(Integer, default=0)
    merged_into_table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    active_order_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    table_number = Column(Integer, index=True)
    status = Column(String, default="KOT_SENT", index=True)
    kot_number = Column(String, nullable=True, index=True)
    invoice_number = Column(String, nullable=True, index=True)
    subtotal = Column(Float, default=0.0)
    discount_applied = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    gst_amount = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    gst_breakdown = Column(JSON, nullable=True)
    total_amount = Column(Float, default=0.0)
    items_summary = Column(String)
    order_type = Column(String, default="Dine-in")
    customer_phone = Column(String, ForeignKey("customers.phone"), nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    archived = Column(Boolean, default=False, index=True)
    taken_by = Column(String, default="Customer")
    payment_method = Column(String, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    table_status = Column(String, default="Occupied")

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


Index("ix_orders_restaurant_status_created", Order.restaurant_id, Order.status, Order.created_at)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True, index=True)
    item_name = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    line_total = Column(Float, default=0.0)
    gst_rate = Column(Float, default=5.0)
    hsn_code = Column(String, default="")
    modifiers_json = Column(JSON, nullable=True)
    is_veg = Column(Boolean, default=True)
    category = Column(String, default="General")

    order = relationship("Order", back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    financial_year = Column(String, index=True)
    sequence_number = Column(Integer)
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    payment_method = Column(String, default="")
    created_at = Column(DateTime, default=utc_now, nullable=False)


class SplitBill(Base):
    __tablename__ = "split_bills"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)
    split_type = Column(String, default="equal")
    receipt_number = Column(String, index=True)
    payer_label = Column(String, default="")
    items_json = Column(JSON, nullable=True)
    amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)


class InventoryRequest(Base):
    __tablename__ = "inventory_requests"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    item_name = Column(Text)
    archived = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=utc_now)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    name = Column(String, index=True, nullable=False)
    unit = Column(String, default="pieces")
    current_stock = Column(Float, default=0.0)
    min_stock_alert = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), index=True)
    quantity = Column(Float, default=0.0)


class StockEntry(Base):
    __tablename__ = "stock_entries"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), index=True)
    quantity = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    supplier = Column(String, default="")
    created_at = Column(DateTime, default=utc_now)


class WastageLog(Base):
    __tablename__ = "wastage_logs"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), index=True)
    quantity = Column(Float, default=0.0)
    reason = Column(String, default="")
    created_at = Column(DateTime, default=utc_now)


class WhatsAppDelivery(Base):
    __tablename__ = "whatsapp_deliveries"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True)
    phone = Column(String, index=True)
    status = Column(String, default="pending", index=True)
    attempts = Column(Integer, default=0)
    last_error = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, index=True, nullable=False)
    entity_type = Column(String, index=True, nullable=False)
    entity_id = Column(String, index=True, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)
