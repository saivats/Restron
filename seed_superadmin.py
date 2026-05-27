import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app.core.security import get_password_hash, verify_password
from app.db.database import SessionLocal
from app.db.schema_guard import ensure_schema
from app.models import models


def main():
    username = os.environ.get("SUPERADMIN_USERNAME")
    password = os.environ.get("SUPERADMIN_PASSWORD")

    if not username or not password:
        print("ERROR: SUPERADMIN_USERNAME and SUPERADMIN_PASSWORD must be set in environment or .env file.")
        sys.exit(1)

    print("Ensuring database schema is up to date...")
    ensure_schema()

    db = SessionLocal()
    try:
        existing = db.query(models.SuperAdmin).filter(models.SuperAdmin.username == username).first()
        if existing:
            existing.password_hash = get_password_hash(password)
            db.commit()
            print(f"SuperAdmin '{username}' already exists — password updated.")
        else:
            admin = models.SuperAdmin(
                username=username,
                password_hash=get_password_hash(password),
            )
            db.add(admin)
            db.commit()
            print(f"SuperAdmin '{username}' created successfully.")
    finally:
        db.close()

    print("Done.")


if __name__ == "__main__":
    main()
