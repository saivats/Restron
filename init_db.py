from app.core.security import get_password_hash
from app.db.database import SessionLocal
from app.db.schema_guard import ensure_schema
from app.models import models


DEFAULT_USERS = [
    ("owner", "owner123", "owner"),
    ("manager", "manager123", "manager"),
    ("cashier", "cashier123", "cashier"),
    ("waiter", "waiter123", "waiter"),
    ("chef", "chef123", "chef"),
]


def main():
    print("Initializing database...")
    ensure_schema()

    db = SessionLocal()
    try:
        for username, password, role in DEFAULT_USERS:
            user = db.query(models.User).filter(models.User.username == username).first()
            if user:
                user.role = role
                if not user.restaurant_id:
                    user.restaurant_id = 1
                continue
            db.add(
                models.User(
                    username=username,
                    password_hash=get_password_hash(password),
                    role=role,
                    restaurant_id=1,
                    is_active=True,
                )
            )
        db.commit()
    finally:
        db.close()

    print("Done. Default logins: owner/owner123, manager/manager123, cashier/cashier123, waiter/waiter123, chef/chef123")


if __name__ == "__main__":
    main()
