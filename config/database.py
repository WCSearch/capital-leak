"""Database connection and configuration"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('https://vlbvrhotrlipaoedudys.supabase.co')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found. Create .env file.")

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
