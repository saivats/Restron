import os
import sys

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import engine, SessionLocal, Base
from app.models import models


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _col_type(sqlite_type: str, pg_type: str) -> str:
    return sqlite_type if engine.dialect.name == "sqlite" else pg_type


def step_1_create_tables():
    print("[1/8] Creating new tables (superadmins, and any missing)...")
    Base.metadata.create_all(bind=engine)
    print("      Done.")


def step_2_add_restaurant_columns():
    print("[2/8] Adding new columns to restaurants table...")
    new_columns = {
        "slug": "VARCHAR",
        "owner_email": "VARCHAR",
        "table_count": "INTEGER DEFAULT 10",
        "gst_rate": "FLOAT DEFAULT 5.0",
        "currency_symbol": "VARCHAR DEFAULT '₹'",
        "is_active": _col_type("BOOLEAN DEFAULT 1 NOT NULL", "BOOLEAN DEFAULT TRUE NOT NULL"),
        "plan": "VARCHAR DEFAULT 'trial'",
        "plan_set_by": "VARCHAR DEFAULT 'system'",
        "plan_expires_at": _col_type("DATETIME", "TIMESTAMP"),
        "growth_preview_used": _col_type("BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
        "growth_preview_expires_at": _col_type("DATETIME", "TIMESTAMP"),
        "menu_pdf_url": "VARCHAR DEFAULT ''",
        "auto_print_kot": _col_type("BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
        "latitude": "FLOAT",
        "longitude": "FLOAT",
        "geofence_radius_meters": "INTEGER DEFAULT 50",
    }
    with engine.begin() as conn:
        inspector = inspect(conn)
        if not _table_exists(inspector, "restaurants"):
            print("      restaurants table does not exist — skipping (create_all should have made it).")
            return

        for col_name, col_ddl in new_columns.items():
            if not _column_exists(inspector, "restaurants", col_name):
                conn.execute(text(f"ALTER TABLE restaurants ADD COLUMN {col_name} {col_ddl}"))
                print(f"      Added column: restaurants.{col_name}")
            else:
                print(f"      Column already exists: restaurants.{col_name}")
    print("      Done.")


def step_3_backfill_default_restaurant():
    print("[3/8] Backfilling default restaurant slug...")
    db = SessionLocal()
    try:
        restaurant = db.get(models.Restaurant, 1)
        if restaurant:
            if not restaurant.slug:
                restaurant.slug = "default"
                print("      Set slug='default' on restaurant ID 1.")
            else:
                print(f"      Restaurant ID 1 already has slug='{restaurant.slug}'.")

            if restaurant.is_active is None:
                restaurant.is_active = True
            if not restaurant.plan:
                restaurant.plan = "trial"
            if not restaurant.table_count:
                restaurant.table_count = 10

            db.commit()
        else:
            print("      No restaurant with ID 1 found — creating default.")
            default = models.Restaurant(
                id=1,
                name="Default Restaurant",
                slug="default",
                is_active=True,
                plan="trial",
                table_count=10,
            )
            db.add(default)
            db.commit()
    finally:
        db.close()
    print("      Done.")


def step_4_backfill_restaurant_ids():
    print("[4/8] Backfilling restaurant_id=1 on orphan rows...")
    db = SessionLocal()
    try:
        backfill_models = [
            models.User, models.MenuItem, models.Customer,
            models.Order, models.OrderItem, models.InventoryRequest,
        ]
        for model in backfill_models:
            count = db.query(model).filter(model.restaurant_id.is_(None)).update(
                {model.restaurant_id: 1}, synchronize_session=False
            )
            if count:
                print(f"      {model.__tablename__}: backfilled {count} rows.")
        db.commit()
    finally:
        db.close()
    print("      Done.")


def step_5_fix_customer_phone_constraint():
    print("[5/8] Fixing customer phone uniqueness constraint...")
    if engine.dialect.name == "sqlite":
        print("      SQLite does not support DROP CONSTRAINT — skipping. Composite constraint is in model definition.")
        return

    with engine.connect() as conn:
        inspector = inspect(conn)
        if not _table_exists(inspector, "customers"):
            print("      customers table does not exist — skipping.")
            return

        statements = [
            ("drop old phone index", "DROP INDEX IF EXISTS ix_customers_phone"),
            (
                "drop old phone unique constraint",
                "ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_phone_key",
            ),
            (
                "add restaurant-scoped phone constraint",
                "ALTER TABLE customers ADD CONSTRAINT uq_customer_phone_restaurant UNIQUE (phone, restaurant_id)",
            ),
        ]

        for label, ddl in statements:
            try:
                conn.execute(text(ddl))
                conn.commit()
                print(f"      {label}: ok")
            except Exception as exc:
                conn.rollback()
                print(f"      {label}: {exc}")

    print("      Done.")


def step_6_add_order_archived_column():
    print("[6/8] Ensuring orders.archived column exists...")
    with engine.begin() as conn:
        inspector = inspect(conn)
        if _column_exists(inspector, "orders", "archived"):
            print("      Column already exists.")
        else:
            ddl = _col_type("BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE")
            conn.execute(text(f"ALTER TABLE orders ADD COLUMN archived {ddl}"))
            print("      Added orders.archived column.")
    print("      Done.")


def step_7_create_indexes():
    print("[7/8] Creating indexes (if missing)...")
    if engine.dialect.name == "sqlite":
        print("      SQLite — indexes created by create_all. Skipping.")
    else:
        with engine.begin() as conn:
            safe_indexes = [
                ("ix_restaurants_slug", "restaurants", "slug"),
                ("ix_orders_archived", "orders", "archived"),
            ]
            for idx_name, table, column in safe_indexes:
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})"))
                    print(f"      Index {idx_name}: ok")
                except Exception as exc:
                    print(f"      Index {idx_name}: {exc}")
    print("      Done.")


def step_8_summary():
    print("[8/8] Migration summary:")
    db = SessionLocal()
    try:
        restaurant_count = db.query(models.Restaurant).count()
        user_count = db.query(models.User).count()
        order_count = db.query(models.Order).count()
        superadmin_count = db.query(models.SuperAdmin).count()
        print(f"      Restaurants: {restaurant_count}")
        print(f"      Users: {user_count}")
        print(f"      Orders: {order_count}")
        print(f"      SuperAdmins: {superadmin_count}")
    finally:
        db.close()
    print("\n[OK] Migration complete. Safe to restart the server.")


def main():
    print("=" * 60)
    print("  Restron Multi-Tenant Migration Script")
    print("=" * 60)
    print()

    step_1_create_tables()
    step_2_add_restaurant_columns()
    step_3_backfill_default_restaurant()
    step_4_backfill_restaurant_ids()
    step_5_fix_customer_phone_constraint()
    step_6_add_order_archived_column()
    step_7_create_indexes()
    step_8_summary()


if __name__ == "__main__":
    main()
