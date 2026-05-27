from typing import Any, List, Optional

from pydantic import BaseModel, Field


class OrderItemSchema(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0)
    modifiers: Optional[List[dict[str, Any]]] = None


class OrderCreate(BaseModel):
    table_number: int
    items: List[OrderItemSchema]
    order_type: str = "Dine-in"
    customer_phone: Optional[str] = None
    taken_by: str = "Customer"
    covers: int = 0


class OrderStatusUpdate(BaseModel):
    status: str


class CustomerCreate(BaseModel):
    name: Optional[str] = None
    phone: str
    relation: str = "Regular"
    discount_percent: float = 0.0


class AvailabilityUpdate(BaseModel):
    is_available: bool


class MenuItemCreate(BaseModel):
    name: str
    price: float = Field(ge=0)
    category: str = "General"
    description: str = ""
    image_url: str = ""
    is_veg: bool = True
    gst_rate: float = 5.0
    hsn_code: str = ""
    hindi_name: str = ""


class InventoryCreate(BaseModel):
    item_name: str


class IngredientCreate(BaseModel):
    name: str
    unit: str = "pieces"
    current_stock: float = 0.0
    min_stock_alert: float = 0.0


class CheckoutSchema(BaseModel):
    order_id: int
    payment_method: str
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    customer_discount: Optional[float] = None
    save_customer: bool = False


class TableUpdate(BaseModel):
    covers: Optional[int] = None
    status: Optional[str] = None


class TableTransfer(BaseModel):
    from_table: int
    to_table: int


class TableMerge(BaseModel):
    source_table: int
    target_table: int


class SplitBillRequest(BaseModel):
    order_id: int
    split_type: str = "equal"
    split_count: int = 1
    item_ids: Optional[List[int]] = None


class StaffCreate(BaseModel):
    username: str
    password: str
    role: str


class RestaurantCreate(BaseModel):
    restaurant_name: str
    slug: str
    owner_username: str
    owner_password: str = ""
    address: str = ""
    phone: str = ""
    table_count: int = 10
    plan: str = "trial"
    gst_rate: float = 5.0
    owner_email: str = ""


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None
    plan: Optional[str] = None
    plan_expires_at: Optional[str] = None
    table_count: Optional[int] = None
    gst_rate: Optional[float] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    owner_email: Optional[str] = None
    menu_pdf_url: Optional[str] = None
    currency_symbol: Optional[str] = None


class RestaurantSettingsUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    logo_url: Optional[str] = None
    table_count: Optional[int] = None
    gst_rate: Optional[float] = None
    menu_pdf_url: Optional[str] = None
    currency_symbol: Optional[str] = None
    gstin: Optional[str] = None
    upi_id: Optional[str] = None
