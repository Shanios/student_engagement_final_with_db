# backend/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")

# PostgreSQL / Supabase engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,        # avoids stale connections
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# Test the connection
try:
    with engine.connect() as conn:
        print("✓ Database connection successful!")
except Exception as e:
    print(f"✗ Database connection failed: {e}")