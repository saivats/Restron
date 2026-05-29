from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import models
from app.schemas.schemas import CheckoutSchema
from app.services.audit_service import write_audit_log
from app.services.billing_service import calculate_order_totals, create_invoice_for_order
from app.services.order_service import ACTIVE_ORDER_STATUSES, ORDER_CLOSED, serialize_order


def checkout_order_logic(
    data: CheckoutSchema,
    db: Session,
    *,
    restaurant_id: int,
    user: models.User | None = None,
):
    order = db.query(models.Order).filter(models.Order.restaurant_id == restaurant_id, models.Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in ACTIVE_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Order is not active; current status is {order.status}")

    before_state = serialize_order(order)
    customer_phone = data.customer_phone.strip() if data.customer_phone else order.customer_phone
    discount_percent = 0.0

    if customer_phone:
        order.customer_phone = customer_phone
        customer = db.query(models.Customer).filter(
            models.Customer.restaurant_id == restaurant_id,
            models.Customer.phone == customer_phone,
        ).first()

        if data.save_customer:
            if customer:
                if data.customer_name:
                    customer.name = data.customer_name
                if data.customer_discount is not None:
                    customer.discount_percent = data.customer_discount
            else:
                customer = models.Customer(
                    restaurant_id=restaurant_id,
                    name=data.customer_name or "Valued Customer",
                    phone=customer_phone,
                    discount_percent=data.customer_discount or 0.0,
                    visit_count=0,
                )
                db.add(customer)
                db.flush()

        if customer:
            customer.visit_count += 1
            if data.customer_name:
                customer.name = data.customer_name
            if data.customer_discount is not None:
                customer.discount_percent = data.customer_discount
            discount_percent = customer.discount_percent
        elif data.customer_discount:
            discount_percent = data.customer_discount

    totals = calculate_order_totals(
        [{"price": item.price, "quantity": item.quantity, "gst_rate": item.gst_rate} for item in order.items],
        discount_percent,
    )
    order.subtotal = totals["subtotal"]
    order.discount_percent = totals["discount_percent"]
    order.discount_applied = totals["discount_amount"]
    order.cgst_amount = totals["cgst_amount"]
    order.sgst_amount = totals["sgst_amount"]
    order.gst_amount = totals["gst_amount"]
    order.gst_breakdown = totals["gst_breakdown"]
    order.total_amount = totals["total_amount"]
    order.status = ORDER_CLOSED
    order.payment_method = data.payment_method
    order.paid_at = datetime.now(timezone.utc)
    order.closed_at = order.paid_at
    order.table_status = "Available"

    invoice = create_invoice_for_order(db, order, data.payment_method, order.paid_at)

    if order.order_type == "Dine-in":
        table = db.query(models.Table).filter(
            models.Table.restaurant_id == restaurant_id,
            models.Table.table_number == order.table_number,
        ).first()
        if table:
            table.status = "Available"
            table.active_order_id = None
            table.covers = 0

    write_audit_log(
        db,
        action="order.checkout",
        entity_type="order",
        entity_id=order.id,
        restaurant_id=restaurant_id,
        user=user,
        before_state=before_state,
        after_state=serialize_order(order),
    )
    db.commit()
    db.refresh(order)

    return {
        "status": "Success",
        "order_id": order.id,
        "invoice_number": invoice.invoice_number,
        "subtotal": order.subtotal,
        "discount_applied": order.discount_applied,
        "cgst": order.cgst_amount,
        "sgst": order.sgst_amount,
        "gst": order.gst_amount,
        "total": order.total_amount,
    }
