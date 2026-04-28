from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CAN_CHECKOUT, get_db, require_permission, user_restaurant_id
from app.models import models
from app.schemas.schemas import CheckoutSchema, SplitBillRequest
from app.services.checkout_service import checkout_order_logic

router = APIRouter()


@router.post("/")
def checkout_order(
    data: CheckoutSchema,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_CHECKOUT)),
):
    return checkout_order_logic(data, db, restaurant_id=user_restaurant_id(user), user=user)


@router.post("/split")
def preview_split_bill(
    payload: SplitBillRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_CHECKOUT)),
):
    restaurant_id = user_restaurant_id(user)
    order = db.query(models.Order).filter(
        models.Order.restaurant_id == restaurant_id,
        models.Order.id == payload.order_id,
    ).first()
    if not order:
        return {"splits": []}

    if payload.split_type == "item" and payload.item_ids:
        selected_items = [item for item in order.items if item.id in set(payload.item_ids)]
        amount = round(sum(item.line_total or item.price * item.quantity for item in selected_items), 2)
        return {"splits": [{"label": "Selected items", "amount": amount, "item_ids": payload.item_ids}]}

    split_count = max(payload.split_count, 1)
    amount = round(order.total_amount / split_count, 2)
    splits = [{"label": f"Person {index + 1}", "amount": amount} for index in range(split_count)]
    if splits:
        splits[-1]["amount"] = round(order.total_amount - amount * (split_count - 1), 2)
    return {"splits": splits}
