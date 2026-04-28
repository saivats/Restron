from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import (
    CAN_CANCEL_ORDER,
    CAN_CREATE_ORDER,
    CAN_READ_ORDER,
    CAN_UPDATE_ORDER,
    get_current_user,
    get_db,
    require_permission,
    user_restaurant_id,
)
from app.core.config import DEFAULT_RESTAURANT_ID
from app.models import models
from app.schemas.schemas import OrderCreate, OrderStatusUpdate
from app.services.order_service import (
    ORDER_CANCELLED,
    ORDER_READY,
    list_active_orders,
    list_history_orders,
    list_kitchen_orders,
    place_order_logic,
    serialize_order,
    update_order_status,
)
from app.services.receipt_service import generate_receipt_logic
from app.services.websocket_manager import kitchen_ws_manager

router = APIRouter()


@router.post("/")
async def place_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user),
):
    restaurant_id = user_restaurant_id(user)
    result = place_order_logic(order_data, db, restaurant_id=restaurant_id, user=user)
    await kitchen_ws_manager.broadcast(restaurant_id, {"event": "order.changed", "order": result["order"]})
    return result


@router.get("/active")
def get_active_orders(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_ORDER)),
):
    return list_active_orders(db, restaurant_id=user_restaurant_id(user))


@router.get("/history")
def get_order_history(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_ORDER)),
):
    return list_history_orders(db, restaurant_id=user_restaurant_id(user), limit=limit)


@router.get("/kitchen")
def kitchen_orders(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_ORDER)),
):
    return list_kitchen_orders(db, restaurant_id=user_restaurant_id(user))


@router.get("/{order_id}/receipt")
def get_receipt(
    order_id: int,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user),
):
    return generate_receipt_logic(order_id, db, restaurant_id=user_restaurant_id(user) if user else None)


@router.post("/{order_id}/status")
async def set_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_UPDATE_ORDER)),
):
    restaurant_id = user_restaurant_id(user)
    order = update_order_status(db, order_id, payload.status, restaurant_id=restaurant_id, user=user)
    await kitchen_ws_manager.broadcast(restaurant_id, {"event": "order.changed", "order": order})
    return order


@router.post("/{order_id}/done")
async def mark_order_done(
    order_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_UPDATE_ORDER)),
):
    restaurant_id = user_restaurant_id(user)
    order = update_order_status(db, order_id, ORDER_READY, restaurant_id=restaurant_id, user=user)
    await kitchen_ws_manager.broadcast(restaurant_id, {"event": "order.changed", "order": order})
    return {"status": "Ready", "order": order}


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_CANCEL_ORDER)),
):
    restaurant_id = user_restaurant_id(user)
    order = update_order_status(db, order_id, ORDER_CANCELLED, restaurant_id=restaurant_id, user=user)
    await kitchen_ws_manager.broadcast(restaurant_id, {"event": "order.changed", "order": order})
    return {"status": "Cancelled", "order": order}


@router.websocket("/ws/kitchen")
async def kitchen_ws(websocket: WebSocket):
    restaurant_id = DEFAULT_RESTAURANT_ID
    await kitchen_ws_manager.connect(restaurant_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        kitchen_ws_manager.disconnect(restaurant_id, websocket)
