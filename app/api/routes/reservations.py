import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, user_restaurant_id
from app.core.rate_limit import enforce_rate_limit, record_failed_attempt
from app.models import models
from app.schemas.schemas import ReservationCreate, ReservationUpdate

router = APIRouter()

VALID_STATUSES = {"confirmed", "seated", "completed", "no_show", "cancelled"}


def _generate_confirmation_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"RSV-{random_part}"


def _parse_time(time_str: str) -> tuple[int, int]:
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def _time_to_minutes(time_str: str) -> int:
    hours, minutes = _parse_time(time_str)
    return hours * 60 + minutes


def _minutes_to_time(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


@router.get("/config/{slug}")
def get_reservation_config(slug: str, db: Session = Depends(get_db)):
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return {
        "enabled": bool(restaurant.reservations_enabled),
        "open_time": restaurant.reservation_open_time or "11:00",
        "close_time": restaurant.reservation_close_time or "22:00",
        "slot_duration": restaurant.reservation_slot_duration or 30,
        "max_party": restaurant.reservation_max_party or 10,
        "advance_days": restaurant.reservation_advance_days or 30,
        "restaurant_name": restaurant.name,
    }


@router.get("/slots/{slug}")
def get_available_slots(
    slug: str,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    party_size: int = Query(2, ge=1),
    db: Session = Depends(get_db),
):
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if not restaurant.reservations_enabled:
        raise HTTPException(status_code=400, detail="Reservations are not enabled")

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") from exc

    today = datetime.now(timezone.utc).date()
    max_date = today + timedelta(days=restaurant.reservation_advance_days or 30)

    if target_date < today:
        raise HTTPException(status_code=400, detail="Cannot book in the past")
    if target_date > max_date:
        raise HTTPException(status_code=400, detail="Date too far in advance")
    if party_size > (restaurant.reservation_max_party or 10):
        raise HTTPException(status_code=400, detail="Party size exceeds maximum")

    existing_reservations = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.restaurant_id == restaurant.id,
            models.Reservation.reservation_date == date,
            models.Reservation.status.in_(["confirmed", "seated"]),
        )
        .all()
    )

    booked_slots = {}
    for reservation in existing_reservations:
        slot_key = reservation.reservation_time
        booked_slots[slot_key] = booked_slots.get(slot_key, 0) + 1

    open_minutes = _time_to_minutes(restaurant.reservation_open_time or "11:00")
    close_minutes = _time_to_minutes(restaurant.reservation_close_time or "22:00")
    slot_duration = restaurant.reservation_slot_duration or 30
    table_count = restaurant.table_count or 10

    max_concurrent = max(1, table_count // 3)

    slots = []
    current_minutes = open_minutes
    while current_minutes + slot_duration <= close_minutes:
        time_str = _minutes_to_time(current_minutes)
        booked_count = booked_slots.get(time_str, 0)
        available = booked_count < max_concurrent

        if target_date == today:
            now_minutes = datetime.now(timezone.utc).hour * 60 + datetime.now(timezone.utc).minute
            if current_minutes <= now_minutes:
                available = False

        slots.append({
            "time": time_str,
            "available": available,
            "remaining": max(0, max_concurrent - booked_count),
        })
        current_minutes += slot_duration

    return {"date": date, "slots": slots, "max_concurrent": max_concurrent}


@router.post("/book/{slug}")
def create_reservation(
    slug: str,
    payload: ReservationCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    enforce_rate_limit("reservation_book", client_ip, client_ip, max_attempts=10)
    record_failed_attempt("reservation_book", client_ip, client_ip)

    restaurant = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if not restaurant.reservations_enabled:
        raise HTTPException(status_code=400, detail="Reservations are not enabled")

    try:
        target_date = datetime.strptime(payload.reservation_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format") from exc

    today = datetime.now(timezone.utc).date()
    max_date = today + timedelta(days=restaurant.reservation_advance_days or 30)

    if target_date < today:
        raise HTTPException(status_code=400, detail="Cannot book in the past")
    if target_date > max_date:
        raise HTTPException(status_code=400, detail="Date too far in advance")
    if payload.party_size > (restaurant.reservation_max_party or 10):
        raise HTTPException(status_code=400, detail="Party size exceeds maximum")

    existing_count = (
        db.query(models.Reservation)
        .filter(
            models.Reservation.restaurant_id == restaurant.id,
            models.Reservation.reservation_date == payload.reservation_date,
            models.Reservation.reservation_time == payload.reservation_time,
            models.Reservation.status.in_(["confirmed", "seated"]),
        )
        .count()
    )

    table_count = restaurant.table_count or 10
    max_concurrent = max(1, table_count // 3)

    if existing_count >= max_concurrent:
        raise HTTPException(status_code=409, detail="This time slot is no longer available")

    for _ in range(10):
        code = _generate_confirmation_code()
        if not db.query(models.Reservation).filter(models.Reservation.confirmation_code == code).first():
            break
    else:
        raise HTTPException(status_code=500, detail="Failed to generate unique confirmation code")

    reservation = models.Reservation(
        restaurant_id=restaurant.id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        party_size=payload.party_size,
        reservation_date=payload.reservation_date,
        reservation_time=payload.reservation_time,
        status="confirmed",
        special_requests=payload.special_requests,
        confirmation_code=code,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return {
        "id": reservation.id,
        "confirmation_code": reservation.confirmation_code,
        "customer_name": reservation.customer_name,
        "party_size": reservation.party_size,
        "date": reservation.reservation_date,
        "time": reservation.reservation_time,
        "status": reservation.status,
        "restaurant_name": restaurant.name,
    }


@router.get("/lookup/{confirmation_code}")
def lookup_reservation(confirmation_code: str, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else None
    enforce_rate_limit("reservation_lookup", client_ip, client_ip, max_attempts=20)
    record_failed_attempt("reservation_lookup", client_ip, client_ip)

    reservation = (
        db.query(models.Reservation)
        .filter(models.Reservation.confirmation_code == confirmation_code)
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    restaurant = db.get(models.Restaurant, reservation.restaurant_id)

    return {
        "id": reservation.id,
        "confirmation_code": reservation.confirmation_code,
        "customer_name": reservation.customer_name,
        "customer_phone": reservation.customer_phone,
        "party_size": reservation.party_size,
        "date": reservation.reservation_date,
        "time": reservation.reservation_time,
        "status": reservation.status,
        "special_requests": reservation.special_requests,
        "restaurant_name": restaurant.name if restaurant else "Unknown",
        "created_at": reservation.created_at.isoformat() if reservation.created_at else None,
    }


@router.get("/")
def list_reservations(
    date: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(["manager", "owner"])),
):
    restaurant_id = user_restaurant_id(user)
    query = db.query(models.Reservation).filter(models.Reservation.restaurant_id == restaurant_id)

    if date:
        query = query.filter(models.Reservation.reservation_date == date)
    if status:
        query = query.filter(models.Reservation.status == status)

    reservations = query.order_by(models.Reservation.reservation_date, models.Reservation.reservation_time).all()

    return [
        {
            "id": r.id,
            "confirmation_code": r.confirmation_code,
            "customer_name": r.customer_name,
            "customer_phone": r.customer_phone,
            "party_size": r.party_size,
            "date": r.reservation_date,
            "time": r.reservation_time,
            "status": r.status,
            "special_requests": r.special_requests,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reservations
    ]


@router.patch("/{reservation_id}")
def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(["manager", "owner"])),
):
    restaurant_id = user_restaurant_id(user)
    reservation = (
        db.query(models.Reservation)
        .filter(models.Reservation.id == reservation_id, models.Reservation.restaurant_id == restaurant_id)
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if payload.status:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
        reservation.status = payload.status
        if payload.status == "cancelled":
            reservation.cancelled_at = datetime.now(timezone.utc)

    db.commit()
    return {"status": "updated", "reservation_id": reservation.id, "new_status": reservation.status}


@router.delete("/{reservation_id}")
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(["manager", "owner"])),
):
    restaurant_id = user_restaurant_id(user)
    reservation = (
        db.query(models.Reservation)
        .filter(models.Reservation.id == reservation_id, models.Reservation.restaurant_id == restaurant_id)
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    reservation.status = "cancelled"
    reservation.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "cancelled", "reservation_id": reservation.id}
