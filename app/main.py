from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.deps import get_current_user, get_db
from app.api.routes import analytics, auth, checkout, customers, inventory, legacy, menu, orders, tables
from app.api.routes import qr as qr_routes
from app.api.routes import settings as settings_routes
from app.api.routes import staff as staff_routes
from app.api.routes import superadmin as superadmin_routes
from app.core.config import ALLOWED_ORIGINS, STATIC_DIR
from app.db.database import SessionLocal
from app.db.schema_guard import ensure_schema
from app.models import models

ensure_schema()

app = FastAPI(title="Restron POS API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(auth.router, prefix="/r/{slug}/auth", tags=["Authentication Slug"])
app.include_router(auth.router, tags=["Authentication Legacy"])
app.include_router(menu.router, prefix="/menu", tags=["Menu"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(orders.router, prefix="/order", tags=["Orders Legacy"])
app.include_router(checkout.router, prefix="/checkout", tags=["Checkout"])
app.include_router(customers.router, prefix="/customers", tags=["Customers"])
app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(tables.router, prefix="/tables", tags=["Tables"])
app.include_router(staff_routes.router, prefix="/staff", tags=["Staff"])
app.include_router(settings_routes.router, prefix="/restaurant", tags=["Restaurant Settings"])
app.include_router(qr_routes.router, prefix="/restaurant", tags=["QR Codes"])
app.include_router(superadmin_routes.router, prefix="/superadmin", tags=["Super Admin"])
app.include_router(legacy.router, tags=["Legacy Screen Compatibility"])

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def static_file(name: str) -> FileResponse:
    return FileResponse(STATIC_DIR / name)


def _resolve_restaurant(slug: str, db):
    return db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()


@app.get("/r/{slug}/login", response_class=HTMLResponse)
async def slug_login_page(slug: str):
    return static_file("login.html")


@app.get("/r/{slug}/mobile", response_class=HTMLResponse)
async def slug_mobile(slug: str):
    return static_file("menu.html")


@app.get("/r/{slug}/kitchen", response_class=HTMLResponse)
async def slug_kitchen(slug: str, user: models.User | None = Depends(get_current_user)):
    if not user or (user.role not in {"chef", "manager", "owner"} and user.role != "superadmin"):
        return static_file("login.html")
    return static_file("kitchen.html")


@app.get("/r/{slug}/waiter", response_class=HTMLResponse)
async def slug_waiter(slug: str, user: models.User | None = Depends(get_current_user)):
    if not user or (user.role not in {"waiter", "manager", "owner"} and user.role != "superadmin"):
        return static_file("login.html")
    return static_file("waiter.html")


@app.get("/r/{slug}/manager", response_class=HTMLResponse)
async def slug_manager(slug: str, user: models.User | None = Depends(get_current_user)):
    if not user or (user.role not in {"manager", "owner"} and user.role != "superadmin"):
        return static_file("login.html")
    return static_file("manager.html")


@app.get("/r/{slug}/owner", response_class=HTMLResponse)
async def slug_owner(slug: str, user: models.User | None = Depends(get_current_user)):
    if not user or (user.role not in {"owner"} and user.role != "superadmin"):
        return static_file("login.html")
    return static_file("owner.html")


@app.get("/r/{slug}/admin", response_class=HTMLResponse)
async def slug_admin(slug: str, user: models.User | None = Depends(get_current_user)):
    if not user or (user.role not in {"manager", "owner"} and user.role != "superadmin"):
        return static_file("login.html")
    return static_file("admin.html")


@app.get("/r/{slug}/receipt/{order_id}", response_class=HTMLResponse)
async def slug_receipt_page(slug: str, order_id: int):
    return static_file("receipt.html")


@app.get("/r/{slug}/receipt/{order_id}/data")
async def slug_receipt_data(slug: str, order_id: int, user: models.User | None = Depends(get_current_user)):
    from app.api.deps import user_restaurant_id
    from app.services.receipt_service import generate_receipt_logic
    db = SessionLocal()
    try:
        return generate_receipt_logic(order_id, db, restaurant_id=user_restaurant_id(user) if user else None)
    finally:
        db.close()


@app.get("/superadmin/login", response_class=HTMLResponse)
async def superadmin_login_page():
    return static_file("superadmin_login.html")


@app.get("/superadmin/dashboard", response_class=HTMLResponse)
async def superadmin_dashboard_page():
    return static_file("superadmin.html")


@app.get("/", response_class=HTMLResponse)
async def read_index():
    return static_file("menu.html")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return RedirectResponse(url="/r/default/login")


@app.get("/owner", response_class=HTMLResponse)
async def owner_dashboard(user: models.User | None = Depends(get_current_user)):
    slug = _get_user_slug(user)
    return RedirectResponse(url=f"/r/{slug}/owner")


@app.get("/manager", response_class=HTMLResponse)
async def manager_dashboard(user: models.User | None = Depends(get_current_user)):
    slug = _get_user_slug(user)
    return RedirectResponse(url=f"/r/{slug}/manager")


@app.get("/waiter", response_class=HTMLResponse)
async def waiter_dashboard(user: models.User | None = Depends(get_current_user)):
    slug = _get_user_slug(user)
    return RedirectResponse(url=f"/r/{slug}/waiter")


@app.get("/kitchen", response_class=HTMLResponse)
async def kitchen_dashboard(user: models.User | None = Depends(get_current_user)):
    slug = _get_user_slug(user)
    return RedirectResponse(url=f"/r/{slug}/kitchen")


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(user: models.User | None = Depends(get_current_user)):
    slug = _get_user_slug(user)
    return RedirectResponse(url=f"/r/{slug}/admin")


@app.get("/mobile", response_class=HTMLResponse)
async def mobile_app():
    return RedirectResponse(url="/r/default/mobile")


def _get_user_slug(user: models.User | None) -> str:
    if not user or not user.restaurant_id:
        return "default"
    db = SessionLocal()
    try:
        restaurant = db.get(models.Restaurant, user.restaurant_id)
        return restaurant.slug if restaurant and restaurant.slug else "default"
    finally:
        db.close()


@app.get("/manifest.json")
async def manifest():
    return FileResponse(
        STATIC_DIR / "manifest.json",
        media_type="application/manifest+json",
    )


@app.get("/sw.js")
async def service_worker():
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@app.get("/health")
def health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"
    finally:
        db.close()

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
