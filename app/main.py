"""Streamlit Dashboard with comprehensive error handling and debugging"""
import sys
import os
import traceback

# Debug: Log startup
print("=" * 80, file=sys.stderr)
print("STARTING CAPITAL LEAK STREAMLIT APP", file=sys.stderr)
print("=" * 80, file=sys.stderr)
print(f"Working directory: {os.getcwd()}", file=sys.stderr)
print(f"Python version: {sys.version}", file=sys.stderr)
print(f"Python path: {sys.path[:3]}...", file=sys.stderr)
sys.stderr.flush()

# Import Streamlit first
try:
    import streamlit as st
    print(f"✓ Streamlit imported successfully (version {st.__version__})", file=sys.stderr)
except ImportError as e:
    print(f"✗ CRITICAL: Failed to import Streamlit: {e}", file=sys.stderr)
    sys.exit(1)

# Configure page early
st.set_page_config(page_title="Capital Leak Analysis", page_icon="💰", layout="wide")

# Import other dependencies
try:
    import pandas as pd
    print(f"✓ Pandas imported successfully (version {pd.__version__})", file=sys.stderr)
except ImportError as e:
    st.error(f"Failed to import Pandas: {e}")
    st.stop()

try:
    import plotly.express as px
    print(f"✓ Plotly imported successfully", file=sys.stderr)
except ImportError as e:
    st.error(f"Failed to import Plotly: {e}")
    st.stop()

# Import database module with comprehensive error handling
print("Attempting to import config.database...", file=sys.stderr)
sys.stderr.flush()

try:
    from config.database import get_engine, test_connection
    print("✓ Database module imported successfully", file=sys.stderr)
except ImportError as e:
    print(f"✗ CRITICAL: Failed to import database module: {e}", file=sys.stderr)
    print(f"Traceback:\n{traceback.format_exc()}", file=sys.stderr)
    sys.stderr.flush()

    st.error("🚨 Database Module Import Error")
    st.error(f"**Error:** {e}")

    with st.expander("📋 View Full Error Details"):
        st.code(traceback.format_exc())

    st.markdown("---")
    st.markdown("### 🔍 Troubleshooting Steps:")

    st.markdown("""
    1. **Check that psycopg2-binary is installed:**
       - In Streamlit Cloud: Verify `requirements.txt` includes `psycopg2-binary`
       - Locally: Run `pip install psycopg2-binary`

    2. **Verify DATABASE_URL is set:**
       - In Streamlit Cloud: Check Secrets in app settings
       - Locally: Create a `.env` file with `DATABASE_URL`

    3. **Check error details above for specific issues**

    4. **View application logs:**
       - In Streamlit Cloud: Click "Manage app" → "Logs"
       - Look for detailed error messages in the logs
    """)

    st.stop()
except Exception as e:
    print(f"✗ UNEXPECTED ERROR importing database: {e}", file=sys.stderr)
    print(f"Traceback:\n{traceback.format_exc()}", file=sys.stderr)
    sys.stderr.flush()

    st.error("🚨 Unexpected Database Error")
    st.error(f"**Error:** {e}")
    st.code(traceback.format_exc())
    st.stop()

# Show app header
st.title("💰 Capital Leak Analysis Dashboard")

# Test database connection
with st.spinner("Connecting to database..."):
    try:
        print("Testing database connection...", file=sys.stderr)
        success, message = test_connection()

        if not success:
            print(f"✗ Database connection failed: {message}", file=sys.stderr)
            st.error("🚨 Database Connection Failed")
            st.error(f"**Error:** {message}")

            with st.expander("🔍 Troubleshooting Information"):
                st.markdown("""
                **Common Issues:**
                - Invalid database credentials
                - Database server not reachable
                - Incorrect DATABASE_URL format
                - Network/firewall issues

                **Expected DATABASE_URL format:**
                ```
                postgresql://username:password@host:port/database
                ```

                **For Supabase:**
                ```
                postgresql://postgres.[project-ref]:[password]@[project-ref].supabase.co:5432/postgres
                ```
                """)
            st.stop()
        else:
            print(f"✓ Database connection successful: {message}", file=sys.stderr)

    except Exception as e:
        print(f"✗ Exception during connection test: {e}", file=sys.stderr)
        print(f"Traceback:\n{traceback.format_exc()}", file=sys.stderr)
        st.error("🚨 Database Connection Error")
        st.error(f"**Error:** {e}")
        st.code(traceback.format_exc())
        st.stop()

# Get database engine
try:
    engine = get_engine()
    print("✓ Database engine acquired", file=sys.stderr)
except Exception as e:
    print(f"✗ Failed to get database engine: {e}", file=sys.stderr)
    st.error(f"Failed to get database engine: {e}")
    st.stop()

# Load companies
try:
    print("Loading companies from database...", file=sys.stderr)
    companies = pd.read_sql("SELECT company_id, company_name FROM companies", engine)
    print(f"✓ Loaded {len(companies)} companies", file=sys.stderr)

    if len(companies) == 0:
        st.warning("📊 No companies analyzed yet")
        st.info("Please run the ETL process to load company data.")
        st.stop()

except Exception as e:
    print(f"✗ Failed to load companies: {e}", file=sys.stderr)
    st.error("🚨 Failed to Load Companies")
    st.error(f"**Error:** {e}")

    with st.expander("📋 Error Details"):
        st.code(traceback.format_exc())

    st.markdown("---")
    st.markdown("""
    **Possible causes:**
    - The `companies` table doesn't exist
    - Database schema not initialized
    - Insufficient permissions

    **Solution:** Run the database initialization scripts in the `database/` folder.
    """)
    st.stop()

# Company selector
selected = st.selectbox(
    "Select Company",
    companies['company_id'].tolist(),
    format_func=lambda x: companies[companies['company_id']==x]['company_name'].values[0]
)

st.header("Cash Conversion Cycle")

# Load CCC metrics
try:
    ccc = pd.read_sql(
        f"SELECT * FROM ccc_metrics WHERE company_id='{selected}' ORDER BY calculation_date DESC LIMIT 1",
        engine
    )

    if len(ccc) > 0:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("CCC", f"{ccc['ccc_value'].values[0]:.1f} days")
        col2.metric("DSO", f"{ccc['dso_value'].values[0]:.1f} days")
        col3.metric("DIO", f"{ccc['dio_value'].values[0]:.1f} days")
        col4.metric("DPO", f"{ccc['dpo_value'].values[0]:.1f} days")
    else:
        st.info(f"No CCC metrics available for {companies[companies['company_id']==selected]['company_name'].values[0]}")

except Exception as e:
    print(f"✗ Failed to load CCC metrics: {e}", file=sys.stderr)
    st.error(f"Failed to load CCC metrics: {e}")
    with st.expander("View Error"):
        st.code(traceback.format_exc())

print("✓ App loaded successfully", file=sys.stderr)
sys.stderr.flush()
