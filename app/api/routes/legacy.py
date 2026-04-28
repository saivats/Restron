from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    CAN_CHECKOUT,
    CAN_READ_ORDER,
    CAN_VIEW_ANALYTICS,
    get_current_user,
    get_db,
    require_permission,
    user_restaurant_id,
)
from app.models import models
from app.schemas.schemas import CheckoutSchema
from app.services.analytics_service import history_report, owner_analytics
from app.services.checkout_service import checkout_order_logic
from app.services.order_service import (
    TERMINAL_ORDER_STATUSES,
    list_active_orders,
    list_history_orders,
    list_kitchen_orders,
    serialize_order,
)
from app.services.receipt_service import generate_receipt_logic
from app.services.table_service import table_dashboard

router = APIRouter()


@router.get("/kitchen-display/")
def kitchen_display(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_ORDER)),
):
    return list_kitchen_orders(db, restaurant_id=user_restaurant_id(user))


@router.get("/receipt/{order_id}")
def receipt(
    order_id: int,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user),
):
    return generate_receipt_logic(order_id, db, restaurant_id=user_restaurant_id(user) if user else None)


@router.get("/manager/tables/")
def manager_tables(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_ORDER)),
):
    return table_dashboard(db, restaurant_id=user_restaurant_id(user))


@router.get("/manager/orders/")
def manager_orders(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_ORDER)),
):
    restaurant_id = user_restaurant_id(user)
    active = [serialize_order(order) for order in list_active_orders(db, restaurant_id=restaurant_id)]
    history = [
        serialize_order(order)
        for order in list_history_orders(db, restaurant_id=restaurant_id)
        if order.status in TERMINAL_ORDER_STATUSES
    ]
    return {"active": active, "history": history[:100]}


@router.post("/manager/checkout/")
def manager_checkout(
    data: CheckoutSchema,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_CHECKOUT)),
):
    return checkout_order_logic(data, db, restaurant_id=user_restaurant_id(user), user=user)


@router.post("/manager/reset-history/")
def reset_today_history(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_VIEW_ANALYTICS)),
):
    restaurant_id = user_restaurant_id(user)
    start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    count = (
        db.query(models.Order)
        .filter(
            models.Order.restaurant_id == restaurant_id,
            models.Order.created_at >= start,
            models.Order.status.in_(TERMINAL_ORDER_STATUSES),
            models.Order.archived == False,
        )
        .update({models.Order.archived: True}, synchronize_session=False)
    )
    db.commit()
    return {"status": "Archived", "message": f"Archived {count} completed/cancelled orders without deleting records."}


@router.get("/owner/analytics/")
def owner_dashboard_analytics(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_VIEW_ANALYTICS)),
):
    return owner_analytics(db, restaurant_id=user_restaurant_id(user))


@router.get("/owner/history/")
def owner_history(
    date: str | None = None,
    month: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_VIEW_ANALYTICS)),
):
    return history_report(db, restaurant_id=user_restaurant_id(user), date=date, month=month)


@router.get("/stats/")
def admin_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_ORDER)),
):
    restaurant_id = user_restaurant_id(user)
    return {
        "pending": len(list_kitchen_orders(db, restaurant_id=restaurant_id)),
        "active": len(list_active_orders(db, restaurant_id=restaurant_id)),
    }
