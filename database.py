from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- INSTRUCTIONS ---
# 1. Go to Supabase -> Connect -> URIs.
# 2. Make sure "Session pooler" is CHECKED/SELECTED (Port should be 6543).
# 3. Copy that long string.
# 4. Paste it below inside the quotes.
# 5. MANUALLY replace '[YOUR-PASSWORD]' with: Restron2025Shop

# 👇 PASTE YOUR LINK INSIDE THESE QUOTES 👇
SQLALCHEMY_DATABASE_URL = "postgresql://postgres.jzuvinbqupubrcwbcqxn:DesiZaika2025@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"
# (Note: I kept the password 'Restron2025Shop' in the link above as an example.
# If your link looks different, just paste yours and type 'Restron2025Shop' in the password section.)

# --- ENGINE SETUP ---
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # Local SQLite (Backup mode)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # Cloud Supabase (Real Production mode)
    # pool_pre_ping=True helps reconnect if the internet blinks
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()