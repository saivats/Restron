from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from pydantic import BaseModel
from typing import List, Optional
from database import engine, SessionLocal
import models
import datetime
from datetime import timedelta
import calendar

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Restron")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- SCHEMAS ---
class OrderItemSchema(BaseModel):
    menu_item_id: int
    quantity: int


class OrderCreate(BaseModel):
    table_number: int
    items: List[OrderItemSchema]
    order_type: str = "Dine-in"
    customer_phone: Optional[str] = None  # New Field


class InventoryCreate(BaseModel):
    item_name: str


class AvailabilityUpdate(BaseModel):
    is_available: bool


class CustomerCreate(BaseModel):
    name: str
    phone: str
    relation: str = "Regular"
    discount_percent: float = 0.0


# --- PAGES ---
@app.get("/mobile")
def p1(): return FileResponse("static/menu.html")


@app.get("/kitchen")
def p2(): return FileResponse("static/kitchen.html")


@app.get("/manager")
def p3(): return FileResponse("static/manager.html")


@app.get("/owner")
def p4(): return FileResponse("static/owner.html")


# --- API ROUTES ---

# 1. MENU
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


# 2. CUSTOMER DATABASE (CRM)
@app.post("/customers/")
def add_customer(c: CustomerCreate, db: Session = Depends(get_db)):
    # Check if exists
    existing = db.query(models.Customer).filter(models.Customer.phone == c.phone).first()
    if existing:
        # Update existing
        existing.name = c.name
        existing.relation = c.relation
        existing.discount_percent = c.discount_percent
        db.commit()
        return {"status": "Updated", "name": c.name}
    else:
        # Create new
        new_cust = models.Customer(
            name=c.name, phone=c.phone, relation=c.relation, discount_percent=c.discount_percent
        )
        db.add(new_cust)
        db.commit()
        return {"status": "Created", "name": c.name}


@app.get("/customers/")
def get_customers(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Customer)
    if search:
        query = query.filter(models.Customer.phone.contains(search) | models.Customer.name.contains(search))
    return query.limit(50).all()


# 3. ORDERS (With Discount Logic)
@app.post("/order/")
def place_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    subtotal = 0.0
    discount_amount = 0.0
    summary_list = []

    # Calculate Subtotal
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

    # Discount Logic
    customer_phone = order_data.customer_phone
    if customer_phone:
        customer = db.query(models.Customer).filter(models.Customer.phone == customer_phone).first()
        if customer:
            if customer.discount_percent > 0:
                discount_amount = (subtotal * customer.discount_percent) / 100

            # Increment visit count
            customer.visit_count += 1
            db.add(customer)

    final_total = subtotal - discount_amount

    # Create Order
    new_order = models.Order(
        table_number=order_data.table_number,
        order_type=order_data.order_type,
        status="Pending",
        subtotal=subtotal,
        discount_applied=discount_amount,
        total_amount=final_total,
        items_summary=", ".join(summary_list),
        customer_phone=customer_phone
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Save Items
    for d in item_details:
        db_item = models.OrderItem(
            order_id=new_order.id,
            item_name=d['name'], quantity=d['qty'], price=d['price'],
            is_veg=d['veg'], category=d['cat']
        )
        db.add(db_item)

    db.commit()
    return {"status": "Placed", "id": new_order.id, "discount": discount_amount}


@app.get("/kitchen-display/")
def kitchen_view(db: Session = Depends(get_db)):
    return db.query(models.Order).filter(models.Order.status == "Pending").all()


@app.post("/order/{order_id}/done")
def mark_done(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order:
        order.status = "Completed"
        db.commit()
    return {"status": "Done"}


# --- MANAGER ---
@app.get("/manager/orders/")
def manager_orders(db: Session = Depends(get_db)):
    active = db.query(models.Order).filter(models.Order.status == "Pending").all()
    history = db.query(models.Order).filter(models.Order.status != "Pending") \
        .order_by(desc(models.Order.created_at)).limit(10).all()
    return {"active": active, "history": history}


# --- INVENTORY ---
@app.post("/inventory/")
def add_inv(req: InventoryCreate, db: Session = Depends(get_db)):
    db.add(models.InventoryRequest(item_name=req.item_name))
    db.commit()
    return {"status": "OK"}


@app.get("/inventory/")
def get_inv(db: Session = Depends(get_db)):
    return db.query(models.InventoryRequest).all()


@app.delete("/inventory/")
def clear_inv(db: Session = Depends(get_db)):
    db.query(models.InventoryRequest).delete()
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
        return db.query(func.sum(models.Order.total_amount)) \
            .filter(models.Order.created_at >= date_limit).scalar() or 0.0

    best_sellers_month = db.query(
        models.OrderItem.item_name, func.sum(models.OrderItem.quantity).label('total_qty')
    ).join(models.Order).filter(models.Order.created_at >= month_start) \
        .group_by(models.OrderItem.item_name).order_by(desc('total_qty')).limit(5).all()

    total_rev_month = get_rev(month_start)
    total_orders_month = db.query(models.Order).filter(models.Order.created_at >= month_start).count()
    aov = round(total_rev_month / total_orders_month, 2) if total_orders_month > 0 else 0

    peak_hours = db.query(
        extract('hour', models.Order.created_at).label('h'), func.count(models.Order.id).label('cnt')
    ).group_by('h').order_by(desc('cnt')).limit(3).all()

    cat_perf = db.query(
        models.OrderItem.category, func.sum(models.OrderItem.price * models.OrderItem.quantity).label('rev')
    ).join(models.Order).filter(models.Order.created_at >= month_start) \
        .group_by(models.OrderItem.category).order_by(desc('rev')).all()

    return {
        "revenue": {
            "today": get_rev(today_start),
            "week": get_rev(week_start),
            "month": total_rev_month,
            "total": db.query(func.sum(models.Order.total_amount)).scalar() or 0.0
        },
        "best_sellers_month": [{"name": b[0], "qty": b[1]} for b in best_sellers_month],
        "advanced": {
            "aov": aov,
            "peak_hours": [{"hour": h[0], "count": h[1]} for h in peak_hours],
            "category_performance": [{"cat": c[0], "rev": c[1]} for c in cat_perf]
        }
    }


@app.get("/owner/history/")
def get_history(date: Optional[str] = None, month: Optional[str] = None, db: Session = Depends(get_db)):
    start_dt = None
    end_dt = None
    if date:
        start_dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=1)
    elif month:
        y, m = map(int, month.split('-'))
        start_dt = datetime.datetime(y, m, 1)
        last_day = calendar.monthrange(y, m)[1]
        end_dt = datetime.datetime(y, m, last_day) + timedelta(days=1)
    else:
        raise HTTPException(status_code=400, detail="Provide date or month")

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
        for o in orders:
            detailed_logs.append({
                "id": o.id, "time": o.created_at.strftime("%I:%M %p"),
                "type": o.order_type, "table": o.table_number if o.order_type == "Dine-in" else "-",
                "items": o.items_summary, "total": o.total_amount,
                "discount": o.discount_applied, "customer": o.customer_phone
            })

    return {
        "revenue": revenue, "veg_sold": veg_count, "non_veg_sold": non_veg_count,
        "items": [{"name": i[0], "qty": i[1]} for i in all_items],
        "detailed_logs": detailed_logs
    }