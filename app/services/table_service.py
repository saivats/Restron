from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import models
from app.services.audit_service import write_audit_log
from app.services.order_service import ACTIVE_ORDER_STATUSES


def table_dashboard(db: Session, *, restaurant_id: int) -> dict:
    tables = (
        db.query(models.Table)
        .filter(models.Table.restaurant_id == restaurant_id)
        .order_by(models.Table.table_number.asc())
        .all()
    )
    running_orders = {
        order.table_number: order
        for order in db.query(models.Order)
        .filter(
            models.Order.restaurant_id == restaurant_id,
            models.Order.archived == False,
            models.Order.order_type == "Dine-in",
            models.Order.status.in_(ACTIVE_ORDER_STATUSES),
        )
        .all()
    }

    payload = []
    for table in tables:
        order = running_orders.get(table.table_number)
        table.status = "Occupied" if order else "Available"
        table.active_order_id = order.id if order else None
        payload.append(
            {
                "table_number": table.table_number,
                "name": table.name or f"Table {table.table_number}",
                "status": table.status,
                "covers": table.covers,
                "merged_into_table_id": table.merged_into_table_id,
                "order_id": order.id if order else None,
                "bill_amount": order.total_amount if order else 0,
                "subtotal": order.subtotal if order else 0,
                "cgst_amount": order.cgst_amount if order else 0,
                "sgst_amount": order.sgst_amount if order else 0,
                "gst_amount": order.gst_amount if order else 0,
                "items_summary": order.items_summary if order else "",
                "created_at": order.created_at.strftime("%H:%M") if order and order.created_at else "",
            }
        )

    db.commit()
    return {"tables": payload}


def transfer_table(
    db: Session,
    *,
    restaurant_id: int,
    from_table: int,
    to_table: int,
    user: models.User | None = None,
) -> dict:
    order = (
        db.query(models.Order)
        .filter(
            models.Order.restaurant_id == restaurant_id,
            models.Order.table_number == from_table,
            models.Order.status.in_(ACTIVE_ORDER_STATUSES),
            models.Order.archived == False,
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="No active order on source table")

    before = {"table_number": order.table_number}
    order.table_number = to_table
    for table_number, status, active_order_id in ((from_table, "Available", None), (to_table, "Occupied", order.id)):
        table = db.query(models.Table).filter(
            models.Table.restaurant_id == restaurant_id,
            models.Table.table_number == table_number,
        ).first()
        if table:
            table.status = status
            table.active_order_id = active_order_id

    write_audit_log(
        db,
        action="table.transfer",
        entity_type="order",
        entity_id=order.id,
        restaurant_id=restaurant_id,
        user=user,
        before_state=before,
        after_state={"table_number": to_table},
    )
    db.commit()
    return {"status": "Transferred", "order_id": order.id, "from_table": from_table, "to_table": to_table}


def merge_tables(
    db: Session,
    *,
    restaurant_id: int,
    source_table: int,
    target_table: int,
    user: models.User | None = None,
) -> dict:
    source = db.query(models.Table).filter(
        models.Table.restaurant_id == restaurant_id,
        models.Table.table_number == source_table,
    ).first()
    target = db.query(models.Table).filter(
        models.Table.restaurant_id == restaurant_id,
        models.Table.table_number == target_table,
    ).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="Table not found")

    source.merged_into_table_id = target.id
    source.status = "Merged"
    target.covers = (target.covers or 0) + (source.covers or 0)
    write_audit_log(
        db,
        action="table.merge",
        entity_type="table",
        entity_id=source.id,
        restaurant_id=restaurant_id,
        user=user,
        before_state={"source_table": source_table, "target_table": target_table},
        after_state={"merged": True},
    )
    db.commit()
    return {"status": "Merged", "source_table": source_table, "target_table": target_table}
