from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 1. Get the DB URL from environment variable (Cloud) or use local file (Laptop)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./restron.db")

# 2. Fix the URL if it starts with "postgres://" (SQLAlchemy needs "postgresql://")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Create the Engine
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # SQLite settings (Local)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL settings (Cloud)
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()