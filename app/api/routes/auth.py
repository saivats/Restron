from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, user_restaurant_id
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.security import create_access_token, verify_password
from app.models import models

router = APIRouter()


@router.post("/token")
async def login(
    response: Response,
    slug: Optional[str] = None,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    restaurant = None
    restaurant_id = None

    if slug:
        restaurant = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")

        if not restaurant.is_active:
            raise HTTPException(status_code=403, detail="This account is inactive. Please contact Restron support.")

        if restaurant.plan_expires_at and restaurant.plan_expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="This account is inactive. Please contact Restron support.")

        restaurant_id = restaurant.id

    user_query = db.query(models.User).filter(
        models.User.username == form_data.username,
        models.User.is_active == True,
    )
    if restaurant_id:
        user_query = user_query.filter(models.User.restaurant_id == restaurant_id)

    user = user_query.first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if not restaurant and user.restaurant_id:
        restaurant = db.get(models.Restaurant, user.restaurant_id)
        if restaurant and not restaurant.is_active:
            raise HTTPException(status_code=403, detail="This account is inactive. Please contact Restron support.")
        if restaurant and restaurant.plan_expires_at and restaurant.plan_expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="This account is inactive. Please contact Restron support.")

    effective_restaurant_id = user_restaurant_id(user)
    effective_slug = ""
    if restaurant:
        effective_slug = restaurant.slug or "default"
    elif not slug:
        r = db.get(models.Restaurant, effective_restaurant_id)
        effective_slug = r.slug if r and r.slug else "default"

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "restaurant_id": effective_restaurant_id},
        expires_delta=access_token_expires,
    )

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")

    slug_prefix = f"/r/{effective_slug}"
    redirect_url = f"{slug_prefix}/mobile"
    if user.role == "owner":
        redirect_url = f"{slug_prefix}/owner"
    elif user.role == "manager":
        redirect_url = f"{slug_prefix}/manager"
    elif user.role == "waiter":
        redirect_url = f"{slug_prefix}/waiter"
    elif user.role == "chef":
        redirect_url = f"{slug_prefix}/kitchen"

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "redirect": redirect_url,
        "redirect_url": redirect_url,
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "Logged out"}
