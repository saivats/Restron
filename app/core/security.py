from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import hmac
from jose import jwt
from passlib.context import CryptContext
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def receipt_token(order_id: int, restaurant_id: int) -> str:
    """Short signed token proving the holder was legitimately given this
    receipt link (e.g. via the checkout flow), so raw order_id enumeration
    can't be used to read another customer's/tenant's receipt.
    """
    message = f"receipt:{restaurant_id}:{order_id}".encode()
    digest = hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()
    return digest[:24]


def verify_receipt_token(order_id: int, restaurant_id: int, token: str | None) -> bool:
    if not token:
        return False
    expected = receipt_token(order_id, restaurant_id)
    return hmac.compare_digest(expected, token)
