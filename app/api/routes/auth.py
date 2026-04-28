from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.api.deps import get_db, user_restaurant_id
from app.core.security import verify_password, create_access_token
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.models import models

router = APIRouter()

@router.post("/token")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "restaurant_id": user_restaurant_id(user)},
        expires_delta=access_token_expires,
    )

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")

    redirect_url = "/mobile"
    if user.role == "owner":
        redirect_url = "/owner"
    elif user.role == "manager":
        redirect_url = "/manager"
    elif user.role == "waiter":
        redirect_url = "/waiter"
    elif user.role == "chef":
        redirect_url = "/kitchen"

    return {"access_token": access_token, "token_type": "bearer", "redirect": redirect_url}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "Logged out"}
