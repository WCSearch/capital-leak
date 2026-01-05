#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot deployment issues
Run this to get comprehensive information about the environment
"""

import sys
import os

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("CAPITAL LEAK DEPLOYMENT DIAGNOSTICS")
print("=" * 80)
print()

# Import and run debug utilities
try:
    from config.debug_utils import (
        log_debug,
        log_environment_info,
        check_database_imports,
        check_install_path_file,
        is_streamlit_cloud
    )

    log_environment_info()
    print()

    check_database_imports()
    print()

    check_install_path_file()
    print()

    print("=" * 80)
    print("TESTING DATABASE CONNECTION")
    print("=" * 80)

    try:
        from config.database import test_connection, DATABASE_URL

        # Mask the URL for display
        masked_url = DATABASE_URL[:20] + "..." + DATABASE_URL[-15:] if len(DATABASE_URL) > 35 else "***"
        print(f"Database URL: {masked_url}")

        success, message = test_connection()
        if success:
            print(f"✓ Database Connection: SUCCESS")
            print(f"  Message: {message}")
        else:
            print(f"✗ Database Connection: FAILED")
            print(f"  Error: {message}")

    except Exception as e:
        print(f"✗ Failed to import or test database: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 80)
    print("TESTING STREAMLIT IMPORTS")
    print("=" * 80)

    try:
        import streamlit as st
        print(f"✓ Streamlit version: {st.__version__}")
    except ImportError as e:
        print(f"✗ Failed to import Streamlit: {e}")

    try:
        import pandas as pd
        print(f"✓ Pandas version: {pd.__version__}")
    except ImportError as e:
        print(f"✗ Failed to import Pandas: {e}")

    try:
        import plotly
        print(f"✓ Plotly version: {plotly.__version__}")
    except ImportError as e:
        print(f"✗ Failed to import Plotly: {e}")

    try:
        import sqlalchemy
        print(f"✓ SQLAlchemy version: {sqlalchemy.__version__}")
    except ImportError as e:
        print(f"✗ Failed to import SQLAlchemy: {e}")

    print()
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

    if is_streamlit_cloud():
        print()
        print("NOTES FOR STREAMLIT CLOUD:")
        print("- The '/mount/admin/install_path' error is a Streamlit Cloud system message")
        print("- It's usually harmless and can be ignored if the app works otherwise")
        print("- Make sure your secrets are configured in Streamlit Cloud settings")
        print("- Check that requirements.txt includes all necessary packages")

except Exception as e:
    print(f"CRITICAL ERROR running diagnostics: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
