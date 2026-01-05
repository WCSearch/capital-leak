"""Streamlit Dashboard"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import traceback

st.set_page_config(page_title="Capital Leak Analysis", page_icon="💰", layout="wide")

# Import and initialize Supabase client with comprehensive error handling
try:
    from config.database import get_supabase_client
    supabase = get_supabase_client()
    st.title("💰 Capital Leak Analysis Dashboard")
except KeyError as e:
    st.error("❌ Supabase Configuration Error")
    st.error(f"**Missing Secret:** {str(e)}")

    st.warning("""
    ### Troubleshooting Steps:

    1. **Check Streamlit secrets** (.streamlit/secrets.toml) contains:
       ```toml
       [supabase]
       url = "your-supabase-url"
       key = "your-supabase-anon-key"
       ```
    2. **In Streamlit Cloud**: Go to App Settings → Secrets and add the Supabase configuration
    3. **Restart the app** after updating secrets

    ### Where to find your Supabase credentials:
    - Dashboard: https://supabase.com/dashboard
    - Settings → API → Project URL and anon/public key
    """)

    with st.expander("📋 Full Error Details"):
        st.code(traceback.format_exc())

    st.stop()
except ImportError as e:
    st.error("❌ Import Error")
    st.error(f"**Error:** {str(e)}")
    st.error(f"**Python Version:** {sys.version}")

    st.warning("""
    ### Troubleshooting Steps:

    1. **Check requirements.txt** contains: `supabase>=2.3.0`
    2. **Restart the app** after updating requirements.txt
    3. **Check logs** in Streamlit Cloud dashboard for installation errors
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
    response = supabase.table('companies').select('company_id', 'company_name').execute()
    companies = pd.DataFrame(response.data)
except Exception as e:
    st.error("❌ Failed to fetch companies from Supabase")
    st.error(f"**Error:** {str(e)}")
    with st.expander("📋 Debug Information"):
        st.code(traceback.format_exc())
        st.info("Check that the Supabase connection is configured correctly and the 'companies' table exists.")
    st.stop()

if len(companies) == 0:
    st.warning("No companies analyzed yet")
    st.stop()

selected = st.selectbox("Select Company", companies['company_id'].tolist(),
                       format_func=lambda x: companies[companies['company_id']==x]['company_name'].values[0])

st.header("Cash Conversion Cycle")

try:
    response = supabase.table('ccc_metrics')\
        .select('*')\
        .eq('company_id', selected)\
        .order('calculation_date', desc=True)\
        .limit(1)\
        .execute()
    ccc = pd.DataFrame(response.data)
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
