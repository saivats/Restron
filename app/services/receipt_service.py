from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import PUBLIC_BASE_URL
from app.core.security import receipt_token, verify_receipt_token
from app.models import models


def _business_profile(db: Session, restaurant_id: int) -> dict:
    restaurant = db.get(models.Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=500, detail=f"Restaurant {restaurant_id} not found — cannot generate receipt")

    return {
        "name": restaurant.name,
        "tagline": "Cloud-powered restaurant billing",
        "location": restaurant.address or "",
        "address": restaurant.address or "",
        "phone": restaurant.phone or "",
        "gstin": restaurant.gstin or "",
        "upi_id": restaurant.upi_id or "",
        "currency_symbol": restaurant.currency_symbol or "₹",
        "gst_rate": restaurant.gst_rate or 5.0,
        "slug": restaurant.slug or "default",
    }


def generate_whatsapp_text(receipt: dict) -> str:
    currency = receipt["business"].get("currency_symbol", "₹")
    return (
        f"Thank you for dining at {receipt['business']['name']}!\n"
        f"Invoice: {receipt.get('invoice_number') or receipt['order_id']}\n"
        f"Total paid: {currency}{receipt['total']:.2f}\n"
        f"Digital copy: {receipt['digital_url']}\n"
        "See you again soon."
    )


def generate_receipt_logic(
    order_id: int,
    db: Session,
    *,
    restaurant_id: int | None = None,
    token: str | None = None,
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if restaurant_id is not None:
        # Authenticated staff request — already tenant-scoped by the caller.
        if order.restaurant_id != restaurant_id:
            raise HTTPException(status_code=404, detail="Order not found")
    else:
        # Unauthenticated (customer-facing) request — must present the
        # signed token issued when the receipt link was created, so raw
        # order_id enumeration can't pull other customers'/tenants' receipts.
        if not verify_receipt_token(order.id, order.restaurant_id, token):
            raise HTTPException(status_code=404, detail="Order not found")

    business = _business_profile(db, order.restaurant_id)
    slug = business["slug"]
    currency = business["currency_symbol"]
    token_value = receipt_token(order.id, order.restaurant_id)

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
    digital_url = f"{PUBLIC_BASE_URL}/r/{slug}/receipt/{order.id}?t={token_value}"
    menu_url = f"{PUBLIC_BASE_URL}/r/{slug}/mobile"
    receipt_upload_path = f"receipts/{order.restaurant_id}/receipt_{order.id}.pdf"

    receipt = {
        "business": business,
        "order_id": order.id,
        "receipt_token": token_value,
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
        "menu_url": menu_url,
        "currency_symbol": currency,
        "receipt_upload_path": receipt_upload_path,
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
