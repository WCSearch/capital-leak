"""Streamlit Dashboard"""
import streamlit as st
import pandas as pd
import plotly.express as px
from config.database import get_engine

st.set_page_config(page_title="Capital Leak Analysis", page_icon="💰", layout="wide")

engine = get_engine()
st.title("💰 Capital Leak Analysis Dashboard")

companies = pd.read_sql("SELECT company_id, company_name FROM companies", engine)

if len(companies) == 0:
    st.warning("No companies analyzed yet")
    st.stop()

selected = st.selectbox("Select Company", companies['company_id'].tolist(),
                       format_func=lambda x: companies[companies['company_id']==x]['company_name'].values[0])

st.header("Cash Conversion Cycle")

ccc = pd.read_sql(f"SELECT * FROM ccc_metrics WHERE company_id='{selected}' ORDER BY calculation_date DESC LIMIT 1", engine)

if len(ccc) > 0:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CCC", f"{ccc['ccc_value'].values[0]:.1f} days")
    col2.metric("DSO", f"{ccc['dso_value'].values[0]:.1f} days")
    col3.metric("DIO", f"{ccc['dio_value'].values[0]:.1f} days")
    col4.metric("DPO", f"{ccc['dpo_value'].values[0]:.1f} days")
