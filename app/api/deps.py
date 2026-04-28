from typing import Callable, Iterable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM, DEFAULT_RESTAURANT_ID, SECRET_KEY
from app.db.database import SessionLocal
from app.models import models


CAN_VIEW_ANALYTICS = "analytics:read"
CAN_CANCEL_ORDER = "order:cancel"
CAN_CREATE_ORDER = "order:create"
CAN_READ_ORDER = "order:read"
CAN_UPDATE_ORDER = "order:update"
CAN_CHECKOUT = "checkout:write"
CAN_MANAGE_MENU = "menu:write"
CAN_READ_CUSTOMERS = "customers:read"
CAN_MANAGE_CUSTOMERS = "customers:write"
CAN_READ_INVENTORY = "inventory:read"
CAN_MANAGE_INVENTORY = "inventory:write"
CAN_READ_TABLES = "tables:read"
CAN_MANAGE_TABLES = "tables:write"
CAN_READ_AUDIT = "audit:read"
CAN_MANAGE_STAFF = "staff:write"
CAN_MANAGE_PLAN = "plan:write"


DEFAULT_ROLE_PERMISSIONS = {
    "owner": {
        CAN_VIEW_ANALYTICS,
        CAN_CANCEL_ORDER,
        CAN_CREATE_ORDER,
        CAN_READ_ORDER,
        CAN_UPDATE_ORDER,
        CAN_CHECKOUT,
        CAN_MANAGE_MENU,
        CAN_READ_CUSTOMERS,
        CAN_MANAGE_CUSTOMERS,
        CAN_READ_INVENTORY,
        CAN_MANAGE_INVENTORY,
        CAN_READ_TABLES,
        CAN_MANAGE_TABLES,
        CAN_READ_AUDIT,
        CAN_MANAGE_STAFF,
        CAN_MANAGE_PLAN,
    },
    "manager": {
        CAN_VIEW_ANALYTICS,
        CAN_CANCEL_ORDER,
        CAN_CREATE_ORDER,
        CAN_READ_ORDER,
        CAN_UPDATE_ORDER,
        CAN_CHECKOUT,
        CAN_MANAGE_MENU,
        CAN_READ_CUSTOMERS,
        CAN_MANAGE_CUSTOMERS,
        CAN_READ_INVENTORY,
        CAN_MANAGE_INVENTORY,
        CAN_READ_TABLES,
        CAN_MANAGE_TABLES,
        CAN_READ_AUDIT,
    },
    "cashier": {CAN_CREATE_ORDER, CAN_READ_ORDER, CAN_CHECKOUT, CAN_READ_CUSTOMERS, CAN_MANAGE_CUSTOMERS, CAN_READ_TABLES},
    "waiter": {CAN_CREATE_ORDER, CAN_READ_ORDER, CAN_READ_TABLES},
    "chef": {CAN_READ_ORDER, CAN_UPDATE_ORDER, CAN_READ_INVENTORY, CAN_MANAGE_INVENTORY},
    "superadmin": {"*"},
}

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _token_from_request(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return request.cookies.get("access_token")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = _token_from_request(request, credentials)
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    return db.query(models.User).filter(models.User.username == username, models.User.is_active == True).first()


def require_user(user: models.User | None = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def user_restaurant_id(user: models.User | None) -> int:
    return int(user.restaurant_id or DEFAULT_RESTAURANT_ID) if user else DEFAULT_RESTAURANT_ID


def role_has_permission(db: Session, user: models.User, permission: str) -> bool:
    if user.role == "superadmin":
        return True

    restaurant_id = user_restaurant_id(user)
    mapped_permissions = db.query(models.RolePermission.permission).filter(
        models.RolePermission.role == user.role,
        (models.RolePermission.restaurant_id == restaurant_id) | (models.RolePermission.restaurant_id.is_(None)),
    ).all()

    if mapped_permissions:
        values = {row[0] for row in mapped_permissions}
        return "*" in values or permission in values

    return permission in DEFAULT_ROLE_PERMISSIONS.get(user.role, set())


def require_permission(permission: str) -> Callable:
    def permission_checker(db: Session = Depends(get_db), user: models.User = Depends(require_user)):
        if not role_has_permission(db, user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return user

    return permission_checker


def require_role(roles: Iterable[str]) -> Callable:
    allowed = set(roles)

    def role_checker(user: models.User = Depends(require_user)):
        if user.role not in allowed and user.role != "superadmin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
        return user

    return role_checker
