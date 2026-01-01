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
from dotenv import load_dotenv

# --- 🔒 SECURITY CONFIGURATION ---
# Load environment variables from .env file
load_dotenv()

# 1. JWT Security Config
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10  # 10 Minutes Session Limit

# 2. Supabase Storage Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase Client
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("⚠️ WARNING: Supabase credentials missing in .env. Receipt upload will fail.")
    supabase = None

# --- APP SETUP ---
# Create Database Tables if they don't exist (non-blocking)
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ Database connection successful - Tables ready")
except Exception as e:
    print(f"⚠️ WARNING: Database connection failed at startup: {e}")
    print("⚠️ App will start, but database operations may fail until connection is restored")
    print("⚠️ Tables will be created automatically on first successful connection")

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
        # Try to create tables if they don't exist (lazy initialization)
        try:
            models.Base.metadata.create_all(bind=engine)
        except Exception:
            pass  # Tables might already exist or DB might be temporarily unavailable
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
def kitchen_page(user: models.User = Depends(get_current_user)):
    if not user or user.role not in ["owner", "manager", "waiter", "chef"]:
        return RedirectResponse("/login")
    return FileResponse("static/kitchen.html")


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
    try:
        order = db.query(models.Order).filter(models.Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # 1. Generate PDF in Memory (80mm thermal receipt width = 227 points)
        buffer = BytesIO()
        # Use Letter size and adjust layout - better for viewing on screens
        c = canvas.Canvas(buffer, pagesize=(227, 900))  # Increased height for better spacing

        y = 880

        # Premium Header with decorative box
        c.setLineWidth(2.5)
        c.rect(8, y-50, 211, 45, stroke=1, fill=0)
        # Decorative corner elements
        c.setLineWidth(1)
        c.line(8, y-5, 18, y-5)
        c.line(8, y-5, 8, y-15)
        c.line(219, y-5, 209, y-5)
        c.line(219, y-5, 219, y-15)
        c.line(8, y-50, 18, y-50)
        c.line(8, y-50, 8, y-40)
        c.line(219, y-50, 209, y-50)
        c.line(219, y-50, 219, y-40)
        y -= 12

        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(113, y, "DESI ZAIKA")
        y -= 16
        c.setFont("Helvetica", 10)
        c.drawCentredString(113, y, "Authentic Flavors")
        y -= 12
        c.setFont("Helvetica", 8)
        c.drawCentredString(113, y, "Ghaziabad")
        y -= 25

        # Tax Invoice Header with decorative lines
        c.setLineWidth(1)
        c.line(10, y, 217, y)
        y -= 8
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(113, y, "TAX INVOICE")
        y -= 8
        c.line(10, y, 217, y)
        y -= 18

        # Order Details in box format
        c.setFont("Helvetica", 9)
        c.drawString(12, y, f"Order Number: #{order.id}")
        table_text = f"Table: {order.table_number}" if order.order_type == "Dine-in" else f"{order.order_type} Order"
        c.drawRightString(215, y, table_text)
        y -= 14
        c.drawString(12, y, f"Date: {order.created_at.strftime('%d %B %Y')}")
        c.drawRightString(215, y, f"Time: {order.created_at.strftime('%I:%M %p')}")
        y -= 20

        # Items Section Header with double line
        c.setLineWidth(1.5)
        c.line(10, y, 217, y)
        y -= 2
        c.line(10, y, 217, y)
        y -= 12
        c.setFont("Helvetica-Bold", 9)
        c.drawString(12, y, "ITEM DESCRIPTION")
        c.drawString(140, y, "QTY")
        c.drawRightString(215, y, "AMOUNT")
        y -= 3
        c.setLineWidth(1.5)
        c.line(10, y, 217, y)
        y -= 12

        # Items List
        c.setFont("Helvetica", 9)
        items = db.query(models.OrderItem).filter(models.OrderItem.order_id == order.id).all()
        for item in items:
            # Better item name truncation with proper spacing
            item_name = item.item_name[:20] if len(item.item_name) > 20 else item.item_name
            # Draw item name (left aligned)
            c.drawString(12, y, item_name)
            # Draw quantity (centered in QTY column)
            qty_width = c.stringWidth(str(item.quantity), "Helvetica", 9)
            c.drawString(145 + (25 - qty_width)/2, y, str(item.quantity))
            # Draw amount (right aligned)
            amount = item.price * item.quantity
            c.drawRightString(215, y, f"₹{amount:.2f}")
            y -= 16  # Increased spacing between items
            if y < 150: 
                c.showPage() 
                y = 880

        y -= 5
        c.setLineWidth(1.5)
        c.line(10, y, 217, y)
        y -= 18

        # Bill Summary with proper alignment
        c.setFont("Helvetica", 9)
        c.drawRightString(150, y, "Subtotal:")
        c.drawRightString(215, y, f"₹{order.subtotal:.2f}")
        y -= 14

        if order.discount_applied > 0:
            discount_pct = (order.discount_applied / order.subtotal * 100) if order.subtotal > 0 else 0
            c.drawRightString(150, y, f"Discount ({discount_pct:.0f}%):")
            c.drawRightString(215, y, f"-₹{order.discount_applied:.2f}")
            y -= 3
            c.setLineWidth(0.5)
            c.line(140, y, 215, y)
            y -= 12
            c.drawRightString(150, y, "Subtotal after disc:")
            c.drawRightString(215, y, f"₹{order.subtotal - order.discount_applied:.2f}")
            y -= 14

        c.drawRightString(150, y, "GST @ 5%:")
        c.drawRightString(215, y, f"₹{order.gst_amount:.2f}")
        y -= 5

        # Double line before total
        c.setLineWidth(1.5)
        c.line(10, y, 217, y)
        y -= 2
        c.line(10, y, 217, y)
        y -= 16

        c.setFont("Helvetica-Bold", 13)
        c.drawRightString(150, y, "GRAND TOTAL:")
        c.drawRightString(215, y, f"₹{order.total_amount:.2f}")
        y -= 5
        c.setLineWidth(1.5)
        c.line(10, y, 217, y)
        y -= 18

        # Payment Info
        c.setFont("Helvetica", 9)
        if order.payment_method:
            c.drawString(12, y, f"Payment Method: {order.payment_method.upper()}")
            if order.paid_at:
                c.drawRightString(215, y, f"Payment Time: {order.paid_at.strftime('%I:%M %p')}")
            y -= 18

        # Savings Message with decorative box
        if order.discount_applied > 0:
            c.setLineWidth(1)
            c.rect(12, y-12, 193, 14, stroke=1, fill=0)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(113, y-2, f" You saved ₹{order.discount_applied:.2f} with your VIP discount!")
            y -= 22

        # Footer with decorative lines
        c.setLineWidth(1.5)
        c.line(10, y, 217, y)
        y -= 2
        c.line(10, y, 217, y)
        y -= 14
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(113, y, "Thank you for your visit!")
        y -= 12
        c.setFont("Helvetica", 9)
        c.drawCentredString(113, y, "Please come again")
        y -= 18
        c.setLineWidth(1.5)
        c.line(10, y, 217, y)
        y -= 12

        # Contact Info
        c.setFont("Helvetica", 7)
        c.drawCentredString(113, y, "Shop No. 46-47, 3rd Floor Food Court,")
        y -= 9
        c.drawCentredString(113, y, "Wave Galleria Shopping Complex, Wave City, Ghaziabad")
        y -= 9
        c.drawCentredString(113, y, "Call Us: +91 7683017632")
        y -= 12

        # Final decorative double line
        c.setLineWidth(2)
        c.line(10, y, 217, y)
        y -= 2
        c.line(10, y, 217, y)

        c.save()

        buffer.seek(0)

        # 2. Upload to Supabase Storage
        filename = f"receipt_{order_id}.pdf"
        bucket_name = "receipts"

        if not supabase: raise Exception("Supabase not configured")

        supabase.storage.from_(bucket_name).upload(
            file=buffer.getvalue(),
            path=filename,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )

        # 3. Get Public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(filename)

        # 4. Get Menu PDF URL
        menu_url = "https://jzuvinbqupubrcwbcqxn.supabase.co/storage/v1/object/public/menu/Desi%20Zaika.pdf"

        # 5. Create WhatsApp message (will be formatted by frontend with customer phone)
        return {
            "pdf_url": public_url,
            "menu_url": menu_url,
            "order_id": order.id,
            "total": order.total_amount,
            "discount": order.discount_applied
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Receipt generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate receipt: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Receipt generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate receipt: {str(e)}")


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
    try:
        if not order_data.items or len(order_data.items) == 0:
            raise HTTPException(status_code=400, detail="No items in order")
        
        subtotal = 0.0
        discount_amount = 0.0
        summary_list = []

        item_details = []
        for item in order_data.items:
            menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
            if not menu_item:
                continue
            if not menu_item.is_available:
                raise HTTPException(status_code=400, detail=f"{menu_item.name} is currently unavailable")
            cost = menu_item.price * item.quantity
            subtotal += cost
            summary_list.append(f"{item.quantity}x {menu_item.name}")
            item_details.append({
                "name": menu_item.name, "qty": item.quantity, "price": menu_item.price,
                "veg": menu_item.is_veg, "cat": menu_item.category
            })

        if subtotal == 0:
            raise HTTPException(status_code=400, detail="Order total cannot be zero")

        if order_data.customer_phone:
            phone_clean = order_data.customer_phone.strip().replace(" ", "").replace("-", "")
            customer = db.query(models.Customer).filter(models.Customer.phone == phone_clean).first()
            if customer:
                if customer.discount_percent > 0:
                    discount_amount = round((subtotal * customer.discount_percent) / 100, 2)
                customer.visit_count += 1
                db.add(customer)

        # Calculate GST (5%)
        gst_amount = round((subtotal - discount_amount) * 0.05, 2)
        final_total = round(subtotal - discount_amount + gst_amount, 2)

        new_order = models.Order(
            table_number=order_data.table_number,
            order_type=order_data.order_type,
            status="Pending",
            subtotal=round(subtotal, 2),
            discount_applied=round(discount_amount, 2),
            gst_amount=gst_amount,
            total_amount=final_total,
            items_summary=", ".join(summary_list),
            customer_phone=order_data.customer_phone.strip() if order_data.customer_phone else None,
            taken_by=order_data.taken_by,
            table_status="Occupied" if order_data.order_type == "Dine-in" else "Available"
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        for d in item_details:
            db.add(models.OrderItem(order_id=new_order.id, item_name=d['name'], quantity=d['qty'], price=d['price'],
                                    is_veg=d['veg'], category=d['cat']))

        db.commit()
        return {"status": "Placed", "id": new_order.id, "discount": discount_amount, "gst": gst_amount}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Order placement error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")


# --- 🔒 SECURE ORDER MANAGEMENT ---
# Only staff can view kitchen display
@app.get("/kitchen-display/")
def kitchen_view(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user or user.role not in ["owner", "manager", "waiter", "chef"]:
        raise HTTPException(status_code=401, detail="Not authorized")
    return db.query(models.Order).filter(models.Order.status == "Pending").all()


# Only staff can complete orders
@app.post("/order/{order_id}/done")
def mark_done(order_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        if not user or user.role not in ["owner", "manager", "chef", "waiter"]:
            raise HTTPException(status_code=401, detail="Not authorized")

        order = db.query(models.Order).filter(models.Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order.status == "Completed":
            return {"status": "Already completed"}
        
        order.status = "Completed"
        db.commit()
        return {"status": "Done"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Mark done error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark order as done: {str(e)}")


# Only Managers/Owners can cancel orders
@app.post("/order/{order_id}/cancel")
def cancel_order(order_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        if not user or user.role not in ["owner", "manager"]:
            raise HTTPException(status_code=401, detail="Not authorized")

        order = db.query(models.Order).filter(models.Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order.status == "Cancelled":
            return {"status": "Already cancelled"}
        
        if order.payment_method:
            raise HTTPException(status_code=400, detail="Cannot cancel paid order")
        
        order.status = "Cancelled"
        db.commit()
        return {"status": "Cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Cancel order error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")


@app.get("/manager/orders/")
def manager_orders(db: Session = Depends(get_db)):
    # Note: Ideally this should be secured too, but leaving open for manager.html fetch
    # If you want to secure manager.html fetch, you'd need to pass token in frontend fetch calls.
    # For now, we assume manager page is behind login gate, but API is technically open if token not checked.
    # Adding security here would require updating manager.html JS to send headers.
    active = db.query(models.Order).filter(models.Order.status == "Pending").all()
    history = db.query(models.Order).filter(models.Order.status != "Pending").order_by(
        desc(models.Order.created_at)).limit(20).all()
    return {"active": active, "history": history}


@app.post("/manager/reset-history/")
def reset_today_history(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Reset order history - deletes today's completed/cancelled orders"""
    if not user or user.role not in ["manager", "owner"]:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Delete completed/cancelled orders from today
        deleted = db.query(models.Order).filter(
            models.Order.status.in_(["Completed", "Cancelled"]),
            models.Order.created_at >= today_start
        ).delete()
        
        db.commit()
        
        return {
            "status": "Success",
            "message": f"Reset {deleted} orders from today",
            "deleted_count": deleted
        }
    except Exception as e:
        db.rollback()
        print(f"Reset history error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset history: {str(e)}")


# --- CUSTOMER CRM ---
@app.post("/customers/")
def add_customer(c: CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Customer).filter(models.Customer.phone == c.phone).first()
    if existing:
        existing.name = c.name if c.name else None
        existing.relation = c.relation
        existing.discount_percent = c.discount_percent
        db.commit()
        return {"status": "Updated", "name": c.name or "Anonymous"}
    else:
        new_cust = models.Customer(
            name=c.name if c.name else None,
            phone=c.phone,
            relation=c.relation,
            discount_percent=c.discount_percent
        )
        db.add(new_cust)
        db.commit()
        return {"status": "Created", "name": c.name or "Anonymous"}


@app.get("/customers/")
def get_customers(search: Optional[str] = None, sort: str = "alpha", db: Session = Depends(get_db)):
    query = db.query(models.Customer)
    if search:
        # Handle NULL names in search
        query = query.filter(
            (models.Customer.phone.contains(search)) |
            (models.Customer.name.isnot(None) & models.Customer.name.contains(search))
        )

    # Sort alphabetically by name or by recent visits
    if sort == "alpha":
        # Sort by name, but put NULL names at the end
        from sqlalchemy import case
        query = query.order_by(
            case((models.Customer.name.is_(None), 1), else_=0),
            models.Customer.name
        )
    elif sort == "recent":
        query = query.order_by(desc(models.Customer.created_at))

    return query.limit(100).all()


@app.get("/customers/lookup/{phone}")
def lookup_customer(phone: str, db: Session = Depends(get_db)):
    """Lookup customer by phone number for real-time checkout"""
    try:
        phone_clean = phone.strip().replace(" ", "").replace("-", "")
        customer = db.query(models.Customer).filter(models.Customer.phone == phone_clean).first()
        if customer:
            return {
                "exists": True,
                "name": customer.name,
                "phone": customer.phone,
                "discount_percent": customer.discount_percent,
                "relation": customer.relation
            }
        return {"exists": False}
    except Exception as e:
        print(f"Customer lookup error: {e}")
        return {"exists": False}


# --- INVENTORY ---
@app.post("/inventory/")
def add_inv(req: InventoryCreate, db: Session = Depends(get_db)):
    db.add(models.InventoryRequest(item_name=req.item_name))
    db.commit()
    return {"status": "OK"}


@app.get("/inventory/")
def get_inv(db: Session = Depends(get_db)): return db.query(models.InventoryRequest).all()


@app.delete("/inventory/")
def clear_inv(db: Session = Depends(get_db)):
    db.query(models.InventoryRequest).delete()
    db.commit()
    return {"status": "Cleared"}


# --- OWNER ANALYTICS ---
@app.get("/owner/analytics/")
def owner_analytics(db: Session = Depends(get_db)):
    now = datetime.utcnow()
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


# --- TABLE MANAGEMENT ---
@app.get("/manager/tables/")
def get_table_status(db: Session = Depends(get_db)):
    """Get real-time status of all 10 tables"""
    tables_data = []

    for table_num in range(1, 11):
        # Find the most recent order for this table that's still pending (not paid)
        active_order = db.query(models.Order).filter(
            models.Order.table_number == table_num,
            models.Order.order_type == "Dine-in",
            models.Order.status.in_(["Pending", "Completed"]),
            models.Order.payment_method.is_(None)  # Not yet paid
        ).order_by(desc(models.Order.created_at)).first()

        if active_order:
            tables_data.append({
                "table_number": table_num,
                "status": "Occupied",
                "order_id": active_order.id,
                "bill_amount": active_order.total_amount,
                "items_summary": active_order.items_summary,
                "created_at": active_order.created_at.strftime("%I:%M %p")
            })
        else:
            tables_data.append({
                "table_number": table_num,
                "status": "Available",
                "order_id": None,
                "bill_amount": 0,
                "items_summary": "",
                "created_at": None
            })

    return {"tables": tables_data}


# --- CHECKOUT & PAYMENT ---
class CheckoutSchema(BaseModel):
    order_id: int
    payment_method: str  # "Cash", "Card", "UPI"
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    customer_discount: Optional[float] = None
    save_customer: bool = False


@app.post("/manager/checkout/")
def checkout_order(checkout: CheckoutSchema, db: Session = Depends(get_db)):
    """Process payment with discount recalculation and customer management"""
    try:
        order = db.query(models.Order).filter(models.Order.id == checkout.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.payment_method:
            raise HTTPException(status_code=400, detail="Order already paid")

        # Handle customer lookup and discount recalculation
        discount_to_apply = 0.0
        customer = None
        
        if checkout.customer_phone:
            # Clean phone number
            phone_clean = checkout.customer_phone.strip().replace(" ", "").replace("-", "")
            
            # Lookup existing customer
            customer = db.query(models.Customer).filter(models.Customer.phone == phone_clean).first()
            
            if customer:
                # Existing customer - use their discount
                if customer.discount_percent > 0:
                    discount_to_apply = (order.subtotal * customer.discount_percent) / 100
                customer.visit_count += 1
            else:
                # New customer - always create entry (to satisfy foreign key constraint)
                # Per requirement: "every number stored in our database with or without name"
                try:
                    # If save_customer is True, save name and discount
                    # If False, just save phone number (anonymous customer)
                    customer = models.Customer(
                        phone=phone_clean,
                        name=checkout.customer_name.strip() if (checkout.save_customer and checkout.customer_name and checkout.customer_name.strip()) else None,
                        discount_percent=float(checkout.customer_discount) if (checkout.save_customer and checkout.customer_discount) else 0.0,
                        relation="Regular"
                    )
                    db.add(customer)
                    db.flush()  # Flush to ensure customer is in database before setting foreign key
                    
                    # Apply discount if provided
                    if checkout.customer_discount and float(checkout.customer_discount) > 0:
                        discount_to_apply = (order.subtotal * float(checkout.customer_discount)) / 100
                except Exception as e:
                    # If customer creation fails (e.g., duplicate phone from race condition), try to fetch again
                    print(f"Customer creation failed, retrying lookup: {e}")
                    customer = db.query(models.Customer).filter(models.Customer.phone == phone_clean).first()
                    if not customer:
                        # If still no customer, we can't set the foreign key - skip setting customer_phone
                        print(f"Warning: Could not create or find customer with phone {phone_clean}, skipping customer_phone assignment")
                        phone_clean = None
            
            # Recalculate bill with discount
            if discount_to_apply > 0:
                order.discount_applied = round(discount_to_apply, 2)
                # Recalculate GST on discounted amount
                order.gst_amount = round((order.subtotal - discount_to_apply) * 0.05, 2)
                order.total_amount = round(order.subtotal - discount_to_apply + order.gst_amount, 2)
            
            # Only set customer_phone if customer exists in database (satisfies foreign key constraint)
            if phone_clean and customer:
                order.customer_phone = phone_clean

        # Mark as paid
        order.payment_method = checkout.payment_method
        order.paid_at = datetime.utcnow()
        order.table_status = "Available"
        order.status = "Completed"  # Also mark order as completed

        db.commit()

        return {
            "status": "Payment Successful",
            "order_id": order.id,
            "total": order.total_amount,
            "payment_method": checkout.payment_method,
            "discount_applied": discount_to_apply
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Checkout error: {e}")
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")


@app.get("/owner/history/")
def get_history(date: Optional[str] = None, month: Optional[str] = None, db: Session = Depends(get_db)):
    start_dt = None
    end_dt = None
    if date:
        start_dt = datetime.strptime(date, "%Y-%m-%d");
        end_dt = start_dt + timedelta(days=1)
    elif month:
        y, m = map(int, month.split('-'));
        import calendar;
        start_dt = datetime(y, m, 1);
        last = \
            calendar.monthrange(y, m)[1];
        end_dt = datetime(y, m, last) + timedelta(days=1)
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