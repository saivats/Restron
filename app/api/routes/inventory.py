from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    CAN_MANAGE_INVENTORY,
    CAN_READ_INVENTORY,
    get_db,
    require_permission,
    user_restaurant_id,
)
from app.models import models
from app.schemas.schemas import IngredientCreate, InventoryCreate
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.get("/")
def get_inventory_requests(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_INVENTORY)),
):
    return (
        db.query(models.InventoryRequest)
        .filter(models.InventoryRequest.restaurant_id == user_restaurant_id(user), models.InventoryRequest.archived == False)
        .order_by(models.InventoryRequest.created_at.desc())
        .all()
    )


@router.post("/")
def create_inventory_request(
    req: InventoryCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_INVENTORY)),
):
    restaurant_id = user_restaurant_id(user)
    request = models.InventoryRequest(restaurant_id=restaurant_id, item_name=req.item_name)
    db.add(request)
    db.flush()
    write_audit_log(
        db,
        action="inventory.requested",
        entity_type="inventory_request",
        entity_id=request.id,
        restaurant_id=restaurant_id,
        user=user,
        after_state=req.model_dump(),
    )
    db.commit()
    return {"status": "Requested", "id": request.id}


@router.delete("/")
def clear_inventory_requests(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_INVENTORY)),
):
    restaurant_id = user_restaurant_id(user)
    count = (
        db.query(models.InventoryRequest)
        .filter(models.InventoryRequest.restaurant_id == restaurant_id, models.InventoryRequest.archived == False)
        .update({models.InventoryRequest.archived: True}, synchronize_session=False)
    )
    write_audit_log(
        db,
        action="inventory.requests_archived",
        entity_type="inventory_request",
        entity_id=None,
        restaurant_id=restaurant_id,
        user=user,
        after_state={"archived_count": count},
    )
    db.commit()
    return {"status": "Archived", "count": count}


@router.get("/ingredients")
def list_ingredients(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_INVENTORY)),
):
    return (
        db.query(models.Ingredient)
        .filter(models.Ingredient.restaurant_id == user_restaurant_id(user), models.Ingredient.is_active == True)
        .order_by(models.Ingredient.name.asc())
        .all()
    )


@router.post("/ingredients")
def create_ingredient(
    ingredient: IngredientCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_INVENTORY)),
):
    restaurant_id = user_restaurant_id(user)
    record = models.Ingredient(restaurant_id=restaurant_id, **ingredient.model_dump())
    db.add(record)
    db.flush()
    write_audit_log(
        db,
        action="inventory.ingredient_created",
        entity_type="ingredient",
        entity_id=record.id,
        restaurant_id=restaurant_id,
        user=user,
        after_state=ingredient.model_dump(),
    )
    db.commit()
    return {"status": "Created", "id": record.id}


@router.get("/low-stock")
def low_stock(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_INVENTORY)),
):
    rows = (
        db.query(models.Ingredient)
        .filter(
            models.Ingredient.restaurant_id == user_restaurant_id(user),
            models.Ingredient.is_active == True,
            models.Ingredient.current_stock <= models.Ingredient.min_stock_alert,
        )
        .order_by(models.Ingredient.name.asc())
        .all()
    )
    return rows
