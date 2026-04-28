from datetime import datetime, time, timedelta, timezone

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models import models
from app.services.order_service import ORDER_CLOSED


def _day_bounds(moment: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(moment.date(), time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _sum_revenue(db: Session, restaurant_id: int, start: datetime | None = None) -> float:
    query = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.restaurant_id == restaurant_id,
        models.Order.status.in_([ORDER_CLOSED, "Paid", "Completed"]),
        models.Order.archived == False,
    )
    if start:
        query = query.filter(models.Order.paid_at >= start)
    return round(query.scalar() or 0, 2)


def owner_analytics(db: Session, *, restaurant_id: int) -> dict:
    now = datetime.now(timezone.utc)
    today_start, _ = _day_bounds(now)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    closed_filter = (
        models.Order.restaurant_id == restaurant_id,
        models.Order.status.in_([ORDER_CLOSED, "Paid", "Completed"]),
        models.Order.archived == False,
    )
    total_revenue = _sum_revenue(db, restaurant_id)
    total_orders = db.query(func.count(models.Order.id)).filter(*closed_filter).scalar() or 0
    aov = round(total_revenue / total_orders, 2) if total_orders else 0

    best_sellers = (
        db.query(models.OrderItem.item_name, func.sum(models.OrderItem.quantity))
        .join(models.Order, models.Order.id == models.OrderItem.order_id)
        .filter(*closed_filter, models.Order.paid_at >= month_start)
        .group_by(models.OrderItem.item_name)
        .order_by(func.sum(models.OrderItem.quantity).desc())
        .limit(5)
        .all()
    )

    hour_expr = func.strftime("%H", models.Order.created_at)
    if db.bind and db.bind.dialect.name == "sqlite":
        hour_expr = func.strftime("%H", models.Order.created_at)
    else:
        hour_expr = extract("hour", models.Order.created_at)

    peak_rows = (
        db.query(hour_expr, func.count(models.Order.id))
        .filter(*closed_filter)
        .group_by(hour_expr)
        .order_by(func.count(models.Order.id).desc())
        .limit(3)
        .all()
    )

    return {
        "revenue": {
            "today": _sum_revenue(db, restaurant_id, today_start),
            "week": _sum_revenue(db, restaurant_id, week_start),
            "month": _sum_revenue(db, restaurant_id, month_start),
            "total": total_revenue,
        },
        "advanced": {
            "aov": aov,
            "peak_hours": [{"hour": int(row[0]), "orders": row[1]} for row in peak_rows if row[0] is not None],
        },
        "total_orders": total_orders,
        "best_sellers_month": [{"name": item[0], "qty": int(item[1] or 0)} for item in best_sellers],
    }


def history_report(db: Session, *, restaurant_id: int, date: str | None = None, month: str | None = None) -> dict:
    query = db.query(models.Order).filter(
        models.Order.restaurant_id == restaurant_id,
        models.Order.status.in_([ORDER_CLOSED, "Paid", "Completed"]),
        models.Order.archived == False,
    )

    include_logs = False
    if date:
        selected = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
        start, end = _day_bounds(selected)
        query = query.filter(models.Order.paid_at >= start, models.Order.paid_at < end)
        include_logs = True
    elif month:
        selected = datetime.fromisoformat(f"{month}-01").replace(tzinfo=timezone.utc)
        next_month = (selected.replace(day=28) + timedelta(days=4)).replace(day=1)
        query = query.filter(models.Order.paid_at >= selected, models.Order.paid_at < next_month)

    orders = query.order_by(models.Order.paid_at.desc()).all()
    items = {}
    veg_sold = 0
    non_veg_sold = 0
    for order in orders:
        for item in order.items:
            items[item.item_name] = items.get(item.item_name, 0) + item.quantity
            if item.is_veg:
                veg_sold += item.quantity
            else:
                non_veg_sold += item.quantity

    report = {
        "revenue": round(sum(order.total_amount for order in orders), 2),
        "veg_sold": veg_sold,
        "non_veg_sold": non_veg_sold,
        "items": [{"name": name, "qty": qty} for name, qty in sorted(items.items())],
    }
    if include_logs:
        report["detailed_logs"] = [
            {
                "id": order.id,
                "time": order.paid_at.strftime("%H:%M") if order.paid_at else "",
                "type": order.order_type,
                "table": order.table_number,
                "items": order.items_summary,
                "total": order.total_amount,
            }
            for order in orders
        ]
    return report
