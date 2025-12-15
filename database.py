import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use DATABASE_URL from environment, fallback to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./api_db.sqlite3")

# SQLite requires special connect_args
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
elif DATABASE_URL.startswith("postgresql://"):
    # Convert to pg8000 driver (pure Python, no system dependencies)
    pg8000_url = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://")
    engine = create_engine(pg8000_url)
else:
    # Other databases (MySQL, etc.)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
