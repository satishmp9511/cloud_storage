import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Render ya Cloud DB ka URL env se uthayega, warna local fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage.db")

# Agar URL postgresql se start hota hai toh standard engine banta hai
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Supabase ke sath secure connection ke liye sslmode require kiya gaya hai
engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
