from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import (
    BUSINESS_ADDRESS,
    BUSINESS_GSTIN,
    BUSINESS_LOCATION,
    BUSINESS_NAME,
    BUSINESS_PHONE,
    BUSINESS_TAGLINE,
    BUSINESS_UPI_ID,
    PUBLIC_BASE_URL,
)
from app.models import models


def _business_profile(db: Session, restaurant_id: int) -> dict:
    restaurant = db.get(models.Restaurant, restaurant_id)
    return {
        "name": restaurant.name if restaurant else BUSINESS_NAME,
        "tagline": BUSINESS_TAGLINE,
        "location": restaurant.timezone if restaurant else BUSINESS_LOCATION,
        "address": restaurant.address if restaurant and restaurant.address else BUSINESS_ADDRESS,
        "phone": restaurant.phone if restaurant and restaurant.phone else BUSINESS_PHONE,
        "gstin": restaurant.gstin if restaurant and restaurant.gstin else BUSINESS_GSTIN,
        "upi_id": restaurant.upi_id if restaurant and restaurant.upi_id else BUSINESS_UPI_ID,
    }


def generate_whatsapp_text(receipt: dict) -> str:
    return (
        f"Thank you for dining at {receipt['business']['name']}!\n"
        f"Invoice: {receipt.get('invoice_number') or receipt['order_id']}\n"
        f"Total paid: INR {receipt['total']:.2f}\n"
        f"Digital copy: {receipt['digital_url']}\n"
        "See you again soon."
    )


def generate_receipt_logic(order_id: int, db: Session, *, restaurant_id: int | None = None):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order or (restaurant_id is not None and order.restaurant_id != restaurant_id):
        raise HTTPException(status_code=404, detail="Order not found")

    business = _business_profile(db, order.restaurant_id)
    items_list = [
        {
            "name": item.item_name,
            "qty": item.quantity,
            "price": item.price,
            "total": round(item.quantity * item.price, 2),
            "gst_rate": item.gst_rate,
            "hsn_code": item.hsn_code,
            "modifiers": item.modifiers_json or [],
        }
        for item in order.items
    ]
    digital_url = f"{PUBLIC_BASE_URL}/receipt/{order.id}"

    receipt = {
        "business": business,
        "order_id": order.id,
        "invoice_number": order.invoice_number,
        "kot_number": order.kot_number,
        "date": order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else "",
        "table": order.table_number,
        "type": order.order_type,
        "items": items_list,
        "subtotal": order.subtotal,
        "discount": order.discount_applied,
        "gst": order.gst_amount,
        "cgst": order.cgst_amount,
        "sgst": order.sgst_amount,
        "gst_breakdown": order.gst_breakdown or {},
        "total": order.total_amount,
        "customer": order.customer_phone,
        "taken_by": order.taken_by,
        "payment_method": order.payment_method,
        "digital_url": digital_url,
        "qr_url": f"{PUBLIC_BASE_URL}/static/qr-placeholder.png",
        "pdf_url": digital_url,
        "menu_url": f"{PUBLIC_BASE_URL}/mobile",
    }
    receipt["whatsapp_text"] = generate_whatsapp_text(receipt)
    return receipt


def generate_kot_logic(order: models.Order) -> dict:
    return {
        "kot_number": order.kot_number,
        "order_id": order.id,
        "table": order.table_number,
        "order_type": order.order_type,
        "time": order.created_at.strftime("%H:%M") if order.created_at else "",
        "items": [
            {
                "name": item.item_name,
                "qty": item.quantity,
                "modifiers": item.modifiers_json or [],
            }
            for item in order.items
        ],
    }
