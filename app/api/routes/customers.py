import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import (
    CAN_MANAGE_CUSTOMERS,
    CAN_READ_CUSTOMERS,
    get_current_user,
    get_db,
    require_permission,
    user_restaurant_id,
)
from app.models import models
from app.schemas.schemas import CustomerCreate
from app.services.audit_service import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
def list_customers(
    search: str = "",
    sort: str = "alpha",
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_CUSTOMERS)),
):
    restaurant_id = user_restaurant_id(user)
    query = db.query(models.Customer).filter(models.Customer.restaurant_id == restaurant_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(models.Customer.name.ilike(pattern), models.Customer.phone.ilike(pattern)))
    if sort == "alpha":
        query = query.order_by(models.Customer.name.asc(), models.Customer.phone.asc())
    return query.limit(200).all()


@router.post("/")
def create_customer(
    c: CustomerCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_CUSTOMERS)),
):
    restaurant_id = user_restaurant_id(user)
    try:
        existing = db.query(models.Customer).filter(
            models.Customer.restaurant_id == restaurant_id,
            models.Customer.phone == c.phone,
        ).first()
        if existing:
            before = {
                "name": existing.name,
                "relation": existing.relation,
                "discount_percent": existing.discount_percent,
            }
            existing.name = c.name
            existing.relation = c.relation
            existing.discount_percent = c.discount_percent
            write_audit_log(
                db,
                action="customer.updated",
                entity_type="customer",
                entity_id=existing.id,
                restaurant_id=restaurant_id,
                user=user,
                before_state=before,
                after_state=c.model_dump(),
            )
            db.commit()
            return {"status": "Updated", "id": existing.id, "name": existing.name}

        new_cust = models.Customer(restaurant_id=restaurant_id, **c.model_dump())
        db.add(new_cust)
        db.flush()
        write_audit_log(
            db,
            action="customer.created",
            entity_type="customer",
            entity_id=new_cust.id,
            restaurant_id=restaurant_id,
            user=user,
            after_state=c.model_dump(),
        )
        db.commit()
        return {"status": "Created", "id": new_cust.id, "name": new_cust.name}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Customer create/update failed phone=%s restaurant_id=%s: %s", c.phone, restaurant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to save customer. Please try again.") from exc


@router.put("/")
def update_customer(
    c: CustomerCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_CUSTOMERS)),
):
    return create_customer(c, db, user)


@router.get("/lookup/{phone}")
def lookup_customer(
    phone: str,
    slug: str | None = None,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user),
):
    if user:
        restaurant_id = user_restaurant_id(user)
    elif slug:
        restaurant = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")
        restaurant_id = restaurant.id
    else:
        # No session and no slug to resolve the correct tenant — refuse
        # rather than silently falling back to the default restaurant's
        # customer data.
        raise HTTPException(status_code=400, detail="Restaurant context required")

    cust = db.query(models.Customer).filter(
        models.Customer.restaurant_id == restaurant_id,
        models.Customer.phone == phone,
    ).first()
    if not cust:
        return {"exists": False}
    return {
        "exists": True,
        "id": cust.id,
        "name": cust.name,
        "phone": cust.phone,
        "relation": cust.relation,
        "discount_percent": cust.discount_percent,
        "visit_count": cust.visit_count,
    }


@router.get("/{phone}")
def get_customer(
    phone: str,
    slug: str | None = None,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user),
):
    if user:
        restaurant_id = user_restaurant_id(user)
    elif slug:
        restaurant = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")
        restaurant_id = restaurant.id
    else:
        raise HTTPException(status_code=400, detail="Restaurant context required")

    cust = db.query(models.Customer).filter(
        models.Customer.restaurant_id == restaurant_id,
        models.Customer.phone == phone,
    ).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Not found")
    return cust
