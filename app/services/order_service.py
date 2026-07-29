from datetime import datetime, timezone
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import DEFAULT_RESTAURANT_ID
from app.models import models
from app.schemas.schemas import OrderCreate
from app.services.audit_service import write_audit_log
from app.services.billing_service import calculate_order_totals, normalize_gst_rate

logger = logging.getLogger(__name__)


ORDER_PLACED = "PLACED"
ORDER_KOT_SENT = "KOT_SENT"
ORDER_PREPARING = "PREPARING"
ORDER_READY = "READY"
ORDER_SERVED = "SERVED"
ORDER_CLOSED = "CLOSED"
ORDER_CANCELLED = "CANCELLED"

ACTIVE_ORDER_STATUSES = {ORDER_PLACED, ORDER_KOT_SENT, ORDER_PREPARING, ORDER_READY, ORDER_SERVED, "Pending"}
KITCHEN_ORDER_STATUSES = {ORDER_PLACED, ORDER_KOT_SENT, ORDER_PREPARING, "Pending"}
TERMINAL_ORDER_STATUSES = {ORDER_CLOSED, ORDER_CANCELLED, "Paid", "Completed", "Cancelled"}
VALID_ORDER_STATUSES = ACTIVE_ORDER_STATUSES | TERMINAL_ORDER_STATUSES


def _clean_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    return cleaned or None


def _kot_number(restaurant_id: int, order_id: int) -> str:
    today = datetime.now(timezone.utc).strftime("%y%m%d")
    return f"KOT-{restaurant_id}-{today}-{order_id:04d}"


def _find_running_table_order(db: Session, table_number: int, restaurant_id: int):
    return (
        db.query(models.Order)
        .filter(
            models.Order.restaurant_id == restaurant_id,
            models.Order.table_number == table_number,
            models.Order.order_type == "Dine-in",
            models.Order.archived == False,
            models.Order.status.in_(ACTIVE_ORDER_STATUSES),
        )
        .order_by(models.Order.created_at.desc())
        .first()
    )


def _line_items_from_order(order: models.Order) -> list[dict]:
    return [
        {
            "price": item.price,
            "quantity": item.quantity,
            "gst_rate": item.gst_rate,
        }
        for item in order.items
    ]


def _apply_totals(order: models.Order, totals: dict) -> None:
    order.subtotal = totals["subtotal"]
    order.discount_percent = totals["discount_percent"]
    order.discount_applied = totals["discount_amount"]
    order.cgst_amount = totals["cgst_amount"]
    order.sgst_amount = totals["sgst_amount"]
    order.gst_amount = totals["gst_amount"]
    order.gst_breakdown = totals["gst_breakdown"]
    order.total_amount = totals["total_amount"]


def _touch_table(db: Session, order: models.Order, covers: int = 0) -> None:
    if order.order_type != "Dine-in" or not order.table_number:
        return

    table = (
        db.query(models.Table)
        .filter(models.Table.restaurant_id == order.restaurant_id, models.Table.table_number == order.table_number)
        .first()
    )
    if not table:
        table = models.Table(
            restaurant_id=order.restaurant_id,
            table_number=order.table_number,
            name=f"Table {order.table_number}",
        )
        db.add(table)

    table.status = "Occupied" if order.status in ACTIVE_ORDER_STATUSES else "Available"
    table.active_order_id = order.id if order.status in ACTIVE_ORDER_STATUSES else None
    if covers:
        table.covers = covers


def _serialize_order(order: models.Order) -> dict:
    return {
        "id": order.id,
        "order_id": order.id,
        "table_number": order.table_number,
        "status": order.status,
        "kot_number": order.kot_number,
        "invoice_number": order.invoice_number,
        "items_summary": order.items_summary,
        "subtotal": order.subtotal,
        "discount_applied": order.discount_applied,
        "gst_amount": order.gst_amount,
        "cgst_amount": order.cgst_amount,
        "sgst_amount": order.sgst_amount,
        "gst_breakdown": order.gst_breakdown or {},
        "total_amount": order.total_amount,
        "order_type": order.order_type,
        "customer_phone": order.customer_phone,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "taken_by": order.taken_by,
        "payment_method": order.payment_method,
        "items": [
            {
                "name": item.item_name,
                "qty": item.quantity,
                "price": item.price,
                "total": item.line_total if item.line_total is not None else round(item.price * item.quantity, 2),
            }
            for item in order.items
        ],
    }


def place_order_logic(
    order_data: OrderCreate,
    db: Session,
    *,
    restaurant_id: int = DEFAULT_RESTAURANT_ID,
    user: models.User | None = None,
):
    if not order_data.items:
        raise HTTPException(status_code=400, detail="No items in order")

    try:
        customer = None
        customer_phone = _clean_phone(order_data.customer_phone)
        if customer_phone:
            customer = db.query(models.Customer).filter(
                models.Customer.restaurant_id == restaurant_id,
                models.Customer.phone == customer_phone,
            ).first()

        discount_percent = customer.discount_percent if customer else 0.0
        line_items = []
        summary_list = []
        new_order_items = []

        for item in order_data.items:
            menu_item = db.query(models.MenuItem).filter(
                models.MenuItem.restaurant_id == restaurant_id,
                models.MenuItem.id == item.menu_item_id,
            ).first()
            if not menu_item:
                raise HTTPException(status_code=404, detail=f"Menu item {item.menu_item_id} not found")
            if not menu_item.is_available:
                raise HTTPException(status_code=400, detail=f"{menu_item.name} is currently unavailable")

            resolved_modifiers = []
            if item.modifier_ids:
                db_modifiers = db.query(models.ItemModifier).filter(
                    models.ItemModifier.id.in_(item.modifier_ids),
                    models.ItemModifier.restaurant_id == restaurant_id,
                    models.ItemModifier.is_available == True,
                    (models.ItemModifier.menu_item_id == menu_item.id)
                    | (models.ItemModifier.menu_item_id.is_(None)),
                ).all()
                found_ids = {modifier.id for modifier in db_modifiers}
                missing = set(item.modifier_ids) - found_ids
                if missing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid modifier selection for {menu_item.name}",
                    )
                resolved_modifiers = db_modifiers

            modifier_price_delta = sum(modifier.price_delta or 0.0 for modifier in resolved_modifiers)
            modifier_percent_delta = sum(modifier.percent_delta or 0.0 for modifier in resolved_modifiers)
            unit_price = round((menu_item.price + modifier_price_delta) * (1 + modifier_percent_delta / 100), 2)
            unit_price = max(unit_price, 0.0)
            gst_rate = normalize_gst_rate(menu_item.gst_rate)

            line_items.append({"price": unit_price, "quantity": item.quantity, "gst_rate": gst_rate})
            modifier_names = [modifier.name for modifier in resolved_modifiers]
            modifier_label = f" ({', '.join(modifier_names)})" if modifier_names else ""
            summary_list.append(f"{item.quantity}x {menu_item.name}{modifier_label}")
            new_order_items.append(
                models.OrderItem(
                    restaurant_id=restaurant_id,
                    menu_item_id=menu_item.id,
                    item_name=menu_item.name,
                    quantity=item.quantity,
                    price=unit_price,
                    line_total=round(unit_price * item.quantity, 2),
                    gst_rate=gst_rate,
                    hsn_code=menu_item.hsn_code,
                    modifiers_json=[
                        {
                            "id": modifier.id,
                            "name": modifier.name,
                            "price_delta": modifier.price_delta,
                            "percent_delta": modifier.percent_delta,
                        }
                        for modifier in resolved_modifiers
                    ],
                    is_veg=menu_item.is_veg,
                    category=menu_item.category,
                )
            )

        totals = calculate_order_totals(line_items, discount_percent)
        if totals["subtotal"] <= 0:
            raise HTTPException(status_code=400, detail="Order total cannot be zero")

        existing_order = None
        if order_data.order_type == "Dine-in":
            existing_order = _find_running_table_order(db, order_data.table_number, restaurant_id)

        if existing_order:
            before_state = _serialize_order(existing_order)
            if not customer and existing_order.customer_phone:
                customer = db.query(models.Customer).filter(
                    models.Customer.restaurant_id == restaurant_id,
                    models.Customer.phone == existing_order.customer_phone,
                ).first()
                discount_percent = customer.discount_percent if customer else 0.0
            combined_line_items = _line_items_from_order(existing_order) + line_items
            for order_item in new_order_items:
                order_item.order_id = existing_order.id
                db.add(order_item)

            db.flush()
            existing_order.items_summary = ", ".join(
                [part for part in [existing_order.items_summary, ", ".join(summary_list)] if part]
            )
            existing_order.customer_phone = customer_phone or existing_order.customer_phone
            existing_order.taken_by = order_data.taken_by if order_data.taken_by != "Customer" else existing_order.taken_by
            existing_order.status = ORDER_KOT_SENT
            _apply_totals(existing_order, calculate_order_totals(combined_line_items, discount_percent))
            _touch_table(db, existing_order, order_data.covers)
            write_audit_log(
                db,
                action="order.updated",
                entity_type="order",
                entity_id=existing_order.id,
                restaurant_id=restaurant_id,
                user=user,
                before_state=before_state,
                after_state=_serialize_order(existing_order),
            )
            db.commit()
            db.refresh(existing_order)
            return {"status": "Updated", "id": existing_order.id, "order": _serialize_order(existing_order)}

        new_order = models.Order(
            restaurant_id=restaurant_id,
            table_number=order_data.table_number,
            order_type=order_data.order_type,
            status=ORDER_KOT_SENT,
            customer_phone=customer_phone,
            items_summary=", ".join(summary_list),
            taken_by=order_data.taken_by,
            table_status="Occupied" if order_data.order_type == "Dine-in" else "Available",
        )
        _apply_totals(new_order, totals)
        db.add(new_order)
        db.flush()

        new_order.kot_number = _kot_number(restaurant_id, new_order.id)
        for order_item in new_order_items:
            order_item.order_id = new_order.id
            db.add(order_item)

        if customer:
            customer.visit_count += 1

        _touch_table(db, new_order, order_data.covers)
        write_audit_log(
            db,
            action="order.created",
            entity_type="order",
            entity_id=new_order.id,
            restaurant_id=restaurant_id,
            user=user,
            after_state=_serialize_order(new_order),
        )
        db.commit()
        db.refresh(new_order)
        return {"status": "Placed", "id": new_order.id, "order": _serialize_order(new_order)}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Order placement failed restaurant_id=%s: %s", restaurant_id, exc)
        raise HTTPException(status_code=500, detail="Order placement failed. Please try again.") from exc


def update_order_status(
    db: Session,
    order_id: int,
    status_value: str,
    *,
    restaurant_id: int,
    user: models.User | None = None,
):
    normalized_status = status_value.upper()
    legacy_map = {"DONE": ORDER_READY, "PAID": ORDER_CLOSED, "COMPLETED": ORDER_CLOSED, "CANCELLED": ORDER_CANCELLED}
    normalized_status = legacy_map.get(normalized_status, normalized_status)
    if normalized_status not in VALID_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid order status")

    order = db.query(models.Order).filter(models.Order.restaurant_id == restaurant_id, models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    before_state = _serialize_order(order)
    order.status = normalized_status
    if normalized_status == ORDER_CANCELLED:
        order.cancelled_at = datetime.now(timezone.utc)
    if normalized_status == ORDER_CLOSED:
        order.closed_at = datetime.now(timezone.utc)
        order.table_status = "Available"

    _touch_table(db, order)
    write_audit_log(
        db,
        action="order.status_changed",
        entity_type="order",
        entity_id=order.id,
        restaurant_id=restaurant_id,
        user=user,
        before_state=before_state,
        after_state=_serialize_order(order),
    )
    db.commit()
    db.refresh(order)
    return _serialize_order(order)


def list_active_orders(db: Session, *, restaurant_id: int):
    return (
        db.query(models.Order)
        .filter(
            models.Order.restaurant_id == restaurant_id,
            models.Order.archived == False,
            models.Order.status.in_(ACTIVE_ORDER_STATUSES),
        )
        .order_by(models.Order.created_at.asc())
        .all()
    )


def list_kitchen_orders(db: Session, *, restaurant_id: int):
    return (
        db.query(models.Order)
        .filter(
            models.Order.restaurant_id == restaurant_id,
            models.Order.archived == False,
            models.Order.status.in_(KITCHEN_ORDER_STATUSES),
        )
        .order_by(models.Order.created_at.asc())
        .all()
    )


def list_history_orders(db: Session, *, restaurant_id: int, limit: int = 100):
    return (
        db.query(models.Order)
        .filter(models.Order.restaurant_id == restaurant_id, models.Order.archived == False)
        .order_by(models.Order.created_at.desc(), models.Order.id.desc())
        .limit(limit)
        .all()
    )


def serialize_order(order: models.Order) -> dict:
    return _serialize_order(order)
