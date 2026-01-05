"""Database connection and configuration"""
import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug: Check if psycopg2 is available
try:
    import psycopg2
    logger.info(f"✓ psycopg2 successfully imported: {psycopg2.__version__}")
except ImportError as e:
    logger.error(f"✗ Failed to import psycopg2: {e}")
    logger.error(f"Python version: {sys.version}")
    logger.error(f"Installed packages:")
    try:
        import pkg_resources
        for pkg in pkg_resources.working_set:
            if 'psycopg' in pkg.key.lower():
                logger.error(f"  - {pkg.key}: {pkg.version}")
    except Exception as pkg_error:
        logger.error(f"Could not list packages: {pkg_error}")

    # Try psycopg2-binary as fallback
    try:
        import psycopg2.extensions
        logger.info("✓ psycopg2.extensions accessible despite import error")
    except ImportError:
        logger.error("✗ psycopg2.extensions also not accessible")
        logger.error("Please ensure 'psycopg2-binary' is in requirements.txt")
        raise ImportError(
            "Failed to import psycopg2. "
            "Make sure 'psycopg2-binary>=2.9.0' is in requirements.txt. "
            f"Error: {e}"
        ) from e

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    error_msg = "DATABASE_URL not found. Create .env file or set environment variable."
    logger.error(error_msg)
    raise ValueError(error_msg)

logger.info(f"Creating database engine with URL: {DATABASE_URL.split('@')[0]}@***")

try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False  # Set to True for SQL debugging
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("✓ Database engine created successfully")
except Exception as e:
    logger.error(f"✗ Failed to create database engine: {e}")
    raise

def get_engine():
    return engine

def test_connection():
    try:
        conn = engine.connect()
        conn.close()
        return True, "Connected"
    except Exception as e:
        return False, str(e)
