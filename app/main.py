from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.deps import get_current_user
from app.api.routes import analytics, auth, checkout, customers, inventory, legacy, menu, orders, tables
from app.core.config import ALLOWED_ORIGINS, STATIC_DIR
from app.db.database import SessionLocal
from app.db.schema_guard import ensure_schema
from app.models import models

ensure_schema()

app = FastAPI(title="Restron POS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(auth.router, tags=["Authentication Legacy"])
app.include_router(menu.router, prefix="/menu", tags=["Menu"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(orders.router, prefix="/order", tags=["Orders Legacy"])
app.include_router(checkout.router, prefix="/checkout", tags=["Checkout"])
app.include_router(customers.router, prefix="/customers", tags=["Customers"])
app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(tables.router, prefix="/tables", tags=["Tables"])
app.include_router(legacy.router, tags=["Legacy Screen Compatibility"])

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def static_file(name: str) -> FileResponse:
    return FileResponse(STATIC_DIR / name)


def role_page(user: models.User | None, roles: set[str], filename: str) -> FileResponse:
    if not user or (user.role not in roles and user.role != "superadmin"):
        return static_file("login.html")
    return static_file(filename)


@app.get("/", response_class=HTMLResponse)
async def read_index():
    return static_file("menu.html")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return static_file("login.html")


@app.get("/owner", response_class=HTMLResponse)
async def owner_dashboard(user: models.User | None = Depends(get_current_user)):
    return role_page(user, {"owner"}, "owner.html")


@app.get("/manager", response_class=HTMLResponse)
async def manager_dashboard(user: models.User | None = Depends(get_current_user)):
    return role_page(user, {"manager", "owner"}, "manager.html")


@app.get("/waiter", response_class=HTMLResponse)
async def waiter_dashboard(user: models.User | None = Depends(get_current_user)):
    return role_page(user, {"waiter", "manager", "owner"}, "waiter.html")


@app.get("/kitchen", response_class=HTMLResponse)
async def kitchen_dashboard(user: models.User | None = Depends(get_current_user)):
    return role_page(user, {"chef", "manager", "owner"}, "kitchen.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(user: models.User | None = Depends(get_current_user)):
    return role_page(user, {"manager", "owner"}, "admin.html")


@app.get("/mobile", response_class=HTMLResponse)
async def mobile_app():
    return static_file("menu.html")


@app.get("/manifest.json")
async def manifest():
    return static_file("manifest.json")


@app.get("/service-worker.js")
async def service_worker():
    return static_file("service-worker.js")


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

    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status}
