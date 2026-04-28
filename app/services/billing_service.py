from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import DEFAULT_GST_RATE
from app.models import models


VALID_GST_RATES = {0.0, 5.0, 12.0, 18.0}


def normalize_gst_rate(rate: float | None) -> float:
    value = float(rate if rate is not None else DEFAULT_GST_RATE)
    return value if value in VALID_GST_RATES else DEFAULT_GST_RATE


def calculate_order_totals(line_items: list[dict], discount_percent: float = 0.0) -> dict:
    subtotal = round(sum(item["price"] * item["quantity"] for item in line_items), 2)
    discount_percent = max(0.0, min(float(discount_percent or 0.0), 100.0))
    discount_amount = round(subtotal * discount_percent / 100, 2)
    taxable_ratio = ((subtotal - discount_amount) / subtotal) if subtotal else 0

    breakdown = defaultdict(lambda: {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "gst": 0.0})
    for item in line_items:
        rate = normalize_gst_rate(item.get("gst_rate"))
        taxable_value = round(item["price"] * item["quantity"] * taxable_ratio, 2)
        gst_amount = round(taxable_value * rate / 100, 2)
        cgst = round(gst_amount / 2, 2)
        sgst = round(gst_amount - cgst, 2)
        bucket = breakdown[str(rate)]
        bucket["taxable"] = round(bucket["taxable"] + taxable_value, 2)
        bucket["cgst"] = round(bucket["cgst"] + cgst, 2)
        bucket["sgst"] = round(bucket["sgst"] + sgst, 2)
        bucket["gst"] = round(bucket["gst"] + gst_amount, 2)

    cgst_amount = round(sum(item["cgst"] for item in breakdown.values()), 2)
    sgst_amount = round(sum(item["sgst"] for item in breakdown.values()), 2)
    gst_amount = round(cgst_amount + sgst_amount, 2)

    return {
        "subtotal": subtotal,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "cgst_amount": cgst_amount,
        "sgst_amount": sgst_amount,
        "gst_amount": gst_amount,
        "gst_breakdown": dict(breakdown),
        "total_amount": round(subtotal - discount_amount + gst_amount, 2),
    }


def financial_year_for(moment: datetime) -> str:
    start_year = moment.year if moment.month >= 4 else moment.year - 1
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def next_invoice_number(db: Session, restaurant_id: int, moment: datetime) -> tuple[str, str, int]:
    financial_year = financial_year_for(moment)
    last_invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.restaurant_id == restaurant_id, models.Invoice.financial_year == financial_year)
        .order_by(models.Invoice.sequence_number.desc())
        .first()
    )
    sequence_number = (last_invoice.sequence_number if last_invoice else 0) + 1
    return f"INV-{financial_year}-{sequence_number:04d}", financial_year, sequence_number


def create_invoice_for_order(db: Session, order: models.Order, payment_method: str, paid_at: datetime) -> models.Invoice:
    existing = db.query(models.Invoice).filter(models.Invoice.order_id == order.id).first()
    if existing:
        return existing

    invoice_number, financial_year, sequence_number = next_invoice_number(db, order.restaurant_id, paid_at)
    invoice = models.Invoice(
        restaurant_id=order.restaurant_id,
        order_id=order.id,
        invoice_number=invoice_number,
        financial_year=financial_year,
        sequence_number=sequence_number,
        subtotal=order.subtotal,
        discount_amount=order.discount_applied,
        cgst_amount=order.cgst_amount,
        sgst_amount=order.sgst_amount,
        total_amount=order.total_amount,
        payment_method=payment_method,
        created_at=paid_at,
    )
    db.add(invoice)
    order.invoice_number = invoice_number
    return invoice
