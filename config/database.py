"""Database connection and configuration with comprehensive debugging"""
import os
import sys
import traceback
from dotenv import load_dotenv

# Import debug utilities first
try:
    from .debug_utils import log_debug, log_environment_info, check_database_imports
    DEBUG_AVAILABLE = True
except ImportError:
    DEBUG_AVAILABLE = False
    def log_debug(msg, level="INFO"):
        print(f"[{level}] {msg}", file=sys.stderr)
        sys.stderr.flush()

# Log environment info at module load time
log_debug("=" * 80, "INFO")
log_debug("Loading database.py module", "INFO")
log_debug("=" * 80, "INFO")

if DEBUG_AVAILABLE:
    log_environment_info()
    check_database_imports()

# Load environment variables
log_debug("Loading .env file", "DEBUG")
try:
    load_dotenv()
    log_debug("Successfully loaded .env", "DEBUG")
except Exception as e:
    log_debug(f"Error loading .env: {e}", "ERROR")

# Import SQLAlchemy with error handling
log_debug("Importing SQLAlchemy", "DEBUG")
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    log_debug("Successfully imported SQLAlchemy", "DEBUG")
except ImportError as e:
    log_debug(f"Failed to import SQLAlchemy: {e}", "ERROR")
    log_debug(f"Traceback:\n{traceback.format_exc()}", "ERROR")
    raise

# Check for psycopg2
log_debug("Checking for psycopg2 availability", "DEBUG")
PSYCOPG2_AVAILABLE = False
PSYCOPG2_VERSION = None
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
    PSYCOPG2_VERSION = psycopg2.__version__
    log_debug(f"psycopg2 is available: version {PSYCOPG2_VERSION}", "INFO")
except ImportError as e:
    log_debug(f"psycopg2 import failed: {e}", "ERROR")
    log_debug("This may cause issues with PostgreSQL connections", "WARNING")
    log_debug("Checking for psycopg2-binary as alternative...", "DEBUG")
    try:
        # psycopg2-binary imports as psycopg2
        import psycopg2
        PSYCOPG2_AVAILABLE = True
        PSYCOPG2_VERSION = psycopg2.__version__
        log_debug(f"psycopg2-binary is available: version {PSYCOPG2_VERSION}", "INFO")
    except ImportError:
        log_debug("psycopg2-binary also not found", "ERROR")

# Get database URL from environment
log_debug("Reading DATABASE_URL from environment", "DEBUG")

# BUG FIX: The original code had os.getenv('https://vlbvrhotrlipaoedudys.supabase.co')
# which passes the URL as the variable name instead of 'DATABASE_URL'
DATABASE_URL = os.getenv('DATABASE_URL')

# If DATABASE_URL is not set, try SUPABASE_URL as fallback
if not DATABASE_URL:
    log_debug("DATABASE_URL not found, checking for SUPABASE_URL", "WARNING")
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    if SUPABASE_URL:
        log_debug(f"Found SUPABASE_URL: {SUPABASE_URL[:30]}...", "DEBUG")
        # For Supabase, construct the PostgreSQL connection URL
        # Format: postgresql://postgres:[password]@[host]:5432/postgres
        DATABASE_URL = SUPABASE_URL
    else:
        log_debug("No database configuration found in environment!", "ERROR")
        log_debug("Available environment variables:", "DEBUG")
        for key in sorted(os.environ.keys()):
            if any(x in key.upper() for x in ['DB', 'DATABASE', 'SUPABASE', 'POSTGRES', 'SQL']):
                value = os.environ[key]
                masked = value[:10] + "..." if len(value) > 10 else "***"
                log_debug(f"  {key}: {masked}", "DEBUG")

        raise ValueError(
            "DATABASE_URL not found in environment. "
            "Please create a .env file with DATABASE_URL or set SUPABASE_URL. "
            "See .env.example for reference."
        )

log_debug(f"Using DATABASE_URL: {DATABASE_URL[:30]}...", "INFO")

# Create database engine with error handling
log_debug("Creating SQLAlchemy engine", "DEBUG")
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False  # Set to True for SQL query debugging
    )
    log_debug("Successfully created SQLAlchemy engine", "INFO")
except Exception as e:
    log_debug(f"Failed to create engine: {e}", "ERROR")
    log_debug(f"DATABASE_URL format: {DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else 'Invalid format'}", "DEBUG")
    log_debug(f"Traceback:\n{traceback.format_exc()}", "ERROR")
    raise

# Create session maker
log_debug("Creating SessionLocal", "DEBUG")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_engine():
    """Get the database engine"""
    log_debug("get_engine() called", "DEBUG")
    return engine

def test_connection():
    """Test database connection with detailed error reporting"""
    log_debug("Testing database connection", "INFO")
    try:
        log_debug("Attempting to connect...", "DEBUG")
        conn = engine.connect()
        log_debug("Connection successful!", "INFO")

        # Try a simple query
        result = conn.execute("SELECT version()")
        version = result.fetchone()[0]
        log_debug(f"PostgreSQL version: {version}", "INFO")

        conn.close()
        log_debug("Connection closed successfully", "DEBUG")
        return True, "Connected successfully"
    except Exception as e:
        error_msg = str(e)
        log_debug(f"Connection failed: {error_msg}", "ERROR")
        log_debug(f"Error type: {type(e).__name__}", "ERROR")
        log_debug(f"Traceback:\n{traceback.format_exc()}", "ERROR")

        # Provide helpful error messages
        if "password authentication failed" in error_msg:
            return False, f"Authentication failed: Check your database password. {error_msg}"
        elif "could not connect to server" in error_msg:
            return False, f"Could not connect to server: Check host and port. {error_msg}"
        elif "database" in error_msg and "does not exist" in error_msg:
            return False, f"Database does not exist: {error_msg}"
        elif "psycopg2" in error_msg or "driver" in error_msg:
            return False, f"Database driver issue: {error_msg}. Check that psycopg2-binary is installed."
        else:
            return False, f"Connection error: {error_msg}"

def get_db_connection():
    """Get a raw database connection (for backward compatibility)"""
    log_debug("get_db_connection() called", "DEBUG")
    try:
        return engine.raw_connection()
    except Exception as e:
        log_debug(f"Failed to get raw connection: {e}", "ERROR")
        raise

# Test connection on module load (only in development)
if os.getenv('ENVIRONMENT') == 'development' or os.getenv('TEST_DB_ON_LOAD') == 'true':
    log_debug("Testing database connection on module load", "INFO")
    success, message = test_connection()
    if success:
        log_debug(f"Database connection OK: {message}", "INFO")
    else:
        log_debug(f"Database connection FAILED: {message}", "ERROR")

log_debug("database.py module loaded successfully", "INFO")
log_debug("=" * 80, "INFO")
