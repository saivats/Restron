from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import CAN_MANAGE_STAFF, get_db, require_permission, user_restaurant_id
from app.core.security import get_password_hash
from app.models import models
from app.schemas.schemas import StaffCreate
from app.services.audit_service import write_audit_log

router = APIRouter()

VALID_STAFF_ROLES = {"waiter", "manager", "chef", "cashier"}


@router.get("/")
def list_staff(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_STAFF)),
):
    restaurant_id = user_restaurant_id(user)
    staff = (
        db.query(models.User)
        .filter(models.User.restaurant_id == restaurant_id, models.User.is_active == True)
        .order_by(models.User.role.asc(), models.User.username.asc())
        .all()
    )
    return [
        {
            "id": member.id,
            "username": member.username,
            "role": member.role,
            "is_active": member.is_active,
        }
        for member in staff
    ]


@router.post("/")
def create_staff(
    payload: StaffCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_STAFF)),
):
    if payload.role not in VALID_STAFF_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_STAFF_ROLES))}")

    restaurant_id = user_restaurant_id(user)
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    try:
        new_user = models.User(
            restaurant_id=restaurant_id,
            username=payload.username,
            password_hash=get_password_hash(payload.password),
            role=payload.role,
            is_active=True,
        )
        db.add(new_user)
        db.flush()
        write_audit_log(
            db,
            action="staff.created",
            entity_type="user",
            entity_id=new_user.id,
            restaurant_id=restaurant_id,
            user=user,
            after_state={"username": new_user.username, "role": new_user.role},
        )
        db.commit()
        return {"status": "Created", "id": new_user.id, "username": new_user.username, "role": new_user.role}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create staff: {exc}") from exc


@router.delete("/{user_id}")
def remove_staff(
    user_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_STAFF)),
):
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    restaurant_id = user_restaurant_id(user)
    target = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.restaurant_id == restaurant_id,
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Staff member not found")

    if target.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the owner account")

    try:
        target.is_active = False
        write_audit_log(
            db,
            action="staff.deactivated",
            entity_type="user",
            entity_id=target.id,
            restaurant_id=restaurant_id,
            user=user,
            before_state={"is_active": True},
            after_state={"is_active": False},
        )
        db.commit()
        return {"status": "Removed", "id": target.id, "username": target.username}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to remove staff: {exc}") from exc
