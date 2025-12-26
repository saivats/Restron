from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from pydantic import BaseModel
from typing import List, Optional
from database import engine, SessionLocal
from passlib.context import CryptContext
from datetime import timedelta, datetime
from jose import jwt, JWTError
import models
import os
from reportlab.pdfgen import canvas
from io import BytesIO
from supabase import create_client, Client

# --- 🔐 CONFIGURATION (UPDATE THESE!) ---
# 1. JWT Security Config
SECRET_KEY = "desi-zaika-super-secret-key-2025"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 720  # 12 Hours

# 2. Supabase Storage Config (Get these from Supabase -> Settings -> API)
SUPABASE_URL = "https://jzuvinbqupubrcwbcqxn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp6dXZpbmJxdXB1YnJjd2JjcXhuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NjczNzQxMiwiZXhwIjoyMDgyMzEzNDEyfQ.1Ymb_brCBrwF5NFfxwlbO4UToE2diiLQ3S8cMR53_zU"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- APP SETUP ---
# Create Database Tables if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Desi Zaika OS - Cloud Edition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- DATABASE DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- DATA SCHEMAS ---
class OrderItemSchema(BaseModel):
    menu_item_id: int
    quantity: int


class OrderCreate(BaseModel):
    table_number: int
    items: List[OrderItemSchema]
    order_type: str = "Dine-in"
    customer_phone: Optional[str] = None
    taken_by: str = "Customer"


class CustomerCreate(BaseModel):
    name: str
    phone: str
    relation: str = "Regular"
    discount_percent: float = 0.0


class AvailabilityUpdate(BaseModel):
    is_available: bool


class InventoryCreate(BaseModel):
    item_name: str


# --- 🔐 AUTH FUNCTIONS ---
def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token: return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: return None
    except JWTError:
        return None

    user = db.query(models.User).filter(models.User.username == username).first()
    return user


# --- PAGES (PROTECTED & PUBLIC) ---
@app.get("/")
def home(): return RedirectResponse("/login")


@app.get("/login")
def login_page(): return FileResponse("static/login.html")


@app.get("/mobile")
def mobile_menu(): return FileResponse("static/menu.html")


@app.get("/kitchen")
def kitchen_page(): return FileResponse("static/kitchen.html")


@app.get("/waiter")
def waiter_page(user: models.User = Depends(get_current_user)):
    if not user or user.role not in ["waiter", "manager", "owner"]: return RedirectResponse("/login")
    return FileResponse("static/waiter.html")


@app.get("/manager")
def manager_page(user: models.User = Depends(get_current_user)):
    if not user or user.role not in ["manager", "owner"]: return RedirectResponse("/login")
    return FileResponse("static/manager.html")


@app.get("/owner")
def owner_page(user: models.User = Depends(get_current_user)):
    if not user or user.role != "owner": return RedirectResponse("/login")
    return FileResponse("static/owner.html")


# --- 🔐 SECURE LOGIN API ---
@app.post("/token")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username, "role": user.role},
                                       expires_delta=access_token_expires)

    # Store secure JWT in HttpOnly cookie
    response.set_cookie(key="access_token", value=access_token, httponly=True)

    redirect_url = "/mobile"
    if user.role == "owner":
        redirect_url = "/owner"
    elif user.role == "manager":
        redirect_url = "/manager"
    elif user.role == "waiter":
        redirect_url = "/waiter"

    return {"access_token": access_token, "token_type": "bearer", "redirect": redirect_url}


@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "Logged out"}


# --- 🧾 CLOUD RECEIPT GENERATOR ---
@app.get("/receipt/{order_id}")
def generate_receipt(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order: raise HTTPException(404, "Order not found")

    # 1. Generate PDF in Memory
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(200, 500))

    c.setFont("Helvetica-Bold", 12);
    c.drawString(50, 480, "DESI ZAIKA")
    c.setFont("Helvetica", 10);
    c.drawString(40, 465, "Est. 1947 - Ghaziabad")
    c.line(10, 455, 190, 455)

    y = 430
    c.drawString(10, y, f"Order #{order.id} | Table: {order.table_number}")
    y -= 20
    c.drawString(10, y, f"Date: {order.created_at.strftime('%d-%m-%Y %H:%M')}")
    y -= 20
    c.line(10, y, 190, y);
    y -= 20

    items = db.query(models.OrderItem).filter(models.OrderItem.order_id == order.id).all()
    for item in items:
        c.drawString(10, y, f"{item.quantity} x {item.item_name[:20]}")
        c.drawRightString(180, y, f"{item.price * item.quantity}")
        y -= 15
        if y < 50: c.showPage(); y = 480

    c.line(10, y, 190, y);
    y -= 20
    c.setFont("Helvetica-Bold", 10);
    c.drawString(10, y, "Subtotal:");
    c.drawRightString(180, y, f"Rs {order.subtotal}");
    y -= 15
    if order.discount_applied > 0:
        c.drawString(10, y, "Discount:");
        c.drawRightString(180, y, f"- Rs {order.discount_applied}");
        y -= 15

    c.setFont("Helvetica-Bold", 14);
    c.drawString(10, y - 10, "TOTAL:");
    c.drawRightString(180, y - 10, f"Rs {order.total_amount}")
    c.save()

    buffer.seek(0)

    # 2. Upload to Supabase Storage
    filename = f"receipt_{order_id}.pdf"
    bucket_name = "receipts"

    try:
        supabase.storage.from_(bucket_name).upload(
            file=buffer.getvalue(),
            path=filename,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )

        # 3. Get Public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(filename)

        # 4. Create WhatsApp Link
        msg = f"Thank you for dining at Desi Zaika! Here is your bill: {public_url}"
        whatsapp_url = f"https://wa.me/?text={msg}"

        return {"pdf_url": public_url, "whatsapp_url": whatsapp_url}

    except Exception as e:
        print(f"Upload Error: {e}")
        # Fallback: If upload fails, try to return a local error or retry
        raise HTTPException(500, f"Failed to upload receipt to cloud: {str(e)}")


# --- STANDARD API ROUTES ---
@app.get("/menu/")
def read_menu(db: Session = Depends(get_db)):
    return db.query(models.MenuItem).all()


@app.post("/menu/")
def create_item(name: str, price: float, category: str, db: Session = Depends(get_db)):
    db.add(models.MenuItem(name=name, price=price, category=category))
    db.commit()
    return {"status": "Added"}


@app.delete("/menu/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db.query(models.MenuItem).filter(models.MenuItem.id == item_id).delete()
    db.commit()
    return {"status": "Deleted"}


@app.put("/menu/{item_id}/availability")
def toggle_stock(item_id: int, s: AvailabilityUpdate, db: Session = Depends(get_db)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if item:
        item.is_available = s.is_available
        db.commit()
    return {"status": "Updated"}


@app.post("/order/")
def place_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    subtotal = 0.0
    discount_amount = 0.0
    summary_list = []

    item_details = []
    for item in order_data.items:
        menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
        if not menu_item: continue
        cost = menu_item.price * item.quantity
        subtotal += cost
        summary_list.append(f"{item.quantity}x {menu_item.name}")
        item_details.append({
            "name": menu_item.name, "qty": item.quantity, "price": menu_item.price,
            "veg": menu_item.is_veg, "cat": menu_item.category
        })

    if order_data.customer_phone:
        customer = db.query(models.Customer).filter(models.Customer.phone == order_data.customer_phone).first()
        if customer:
            if customer.discount_percent > 0:
                discount_amount = (subtotal * customer.discount_percent) / 100
            customer.visit_count += 1
            db.add(customer)

    final_total = subtotal - discount_amount

    new_order = models.Order(
        table_number=order_data.table_number,
        order_type=order_data.order_type,
        status="Pending",
        subtotal=subtotal,
        discount_applied=discount_amount,
        total_amount=final_total,
        items_summary=", ".join(summary_list),
        customer_phone=order_data.customer_phone,
        taken_by=order_data.taken_by
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for d in item_details:
        db.add(models.OrderItem(order_id=new_order.id, item_name=d['name'], quantity=d['qty'], price=d['price'],
                                is_veg=d['veg'], category=d['cat']))

    db.commit()
    return {"status": "Placed", "id": new_order.id, "discount": discount_amount}


@app.get("/kitchen-display/")
def kitchen_view(db: Session = Depends(get_db)):
    return db.query(models.Order).filter(models.Order.status == "Pending").all()


@app.post("/order/{order_id}/done")
def mark_done(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order: order.status = "Completed"; db.commit()
    return {"status": "Done"}


@app.get("/manager/orders/")
def manager_orders(db: Session = Depends(get_db)):
    active = db.query(models.Order).filter(models.Order.status == "Pending").all()
    history = db.query(models.Order).filter(models.Order.status != "Pending").order_by(
        desc(models.Order.created_at)).limit(20).all()
    return {"active": active, "history": history}


# --- CUSTOMER CRM ---
@app.post("/customers/")
def add_customer(c: CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Customer).filter(models.Customer.phone == c.phone).first()
    if existing:
        existing.name = c.name
        existing.relation = c.relation
        existing.discount_percent = c.discount_percent
        db.commit()
        return {"status": "Updated", "name": c.name}
    else:
        new_cust = models.Customer(name=c.name, phone=c.phone, relation=c.relation, discount_percent=c.discount_percent)
        db.add(new_cust)
        db.commit()
        return {"status": "Created", "name": c.name}


@app.get("/customers/")
def get_customers(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Customer)
    if search: query = query.filter(models.Customer.phone.contains(search) | models.Customer.name.contains(search))
    return query.limit(50).all()


# --- INVENTORY ---
@app.post("/inventory/")
def add_inv(req: InventoryCreate, db: Session = Depends(get_db)):
    db.add(models.InventoryRequest(item_name=req.item_name));
    db.commit()
    return {"status": "OK"}


@app.get("/inventory/")
def get_inv(db: Session = Depends(get_db)): return db.query(models.InventoryRequest).all()


@app.delete("/inventory/")
def clear_inv(db: Session = Depends(get_db)):
    db.query(models.InventoryRequest).delete();
    db.commit()
    return {"status": "Cleared"}


# --- OWNER ANALYTICS ---
@app.get("/owner/analytics/")
def owner_analytics(db: Session = Depends(get_db)):
    now = datetime.datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    def get_rev(date_limit):
        return db.query(func.sum(models.Order.total_amount)).filter(
            models.Order.created_at >= date_limit).scalar() or 0.0

    best_sellers_month = db.query(models.OrderItem.item_name,
                                  func.sum(models.OrderItem.quantity).label('total_qty')).join(models.Order).filter(
        models.Order.created_at >= month_start).group_by(models.OrderItem.item_name).order_by(desc('total_qty')).limit(
        5).all()
    total_rev_month = get_rev(month_start)
    total_orders_month = db.query(models.Order).filter(models.Order.created_at >= month_start).count()
    aov = round(total_rev_month / total_orders_month, 2) if total_orders_month > 0 else 0
    peak_hours = db.query(extract('hour', models.Order.created_at).label('h'),
                          func.count(models.Order.id).label('cnt')).group_by('h').order_by(desc('cnt')).limit(3).all()

    return {
        "revenue": {"today": get_rev(today_start), "week": get_rev(week_start), "month": total_rev_month,
                    "total": db.query(func.sum(models.Order.total_amount)).scalar() or 0.0},
        "best_sellers_month": [{"name": b[0], "qty": b[1]} for b in best_sellers_month],
        "advanced": {"aov": aov, "peak_hours": [{"hour": h[0], "count": h[1]} for h in peak_hours]}
    }


@app.get("/owner/history/")
def get_history(date: Optional[str] = None, month: Optional[str] = None, db: Session = Depends(get_db)):
    start_dt = None;
    end_dt = None
    if date:
        start_dt = datetime.datetime.strptime(date, "%Y-%m-%d"); end_dt = start_dt + timedelta(days=1)
    elif month:
        y, m = map(int, month.split('-')); import calendar; start_dt = datetime.datetime(y, m, 1); last = \
        calendar.monthrange(y, m)[1]; end_dt = datetime.datetime(y, m, last) + timedelta(days=1)
    else:
        raise HTTPException(400, "Date needed")

    revenue = db.query(func.sum(models.Order.total_amount)).filter(models.Order.created_at >= start_dt,
                                                                   models.Order.created_at < end_dt).scalar() or 0.0
    veg_count = db.query(func.sum(models.OrderItem.quantity)).join(models.Order).filter(
        models.Order.created_at >= start_dt, models.Order.created_at < end_dt,
        models.OrderItem.is_veg == True).scalar() or 0
    non_veg_count = db.query(func.sum(models.OrderItem.quantity)).join(models.Order).filter(
        models.Order.created_at >= start_dt, models.Order.created_at < end_dt,
        models.OrderItem.is_veg == False).scalar() or 0
    all_items = db.query(models.OrderItem.item_name, func.sum(models.OrderItem.quantity).label("qty")).join(
        models.Order).filter(models.Order.created_at >= start_dt, models.Order.created_at < end_dt).group_by(
        models.OrderItem.item_name).order_by(desc("qty")).all()

    detailed_logs = []
    if date:
        orders = db.query(models.Order).filter(models.Order.created_at >= start_dt,
                                               models.Order.created_at < end_dt).order_by(
            desc(models.Order.created_at)).all()
        for o in orders: detailed_logs.append(
            {"id": o.id, "time": o.created_at.strftime("%I:%M %p"), "type": o.order_type, "table": o.table_number,
             "items": o.items_summary, "total": o.total_amount, "taken_by": o.taken_by})

    return {"revenue": revenue, "veg_sold": veg_count, "non_veg_sold": non_veg_count,
            "items": [{"name": i[0], "qty": i[1]} for i in all_items], "detailed_logs": detailed_logs}