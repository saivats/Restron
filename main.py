from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
from database import engine, SessionLocal
import models

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


class OrderItemSchema(BaseModel):
    menu_item_id: int
    quantity: int


class OrderCreate(BaseModel):
    table_number: int
    items: List[OrderItemSchema]


# --- ROUTES ---

@app.get("/")
def home():
    return {"message": "Welcome to Restron!"}


@app.post("/menu/")
def create_menu_item(name: str, price: float, category: str, db: Session = Depends(get_db)):
    new_item = models.MenuItem(name=name, price=price, category=category)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/menu/")
def read_menu(db: Session = Depends(get_db)):
    items = db.query(models.MenuItem).all()
    return items


# --- NEW: Delete Menu Item ---
@app.delete("/menu/{item_id}")
def delete_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"status": "Item Deleted"}


@app.post("/order/")
def place_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    total_bill = 0.0
    summary_text_list = []
    for item in order_data.items:
        menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"Menu Item ID {item.menu_item_id} not found")
        item_cost = menu_item.price * item.quantity
        total_bill += item_cost
        summary_text_list.append(f"{item.quantity}x {menu_item.name}")

    final_summary = ", ".join(summary_text_list)
    new_order = models.Order(
        table_number=order_data.table_number,
        items_summary=final_summary,
        total_amount=total_bill
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return {"status": "Order Placed", "order_id": new_order.id, "summary": final_summary}


@app.get("/kitchen-display/")
def view_kitchen_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).filter(models.Order.status == "Pending").all()
    return orders


@app.post("/order/{order_id}/done")
def mark_order_done(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = "Completed"
    db.commit()
    return {"status": "Order Marked as Completed"}


# --- NEW: Sales Report Endpoint ---
@app.get("/stats/")
def get_stats(db: Session = Depends(get_db)):
    # Calculate total revenue from all orders
    total_revenue = db.query(func.sum(models.Order.total_amount)).scalar() or 0.0
    total_orders = db.query(models.Order).count()
    pending_orders = db.query(models.Order).filter(models.Order.status == "Pending").count()

    return {
        "revenue": total_revenue,
        "total_orders": total_orders,
        "pending": pending_orders
    }