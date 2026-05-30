from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CAN_MANAGE_MENU, get_current_user, get_db, require_permission, user_restaurant_id
from app.models import models
from app.schemas.schemas import AvailabilityUpdate, BulkMenuItemCreate, MenuItemCreate
from app.services.audit_service import write_audit_log

router = APIRouter()


def _parse_bulk_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    truthy = {"true", "yes", "1", "veg"}
    falsy = {"false", "no", "0", "non-veg", "non veg", "nonveg"}
    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    return None


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


@router.post("/bulk/")
def bulk_create_items(
    items: list[BulkMenuItemCreate],
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_MENU)),
):
    restaurant_id = user_restaurant_id(user)
    menu_items = []
    errors = []

    for index, item in enumerate(items, start=1):
        data = item.model_dump()
        name = str(data.get("name") or "").strip()
        category = str(data.get("category") or "").strip() or "General"

        if not name:
            errors.append({"row": index, "reason": "Name is required"})
            continue

        try:
            price = float(data.get("price"))
        except (TypeError, ValueError):
            errors.append({"row": index, "reason": "Price must be a positive number"})
            continue

        if price <= 0:
            errors.append({"row": index, "reason": "Price must be a positive number"})
            continue

        is_veg = _parse_bulk_bool(data.get("is_veg"))
        if is_veg is None:
            errors.append({"row": index, "reason": "is_veg must be true/false, yes/no, 1/0, veg/non-veg"})
            continue

        menu_items.append(
            models.MenuItem(
                restaurant_id=restaurant_id,
                name=name,
                price=price,
                category=category,
                is_veg=is_veg,
            )
        )

    if menu_items:
        db.add_all(menu_items)
        db.flush()
        write_audit_log(
            db,
            action="menu.bulk_created",
            entity_type="menu_item",
            entity_id="bulk",
            restaurant_id=restaurant_id,
            user=user,
            after_state={"imported": len(menu_items), "skipped": len(errors)},
        )
        db.commit()

    return {"imported": len(menu_items), "skipped": len(errors), "errors": errors}


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
