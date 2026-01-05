# Capital Leak Analysis Platform

Find hidden capital leaks in mid-market companies through ERP event log analysis.

## What This Does
Analyzes ERP data to identify capital trapped in working capital:
- DSO (Days Sales Outstanding): Cash trapped in receivables
- DIO (Days Inventory Outstanding): Cash trapped in inventory
- DPO (Days Payable Outstanding): Cash management in payables

CCC = DSO + DIO - DPO (Cash Conversion Cycle)

## Quick Start
```bash
pip install -r requirements.txt
cp .env.example .env
# Add your DATABASE_URL to .env
python scripts/setup_database.py
streamlit run app/main.py
```

## Supported ERPs
- SAP, Oracle, NetSuite, Microsoft Dynamics
