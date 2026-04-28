from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import (
    BUSINESS_ADDRESS,
    BUSINESS_GSTIN,
    BUSINESS_NAME,
    BUSINESS_PHONE,
    BUSINESS_UPI_ID,
    DEFAULT_RESTAURANT_ID,
    DEFAULT_TABLE_COUNT,
)
from app.db.database import Base, SessionLocal, engine
from app.models import models


def _column_type(sqlite_type: str, postgres_type: str) -> str:
    return sqlite_type if engine.dialect.name == "sqlite" else postgres_type


def _add_column(conn, inspector, table_name: str, column_name: str, ddl: str) -> None:
    if table_name not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name not in columns:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))


def _ensure_columns() -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        bool_type = _column_type("BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE")
        nullable_int = _column_type("INTEGER", "INTEGER")
        datetime_type = _column_type("DATETIME", "TIMESTAMP")
        json_type = _column_type("JSON", "JSONB")

        for table_name in ("users", "menu_items", "customers", "orders", "order_items", "inventory_requests"):
            _add_column(conn, inspector, table_name, "restaurant_id", f"{nullable_int} NULL")

        user_columns = {
            "is_active": _column_type("BOOLEAN DEFAULT 1", "BOOLEAN DEFAULT TRUE") + " NOT NULL",
        }
        menu_columns = {
            "hindi_name": "VARCHAR DEFAULT ''",
            "hsn_code": "VARCHAR DEFAULT ''",
            "gst_rate": "FLOAT DEFAULT 5.0",
        }
        inventory_columns = {
            "archived": bool_type,
        }
        order_columns = {
            "kot_number": "VARCHAR",
            "invoice_number": "VARCHAR",
            "discount_percent": "FLOAT DEFAULT 0.0",
            "cgst_amount": "FLOAT DEFAULT 0.0",
            "sgst_amount": "FLOAT DEFAULT 0.0",
            "gst_breakdown": json_type,
            "updated_at": datetime_type,
            "cancelled_at": datetime_type,
            "closed_at": datetime_type,
            "archived": bool_type,
            "taken_by": "VARCHAR DEFAULT 'Customer'",
            "payment_method": "VARCHAR",
            "paid_at": datetime_type,
            "table_status": "VARCHAR DEFAULT 'Occupied'",
        }
        order_item_columns = {
            "menu_item_id": nullable_int,
            "line_total": "FLOAT DEFAULT 0.0",
            "gst_rate": "FLOAT DEFAULT 5.0",
            "hsn_code": "VARCHAR DEFAULT ''",
            "modifiers_json": json_type,
        }

        for name, ddl in user_columns.items():
            _add_column(conn, inspector, "users", name, ddl)
        for name, ddl in menu_columns.items():
            _add_column(conn, inspector, "menu_items", name, ddl)
        for name, ddl in inventory_columns.items():
            _add_column(conn, inspector, "inventory_requests", name, ddl)
        for name, ddl in order_columns.items():
            _add_column(conn, inspector, "orders", name, ddl)
        for name, ddl in order_item_columns.items():
            _add_column(conn, inspector, "order_items", name, ddl)


def _seed_foundation_rows() -> None:
    db = SessionLocal()
    try:
        restaurant = db.get(models.Restaurant, DEFAULT_RESTAURANT_ID)
        if not restaurant:
            restaurant = models.Restaurant(
                id=DEFAULT_RESTAURANT_ID,
                name=BUSINESS_NAME,
                address=BUSINESS_ADDRESS,
                phone=BUSINESS_PHONE,
                gstin=BUSINESS_GSTIN,
                upi_id=BUSINESS_UPI_ID,
            )
            db.add(restaurant)

        for table_number in range(1, DEFAULT_TABLE_COUNT + 1):
            exists = db.query(models.Table).filter(
                models.Table.restaurant_id == DEFAULT_RESTAURANT_ID,
                models.Table.table_number == table_number,
            ).first()
            if not exists:
                db.add(
                    models.Table(
                        restaurant_id=DEFAULT_RESTAURANT_ID,
                        table_number=table_number,
                        name=f"Table {table_number}",
                    )
                )

        for model in (models.User, models.MenuItem, models.Customer, models.Order, models.OrderItem, models.InventoryRequest):
            db.query(model).filter(model.restaurant_id.is_(None)).update(
                {model.restaurant_id: DEFAULT_RESTAURANT_ID},
                synchronize_session=False,
            )

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    Base.metadata.create_all(bind=engine)
    _seed_foundation_rows()
