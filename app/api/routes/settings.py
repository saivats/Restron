from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import CAN_MANAGE_PLAN, get_db, require_permission, require_user, user_restaurant_id
from app.models import models
from app.schemas.schemas import RestaurantSettingsUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.get("/settings/")
def get_restaurant_settings(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_PLAN)),
):
    restaurant = db.get(models.Restaurant, user_restaurant_id(user))
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "slug": restaurant.slug,
        "address": restaurant.address,
        "phone": restaurant.phone,
        "gstin": restaurant.gstin,
        "logo_url": restaurant.logo_url,
        "table_count": restaurant.table_count,
        "gst_rate": restaurant.gst_rate,
        "currency_symbol": restaurant.currency_symbol,
        "menu_pdf_url": restaurant.menu_pdf_url,
        "upi_id": restaurant.upi_id,
        "plan": restaurant.plan,
        "is_active": restaurant.is_active,
    }


@router.patch("/settings/")
def update_restaurant_settings(
    payload: RestaurantSettingsUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_PLAN)),
):
    restaurant_id = user_restaurant_id(user)
    restaurant = db.get(models.Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    before_state = {"name": restaurant.name, "address": restaurant.address, "phone": restaurant.phone}
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return {"status": "No changes"}

    try:
        for field, value in updates.items():
            setattr(restaurant, field, value)

        write_audit_log(
            db,
            action="restaurant.settings_updated",
            entity_type="restaurant",
            entity_id=restaurant.id,
            restaurant_id=restaurant_id,
            user=user,
            before_state=before_state,
            after_state=updates,
        )
        db.commit()
        return {"status": "Updated", "updated_fields": list(updates.keys())}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {exc}") from exc


@router.get("/status/")
def get_restaurant_status(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    restaurant = db.get(models.Restaurant, user_restaurant_id(user))
    if not restaurant:
        return {"is_active": False, "plan": "none", "plan_expires_at": None}

    return {
        "is_active": restaurant.is_active,
        "plan": restaurant.plan,
        "plan_expires_at": restaurant.plan_expires_at.isoformat() if restaurant.plan_expires_at else None,
        "name": restaurant.name,
    }
