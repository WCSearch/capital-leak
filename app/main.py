"""Streamlit Dashboard"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import traceback

st.set_page_config(page_title="Capital Leak Analysis", page_icon="💰", layout="wide")

# Import and initialize database with comprehensive error handling
try:
    from config.database import get_engine
    engine = get_engine()
    st.title("💰 Capital Leak Analysis Dashboard")
except ImportError as e:
    st.error("❌ Database Connection Error")
    st.error(f"**Import Error:** {str(e)}")
    st.error(f"**Python Version:** {sys.version}")

    st.warning("""
    ### Troubleshooting Steps:

    1. **Check requirements.txt** contains: `psycopg2-binary>=2.9.9`
    2. **Verify DATABASE_URL** environment variable is set in Streamlit Cloud
    3. **Check logs** in Streamlit Cloud dashboard for detailed error messages
    4. **Restart the app** after updating requirements.txt

    ### Common Solutions:
    - Make sure you're using `psycopg2-binary` (not `psycopg2`)
    - Ensure all secrets are properly configured in Streamlit Cloud
    - Check that the database URL is accessible from Streamlit Cloud
    """)

    with st.expander("📋 Full Error Details"):
        st.code(traceback.format_exc())

    st.stop()
except Exception as e:
    st.error("❌ Application Initialization Error")
    st.error(f"**Error:** {str(e)}")

    with st.expander("📋 Full Error Details"):
        st.code(traceback.format_exc())

    st.stop()

# Query companies with error handling
try:
    companies = pd.read_sql("SELECT company_id, company_name FROM companies", engine)
except Exception as e:
    st.error("❌ Failed to fetch companies from database")
    st.error(f"**Error:** {str(e)}")
    with st.expander("📋 Debug Information"):
        st.code(traceback.format_exc())
        st.info("Check that the database is accessible and the 'companies' table exists.")
    st.stop()

if len(companies) == 0:
    st.warning("No companies analyzed yet")
    st.stop()

selected = st.selectbox("Select Company", companies['company_id'].tolist(),
                       format_func=lambda x: companies[companies['company_id']==x]['company_name'].values[0])

st.header("Cash Conversion Cycle")

try:
    ccc = pd.read_sql(f"SELECT * FROM ccc_metrics WHERE company_id='{selected}' ORDER BY calculation_date DESC LIMIT 1", engine)
except Exception as e:
    st.error(f"❌ Failed to fetch CCC metrics for company {selected}")
    st.error(f"**Error:** {str(e)}")
    ccc = pd.DataFrame()  # Empty dataframe to prevent further errors

if len(ccc) > 0:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CCC", f"{ccc['ccc_value'].values[0]:.1f} days")
    col2.metric("DSO", f"{ccc['dso_value'].values[0]:.1f} days")
    col3.metric("DIO", f"{ccc['dio_value'].values[0]:.1f} days")
    col4.metric("DPO", f"{ccc['dpo_value'].values[0]:.1f} days")
