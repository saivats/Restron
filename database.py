from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 1. Try to get the Cloud Database URL from the environment
# If not found, fall back to local SQLite (for when you run it on your laptop)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./restron.db")

# 2. Configure connection args (SQLite needs a specific flag, Postgres does not)
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL (Supabase) configuration
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()