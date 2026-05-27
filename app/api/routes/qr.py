import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user, user_restaurant_id
from app.core.config import PUBLIC_BASE_URL
from app.models import models

router = APIRouter()


@router.get("/qr/{table_number}")
def generate_table_qr(
    table_number: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    try:
        import qrcode
    except ImportError:
        raise HTTPException(status_code=501, detail="qrcode library not installed")

    restaurant = db.get(models.Restaurant, user_restaurant_id(user))
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    slug = restaurant.slug or "default"
    url = f"{PUBLIC_BASE_URL}/r/{slug}/mobile?table={table_number}"

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=qr_table_{table_number}.png"},
    )
