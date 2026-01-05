"""Database connection and configuration"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Try both possible environment variable names
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found. Create .env file with DATABASE_URL or NEXT_PUBLIC_SUPABASE_URL.")

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_engine():
    return engine

def test_connection():
    try:
        conn = engine.connect()
        conn.close()
        return True, "Connected"
    except Exception as e:
        return False, str(e)
