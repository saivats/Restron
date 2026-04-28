from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CAN_MANAGE_TABLES, CAN_READ_TABLES, get_db, require_permission, user_restaurant_id
from app.models import models
from app.schemas.schemas import TableMerge, TableTransfer, TableUpdate
from app.services.table_service import merge_tables, table_dashboard, transfer_table

router = APIRouter()


@router.get("/")
def get_tables(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_TABLES)),
):
    return table_dashboard(db, restaurant_id=user_restaurant_id(user))


@router.get("/status")
def get_table_status(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_READ_TABLES)),
):
    data = table_dashboard(db, restaurant_id=user_restaurant_id(user))
    occupied = [table["table_number"] for table in data["tables"] if table["status"] == "Occupied"]
    return {"occupied_tables": occupied, **data}


@router.put("/{table_number}")
def update_table(
    table_number: int,
    payload: TableUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_TABLES)),
):
    restaurant_id = user_restaurant_id(user)
    table = db.query(models.Table).filter(
        models.Table.restaurant_id == restaurant_id,
        models.Table.table_number == table_number,
    ).first()
    if not table:
        table = models.Table(restaurant_id=restaurant_id, table_number=table_number, name=f"Table {table_number}")
        db.add(table)
    if payload.covers is not None:
        table.covers = payload.covers
    if payload.status is not None:
        table.status = payload.status
    db.commit()
    return {"status": "Updated", "table_number": table_number}


@router.post("/transfer")
def transfer(
    payload: TableTransfer,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_TABLES)),
):
    return transfer_table(
        db,
        restaurant_id=user_restaurant_id(user),
        from_table=payload.from_table,
        to_table=payload.to_table,
        user=user,
    )


@router.post("/merge")
def merge(
    payload: TableMerge,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_permission(CAN_MANAGE_TABLES)),
):
    return merge_tables(
        db,
        restaurant_id=user_restaurant_id(user),
        source_table=payload.source_table,
        target_table=payload.target_table,
        user=user,
    )
