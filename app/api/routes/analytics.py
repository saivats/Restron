from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CAN_VIEW_ANALYTICS, get_db, require_permission, user_restaurant_id
from app.models import models
from app.services.analytics_service import history_report, owner_analytics

router = APIRouter()


@router.get("/summary")
def get_analytics(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_VIEW_ANALYTICS)),
):
    data = owner_analytics(db, restaurant_id=user_restaurant_id(user))
    return {
        "total_revenue": data["revenue"]["total"],
        "total_orders": data["total_orders"],
        "popular_items": data["best_sellers_month"],
        **data,
    }


@router.get("/history")
def get_history(
    date: str | None = None,
    month: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_VIEW_ANALYTICS)),
):
    return history_report(db, restaurant_id=user_restaurant_id(user), date=date, month=month)
