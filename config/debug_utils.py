"""Debug utilities for troubleshooting deployment issues"""
import os
import sys
import traceback
from datetime import datetime


def log_debug(message, level="INFO"):
    """Print debug message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {message}", file=sys.stderr)
    sys.stderr.flush()


def log_environment_info():
    """Log detailed environment information"""
    log_debug("=" * 80, "DEBUG")
    log_debug("ENVIRONMENT DIAGNOSTICS", "DEBUG")
    log_debug("=" * 80, "DEBUG")

    # Python version
    log_debug(f"Python Version: {sys.version}", "DEBUG")
    log_debug(f"Python Executable: {sys.executable}", "DEBUG")

    # Working directory
    log_debug(f"Current Working Directory: {os.getcwd()}", "DEBUG")

    # Python path
    log_debug("Python Path:", "DEBUG")
    for path in sys.path:
        log_debug(f"  - {path}", "DEBUG")

    # Environment variables
    log_debug("Key Environment Variables:", "DEBUG")
    env_vars_to_check = [
        'DATABASE_URL', 'SUPABASE_URL', 'SUPABASE_KEY',
        'HOME', 'USER', 'PATH', 'VIRTUAL_ENV', 'PYTHONPATH'
    ]
    for var in env_vars_to_check:
        value = os.getenv(var, '<NOT SET>')
        # Mask sensitive values
        if 'URL' in var or 'KEY' in var or 'PASSWORD' in var:
            if value != '<NOT SET>':
                value = value[:10] + "..." + value[-10:] if len(value) > 20 else "***MASKED***"
        log_debug(f"  {var}: {value}", "DEBUG")

    # Check if running on Streamlit Cloud
    log_debug(f"Running on Streamlit Cloud: {is_streamlit_cloud()}", "DEBUG")

    # File system checks
    paths_to_check = [
        '/mount/admin/install_path',
        '/mount/src',
        '/home/adminuser',
        os.path.expanduser('~/.streamlit'),
        '.env'
    ]
    log_debug("File System Checks:", "DEBUG")
    for path in paths_to_check:
        exists = os.path.exists(path)
        is_dir = os.path.isdir(path) if exists else False
        is_file = os.path.isfile(path) if exists else False
        log_debug(f"  {path}: exists={exists}, is_dir={is_dir}, is_file={is_file}", "DEBUG")

    # Check installed packages
    log_debug("Checking critical packages:", "DEBUG")
    packages_to_check = ['psycopg2', 'sqlalchemy', 'streamlit', 'pandas']
    for package in packages_to_check:
        try:
            __import__(package)
            log_debug(f"  ✓ {package} is installed", "DEBUG")
        except ImportError as e:
            log_debug(f"  ✗ {package} is NOT installed: {e}", "ERROR")

    log_debug("=" * 80, "DEBUG")


def is_streamlit_cloud():
    """Detect if running on Streamlit Cloud"""
    # Streamlit Cloud specific paths
    streamlit_cloud_indicators = [
        '/mount/src' in os.getcwd(),
        os.path.exists('/home/adminuser'),
        'STREAMLIT_SHARING_MODE' in os.environ,
        'STREAMLIT_SERVER_HEADLESS' in os.environ
    ]
    return any(streamlit_cloud_indicators)


def check_database_imports():
    """Check which database drivers are available"""
    log_debug("Checking database driver imports:", "DEBUG")

    drivers = {
        'psycopg2': None,
        'psycopg2-binary': 'psycopg2',
        'psycopg': None,
        'pg8000': None,
        'asyncpg': None
    }

    available_drivers = []

    for driver_name, import_name in drivers.items():
        module_name = import_name if import_name else driver_name
        try:
            module = __import__(module_name)
            version = getattr(module, '__version__', 'unknown')
            log_debug(f"  ✓ {driver_name} (import as '{module_name}'): v{version}", "DEBUG")
            available_drivers.append(module_name)
        except ImportError as e:
            log_debug(f"  ✗ {driver_name} (import as '{module_name}'): {e}", "DEBUG")

    if available_drivers:
        log_debug(f"Available drivers: {', '.join(available_drivers)}", "INFO")
        return available_drivers[0]
    else:
        log_debug("WARNING: No PostgreSQL drivers found!", "ERROR")
        return None


def safe_import(module_name, package=None):
    """Safely import a module with detailed error logging"""
    try:
        log_debug(f"Attempting to import: {module_name}", "DEBUG")
        module = __import__(module_name, fromlist=[package] if package else [])
        log_debug(f"Successfully imported: {module_name}", "DEBUG")
        return module
    except ImportError as e:
        log_debug(f"Failed to import {module_name}: {e}", "ERROR")
        log_debug(f"Traceback:\n{traceback.format_exc()}", "ERROR")
        raise
    except Exception as e:
        log_debug(f"Unexpected error importing {module_name}: {e}", "ERROR")
        log_debug(f"Traceback:\n{traceback.format_exc()}", "ERROR")
        raise


def check_install_path_file():
    """Check and debug the install_path file issue"""
    log_debug("Checking /mount/admin/install_path issue:", "DEBUG")

    install_path = '/mount/admin/install_path'

    if os.path.exists(install_path):
        try:
            with open(install_path, 'r') as f:
                content = f.read()
            log_debug(f"  Content: {content}", "DEBUG")
        except Exception as e:
            log_debug(f"  Exists but cannot read: {e}", "ERROR")
    else:
        log_debug(f"  File does not exist (this is OK if not on Streamlit Cloud)", "DEBUG")

        # Check parent directory
        parent = os.path.dirname(install_path)
        if os.path.exists(parent):
            try:
                files = os.listdir(parent)
                log_debug(f"  Parent directory {parent} exists, contains: {files}", "DEBUG")
            except Exception as e:
                log_debug(f"  Parent directory exists but cannot list: {e}", "DEBUG")
        else:
            log_debug(f"  Parent directory {parent} does not exist", "DEBUG")


if __name__ == "__main__":
    log_environment_info()
    check_database_imports()
    check_install_path_file()
