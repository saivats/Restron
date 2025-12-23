from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from database import engine, SessionLocal
import models
import os

# Create tables
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
    order_type: str = "Dine-in"  # Default to Dine-in


class InventoryCreate(BaseModel):
    item_name: str


class AvailabilityUpdate(BaseModel):
    is_available: bool


# --- PAGE ROUTES ---
@app.get("/mobile")
def mobile_app(): return FileResponse("static/menu.html")


@app.get("/kitchen")
def kitchen_app(): return FileResponse("static/kitchen.html")


@app.get("/manager")
def manager_app(): return FileResponse("static/manager.html")  # NEW


@app.get("/owner")
def owner_app(): return FileResponse("static/owner.html")  # NEW (Replaces admin)


# --- API ROUTES ---

@app.get("/")
def home(): return {"message": "Restron is Online!"}


# 1. MENU MANAGEMENT (Owner Only)
@app.post("/menu/")
def create_menu_item(name: str, price: float, category: str, db: Session = Depends(get_db)):
    new_item = models.MenuItem(name=name, price=price, category=category)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.delete("/menu/{item_id}")
def delete_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"status": "Deleted"}


@app.get("/menu/")
def read_menu(db: Session = Depends(get_db)):
    # Manager Dashboard needs ALL items to toggle availability
    # Customer Menu needs ONLY available items
    # For simplicity, we send ALL and let Frontend filter if needed
    return db.query(models.MenuItem).all()


# 2. STOCK MANAGEMENT (Manager)
@app.put("/menu/{item_id}/availability")
def toggle_availability(item_id: int, status: AvailabilityUpdate, db: Session = Depends(get_db)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.is_available = status.is_available
    db.commit()
    return {"status": "Updated"}


# 3. ORDERING (With Delivery Logic)
@app.post("/order/")
def place_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    total_bill = 0.0
    summary_list = []

    if not order_data.items: raise HTTPException(status_code=400, detail="Empty order")

    for item in order_data.items:
        menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
        if not menu_item: continue
        item_cost = menu_item.price * item.quantity
        total_bill += item_cost
        summary_list.append(f"{item.quantity}x {menu_item.name}")

    new_order = models.Order(
        table_number=order_data.table_number,
        items_summary=", ".join(summary_list),
        total_amount=total_bill,
        status="Pending",
        order_type=order_data.order_type  # Save the tag
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return {"status": "Order Placed", "id": new_order.id}


@app.get("/kitchen-display/")
def get_kitchen_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).filter(models.Order.status == "Pending").all()


@app.post("/order/{order_id}/done")
def mark_done(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order:
        order.status = "Completed"
        db.commit()
    return {"status": "Done"}


# 4. INVENTORY (Manager Request -> Owner View)
@app.post("/inventory/")
def request_inventory(req: InventoryCreate, db: Session = Depends(get_db)):
    db_req = models.InventoryRequest(item_name=req.item_name)
    db.add(db_req)
    db.commit()
    return {"status": "Requested"}


@app.get("/inventory/")
def get_inventory(db: Session = Depends(get_db)):
    return db.query(models.InventoryRequest).all()


@app.delete("/inventory/")
def clear_inventory(db: Session = Depends(get_db)):
    db.query(models.InventoryRequest).delete()
    db.commit()
    return {"status": "Cleared"}


# 5. STATS (Owner Only)
@app.get("/stats/")
def get_stats(db: Session = Depends(get_db)):
    total_rev = db.query(func.sum(models.Order.total_amount)).scalar() or 0.0
    total_orders = db.query(models.Order).count()

    # Split by Delivery/Dine-in
    dine_in_count = db.query(models.Order).filter(models.Order.order_type == "Dine-in").count()
    delivery_count = db.query(models.Order).filter(models.Order.order_type == "Delivery").count()

    return {
        "revenue": total_rev,
        "total_orders": total_orders,
        "dine_in": dine_in_count,
        "delivery": delivery_count
    }