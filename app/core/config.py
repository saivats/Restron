from functools import lru_cache
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field, field_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # Keeps local syntax checks working until requirements are installed.
    from pydantic import BaseModel as BaseSettings

    class BaseSettings(BaseSettings):
        def __init__(self, **data):
            env_data = {}
            for name, field in self.model_fields.items():
                alias = field.alias or name
                if alias in os.environ:
                    env_data[alias] = os.environ[alias]
            env_data.update(data)
            super().__init__(**env_data)

    class SettingsConfigDict(dict):
        pass


load_dotenv()

APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT
STATIC_DIR = PROJECT_ROOT / "static"
RECEIPT_DIR = STATIC_DIR / "receipts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    database_url: str = Field(default="sqlite:///./restron.db", alias="DATABASE_URL")
    allowed_origins_raw: str = Field(default="http://localhost:8000,http://127.0.0.1:8000", alias="ALLOWED_ORIGINS")

    business_name: str = Field(default="Restron POS", alias="BUSINESS_NAME")
    business_tagline: str = Field(default="Cloud-powered restaurant billing", alias="BUSINESS_TAGLINE")
    business_location: str = Field(default="India", alias="BUSINESS_LOCATION")
    business_address: str = Field(default="Set BUSINESS_ADDRESS in .env", alias="BUSINESS_ADDRESS")
    business_phone: str = Field(default="Set BUSINESS_PHONE in .env", alias="BUSINESS_PHONE")
    business_gstin: str = Field(default="", alias="BUSINESS_GSTIN")
    business_upi_id: str = Field(default="", alias="BUSINESS_UPI_ID")

    default_gst_rate: float = Field(default=5.0, alias="DEFAULT_GST_RATE")
    default_restaurant_id: int = Field(default=1, alias="DEFAULT_RESTAURANT_ID")
    default_table_count: int = Field(default=10, alias="DEFAULT_TABLE_COUNT")
    max_tables_legacy: int | None = Field(default=None, alias="MAX_TABLES")
    invoice_reset_policy: str = Field(default="financial_year", alias="INVOICE_RESET_POLICY")

    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_key: str | None = Field(default=None, alias="SUPABASE_KEY")
    public_base_url: str = Field(default="http://localhost:8000", alias="PUBLIC_BASE_URL")

    @field_validator("secret_key")
    @classmethod
    def require_secret_key(cls, value: str) -> str:
        if not value or value.strip() == "":
            raise ValueError(
                "SECRET_KEY environment variable is not set. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def require_shift_safe_token(cls, value: int) -> int:
        if value < 480:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be at least 480 for POS shift safety.")
        return value

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Backward-compatible constants for the existing modules.
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
SQLALCHEMY_DATABASE_URL = settings.database_url
ALLOWED_ORIGINS = settings.allowed_origins
BUSINESS_NAME = settings.business_name
BUSINESS_TAGLINE = settings.business_tagline
BUSINESS_LOCATION = settings.business_location
BUSINESS_ADDRESS = settings.business_address
BUSINESS_PHONE = settings.business_phone
BUSINESS_GSTIN = settings.business_gstin
BUSINESS_UPI_ID = settings.business_upi_id
DEFAULT_GST_RATE = settings.default_gst_rate
DEFAULT_RESTAURANT_ID = settings.default_restaurant_id
DEFAULT_TABLE_COUNT = settings.default_table_count if os.getenv("DEFAULT_TABLE_COUNT") else (settings.max_tables_legacy or settings.default_table_count)
PUBLIC_BASE_URL = settings.public_base_url.rstrip("/")
SUPABASE_URL = settings.supabase_url
SUPABASE_KEY = settings.supabase_key
