import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_superadmin
from app.core.plans import PLAN_LIMITS
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import models
from app.schemas.schemas import RestaurantCreate, RestaurantUpdate

router = APIRouter()


@router.post("/token")
def superadmin_login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    admin = db.query(models.SuperAdmin).filter(models.SuperAdmin.username == form_data.username).first()
    if not admin or not verify_password(form_data.password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Invalid superadmin credentials")

    token = create_access_token(
        data={"sub": admin.username, "role": "superadmin"},
        expires_delta=timedelta(hours=12),
    )
    response.set_cookie(key="superadmin_token", value=token, httponly=True, samesite="lax")
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def superadmin_logout(response: Response):
    response.delete_cookie("superadmin_token")
    return {"status": "Logged out"}


@router.get("/restaurants/")
def list_restaurants(
    db: Session = Depends(get_db),
    admin: models.SuperAdmin = Depends(require_superadmin),
):
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    restaurants = db.query(models.Restaurant).order_by(models.Restaurant.id.asc()).all()

    result = []
    for restaurant in restaurants:
        order_count = (
            db.query(func.count(models.Order.id))
            .filter(
                models.Order.restaurant_id == restaurant.id,
                models.Order.created_at >= thirty_days_ago,
            )
            .scalar()
            or 0
        )
        result.append({
            "id": restaurant.id,
            "name": restaurant.name,
            "slug": restaurant.slug,
            "plan": restaurant.plan,
            "plan_set_by": restaurant.plan_set_by,
            "plan_expires_at": restaurant.plan_expires_at.isoformat() if restaurant.plan_expires_at else None,
            "is_active": restaurant.is_active,
            "created_at": restaurant.created_at.isoformat() if restaurant.created_at else None,
            "order_count_30d": order_count,
            "table_count": restaurant.table_count,
            "address": restaurant.address,
            "phone": restaurant.phone,
            "growth_preview_used": bool(restaurant.growth_preview_used),
            "growth_preview_expires_at": restaurant.growth_preview_expires_at.isoformat() if restaurant.growth_preview_expires_at else None,
        })
    return result


@router.post("/restaurants/")
def create_restaurant(
    payload: RestaurantCreate,
    db: Session = Depends(get_db),
    admin: models.SuperAdmin = Depends(require_superadmin),
):
    existing_slug = db.query(models.Restaurant).filter(models.Restaurant.slug == payload.slug).first()
    if existing_slug:
        raise HTTPException(status_code=409, detail="Slug already exists")

    existing_user = db.query(models.User).filter(models.User.username == payload.owner_username).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Owner username already exists")

    generated_password = payload.owner_password or secrets.token_urlsafe(12)

    try:
        created_at = datetime.now(timezone.utc)
        restaurant = models.Restaurant(
            name=payload.restaurant_name,
            slug=payload.slug,
            address=payload.address,
            phone=payload.phone,
            table_count=payload.table_count,
            plan="trial",
            plan_set_by="system",
            plan_expires_at=created_at + timedelta(days=PLAN_LIMITS["trial"]["duration_days"]),
            gst_rate=payload.gst_rate,
            owner_email=payload.owner_email,
            is_active=True,
            created_at=created_at,
        )
        db.add(restaurant)
        db.flush()

        owner_user = models.User(
            restaurant_id=restaurant.id,
            username=payload.owner_username,
            password_hash=get_password_hash(generated_password),
            role="owner",
            is_active=True,
        )
        db.add(owner_user)

        for table_number in range(1, payload.table_count + 1):
            db.add(models.Table(
                restaurant_id=restaurant.id,
                table_number=table_number,
                name=f"Table {table_number}",
            ))

        db.commit()
        return {
            "status": "Created",
            "restaurant": {
                "id": restaurant.id,
                "name": restaurant.name,
                "slug": restaurant.slug,
                "plan": restaurant.plan,
            },
            "owner": {
                "username": payload.owner_username,
                "password": generated_password,
            },
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create restaurant: {exc}") from exc


@router.patch("/restaurants/{restaurant_id}")
def update_restaurant(
    restaurant_id: int,
    payload: RestaurantUpdate,
    db: Session = Depends(get_db),
    admin: models.SuperAdmin = Depends(require_superadmin),
):
    restaurant = db.get(models.Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return {"status": "No changes"}

    if "plan_expires_at" in updates and updates["plan_expires_at"]:
        updates["plan_expires_at"] = datetime.fromisoformat(updates["plan_expires_at"]).replace(tzinfo=timezone.utc)
    if "plan" in updates:
        updates["plan_set_by"] = "superadmin"

    try:
        for field, value in updates.items():
            setattr(restaurant, field, value)
        db.commit()
        return {"status": "Updated", "updated_fields": list(updates.keys())}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update restaurant: {exc}") from exc


@router.delete("/restaurants/{restaurant_id}")
def delete_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    admin: models.SuperAdmin = Depends(require_superadmin),
):
    restaurant = db.get(models.Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    restaurant.is_active = False
    db.commit()
    return {"status": "Deactivated", "id": restaurant_id, "name": restaurant.name}


@router.get("/restaurants/{restaurant_id}/stats")
def restaurant_stats(
    restaurant_id: int,
    db: Session = Depends(get_db),
    admin: models.SuperAdmin = Depends(require_superadmin),
):
    restaurant = db.get(models.Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    closed_statuses = ["CLOSED", "Paid", "Completed"]
    order_count = (
        db.query(func.count(models.Order.id))
        .filter(models.Order.restaurant_id == restaurant_id)
        .scalar()
        or 0
    )
    revenue_total = (
        db.query(func.sum(models.Order.total_amount))
        .filter(
            models.Order.restaurant_id == restaurant_id,
            models.Order.status.in_(closed_statuses),
        )
        .scalar()
        or 0
    )
    last_order = (
        db.query(models.Order.created_at)
        .filter(models.Order.restaurant_id == restaurant_id)
        .order_by(models.Order.created_at.desc())
        .first()
    )

    return {
        "restaurant_id": restaurant_id,
        "name": restaurant.name,
        "order_count": order_count,
        "revenue_total": round(float(revenue_total), 2),
        "last_activity": last_order[0].isoformat() if last_order and last_order[0] else None,
    }
