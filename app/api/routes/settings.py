from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import CAN_MANAGE_PLAN, get_db, require_permission, require_user, user_restaurant_id
from app.core.plans import limits_for_plan
from app.models import models
from app.schemas.schemas import RestaurantSettingsUpdate
from app.services.audit_service import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _apply_growth_preview_expiry(db: Session, restaurant: models.Restaurant) -> None:
    expires_at = _as_utc(restaurant.growth_preview_expires_at)
    if (
        restaurant.plan == "growth"
        and restaurant.plan_set_by == "system"
        and expires_at
        and expires_at < datetime.now(timezone.utc)
    ):
        restaurant.plan = "starter"
        db.commit()


def _plan_expired(restaurant: models.Restaurant) -> bool:
    expires_at = _as_utc(restaurant.plan_expires_at)
    return bool(expires_at and expires_at < datetime.now(timezone.utc))


@router.get("/settings/")
def get_restaurant_settings(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
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
        "auto_print_kot": restaurant.auto_print_kot,
        "latitude": restaurant.latitude,
        "longitude": restaurant.longitude,
        "geofence_radius_meters": restaurant.geofence_radius_meters,
        "reservations_enabled": bool(restaurant.reservations_enabled),
        "reservation_open_time": restaurant.reservation_open_time,
        "reservation_close_time": restaurant.reservation_close_time,
        "reservation_slot_duration": restaurant.reservation_slot_duration,
        "reservation_max_party": restaurant.reservation_max_party,
        "reservation_advance_days": restaurant.reservation_advance_days,
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
        if "table_count" in updates:
            table_limit = limits_for_plan(restaurant.plan).get("max_tables")
            if table_limit is not None and updates["table_count"] is not None and updates["table_count"] > table_limit:
                return JSONResponse(
                    status_code=403,
                    content={"error": "table_limit_reached", "limit": table_limit, "plan": restaurant.plan},
                )

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
        logger.exception("Failed to update settings restaurant_id=%s: %s", restaurant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update settings.") from exc


@router.get("/status/")
def get_restaurant_status(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    restaurant = db.get(models.Restaurant, user_restaurant_id(user))
    if not restaurant:
        return {"is_active": False, "plan": "none", "expired": True, "plan_expires_at": None}

    _apply_growth_preview_expiry(db, restaurant)
    growth_preview_expires_at = _as_utc(restaurant.growth_preview_expires_at)
    growth_preview_expired = bool(
        restaurant.growth_preview_used
        and growth_preview_expires_at
        and growth_preview_expires_at < datetime.now(timezone.utc)
        and restaurant.plan_set_by == "system"
    )
    limits = limits_for_plan(restaurant.plan)
    staff_count = (
        db.query(func.count(models.User.id))
        .filter(models.User.restaurant_id == restaurant.id, models.User.is_active == True)
        .scalar()
        or 0
    )
    table_limit = limits.get("max_tables")
    staff_limit = limits.get("max_staff")

    return {
        "is_active": restaurant.is_active,
        "plan": restaurant.plan,
        "expired": _plan_expired(restaurant) or growth_preview_expired,
        "plan_expires_at": restaurant.plan_expires_at.isoformat() if restaurant.plan_expires_at else None,
        "at_table_limit": table_limit is not None and (restaurant.table_count or 0) >= table_limit,
        "at_staff_limit": staff_limit is not None and staff_count >= staff_limit,
        "growth_preview_used": bool(restaurant.growth_preview_used),
        "growth_preview_expires_at": restaurant.growth_preview_expires_at.isoformat() if restaurant.growth_preview_expires_at else None,
        "name": restaurant.name,
    }


@router.post("/growth-preview/")
def start_growth_preview(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    restaurant = db.get(models.Restaurant, user_restaurant_id(user))
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if restaurant.growth_preview_used:
        return JSONResponse(status_code=403, content={"error": "One-time preview already used"})

    preview_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    restaurant.growth_preview_used = True
    restaurant.growth_preview_expires_at = preview_expires_at
    restaurant.plan = "growth"
    restaurant.plan_set_by = "system"
    db.commit()
    return {"preview_expires_at": preview_expires_at.isoformat()}


@router.get("/geofence/{slug}")
def get_restaurant_geofence(
    slug: str,
    db: Session = Depends(get_db),
):
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return {
        "latitude": restaurant.latitude,
        "longitude": restaurant.longitude,
        "geofence_radius_meters": restaurant.geofence_radius_meters,
    }
