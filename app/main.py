"""Streamlit Dashboard"""
import streamlit as st
import pandas as pd
import plotly.express as px
from config.database import get_client

st.set_page_config(page_title="Capital Leak Analysis", page_icon="💰", layout="wide")

supabase = get_client()
st.title("💰 Capital Leak Analysis Dashboard")

# Fetch companies using Supabase API
companies_response = supabase.table('companies').select('company_id, company_name').execute()
companies = pd.DataFrame(companies_response.data)

if len(companies) == 0:
    st.warning("No companies analyzed yet")
    st.stop()

selected = st.selectbox("Select Company", companies['company_id'].tolist(),
                       format_func=lambda x: companies[companies['company_id']==x]['company_name'].values[0])

st.header("Cash Conversion Cycle")

# Fetch CCC metrics using Supabase API
ccc_response = supabase.table('ccc_metrics')\
    .select('*')\
    .eq('company_id', selected)\
    .order('calculation_date', desc=True)\
    .limit(1)\
    .execute()
ccc = pd.DataFrame(ccc_response.data)

if len(ccc) > 0:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CCC", f"{ccc['ccc_value'].values[0]:.1f} days")
    col2.metric("DSO", f"{ccc['dso_value'].values[0]:.1f} days")
    col3.metric("DIO", f"{ccc['dio_value'].values[0]:.1f} days")
    col4.metric("DPO", f"{ccc['dpo_value'].values[0]:.1f} days")
