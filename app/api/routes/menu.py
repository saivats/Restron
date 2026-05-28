from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CAN_MANAGE_MENU, get_current_user, get_db, require_permission, user_restaurant_id
from app.models import models
from app.schemas.schemas import AvailabilityUpdate, MenuItemCreate
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.get("/")
def read_menu(
    slug: str | None = None,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user),
):
    restaurant_id = user_restaurant_id(user)
    if not user and slug:
        restaurant = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
        if restaurant:
            restaurant_id = restaurant.id
    return (
        db.query(models.MenuItem)
        .filter(models.MenuItem.restaurant_id == restaurant_id)
        .order_by(models.MenuItem.category.asc(), models.MenuItem.name.asc())
        .all()
    )


@router.post("/")
def create_item(
    item: MenuItemCreate = Depends(),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_MENU)),
):
    restaurant_id = user_restaurant_id(user)
    menu_item = models.MenuItem(restaurant_id=restaurant_id, **item.model_dump())
    db.add(menu_item)
    db.flush()
    write_audit_log(
        db,
        action="menu.created",
        entity_type="menu_item",
        entity_id=menu_item.id,
        restaurant_id=restaurant_id,
        user=user,
        after_state=item.model_dump(),
    )
    db.commit()
    db.refresh(menu_item)
    return {"status": "Added", "id": menu_item.id, "name": menu_item.name}


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_MENU)),
):
    restaurant_id = user_restaurant_id(user)
    item = db.query(models.MenuItem).filter(
        models.MenuItem.restaurant_id == restaurant_id,
        models.MenuItem.id == item_id,
    ).first()
    if item:
        before = {"name": item.name, "price": item.price, "category": item.category}
        db.delete(item)
        write_audit_log(
            db,
            action="menu.deleted",
            entity_type="menu_item",
            entity_id=item_id,
            restaurant_id=restaurant_id,
            user=user,
            before_state=before,
        )
        db.commit()
    return {"status": "Deleted"}


@router.put("/{item_id}/availability")
def toggle_stock(
    item_id: int,
    s: AvailabilityUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_MENU)),
):
    restaurant_id = user_restaurant_id(user)
    item = db.query(models.MenuItem).filter(
        models.MenuItem.restaurant_id == restaurant_id,
        models.MenuItem.id == item_id,
    ).first()
    if item:
        before = {"is_available": item.is_available}
        item.is_available = s.is_available
        write_audit_log(
            db,
            action="menu.availability_changed",
            entity_type="menu_item",
            entity_id=item_id,
            restaurant_id=restaurant_id,
            user=user,
            before_state=before,
            after_state={"is_available": item.is_available},
        )
        db.commit()
    return {"status": "Updated"}
