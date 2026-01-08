"""
Test exact ingestion process for DIO transactions to identify the issue
"""

import pandas as pd
import json
from pathlib import Path
from supabase import create_client
import sys
import os

from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://vlbvrhotrlipaoedudys.supabase.co")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "")

if SUPABASE_URL.startswith("postgresql://"):
    parts = SUPABASE_URL.split("@")
    if len(parts) > 1:
        host_part = parts[1].split(":")[0]
        project_ref = host_part.replace("db.", "").replace(".supabase.co", "")
        SUPABASE_URL = f"https://{project_ref}.supabase.co"

print("=" * 80)
print("DIO BATCH INSERT TEST")
print("=" * 80)

def clean_dataframe(df, table_name):
    """Clean dataframe exactly like ingest_synthetic_data.py does"""
    # Convert NaN to None
    df = df.where(pd.notnull(df), None)

    # Parse JSON fields
    if table_name == 'transactions' and 'erp_metadata' in df.columns:
        df['erp_metadata'] = df['erp_metadata'].apply(
            lambda x: json.loads(x) if isinstance(x, str) and x else x
        )

    # Parse dates
    if 'transaction_date' in df.columns:
        df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d')

    if 'due_date' in df.columns and df['due_date'].dtype == 'object':
        df['due_date'] = pd.to_datetime(df['due_date'], errors='coerce').dt.strftime('%Y-%m-%d')

    return df

# Load transactions
df = pd.read_csv('data/synthetic/transactions.csv')

# Get just DIO transactions
dio_df = df[df['component_type'] == 'DIO'].copy()

print(f"Total DIO transactions: {len(dio_df)}")
print(f"GL account data type: {dio_df['gl_account'].dtype}")
print(f"Sample gl_account values: {dio_df['gl_account'].head(3).tolist()}")

# Clean the data
dio_clean = clean_dataframe(dio_df, 'transactions')

print(f"\nAfter cleaning:")
print(f"GL account data type: {dio_clean['gl_account'].dtype}")

# Convert to records (like the ingestion script does)
records = dio_clean.to_dict('records')

print(f"\n" + "=" * 80)
print("Testing first 5 DIO records")
print("=" * 80)

client = create_client(SUPABASE_URL, SUPABASE_KEY)

for i, record in enumerate(records[:5]):
    print(f"\n[Record {i+1}] Transaction ID: {record['transaction_id'][:8]}...")
    print(f"  GL Account: {record['gl_account']} (type: {type(record['gl_account']).__name__})")
    print(f"  Component Type: {record['component_type']}")
    print(f"  Status: {record['status']}")
    print(f"  Amount: {record['amount']}")

    # Check for problematic values
    issues = []
    for key, value in record.items():
        if value is not None:
            if isinstance(value, float):
                import math
                if math.isnan(value) or math.isinf(value):
                    issues.append(f"{key}={value}")

    if issues:
        print(f"  ✗ ISSUES FOUND: {', '.join(issues)}")
    else:
        print(f"  ✓ No NaN/Inf values")

    # Try to serialize to JSON (what Supabase client does internally)
    try:
        json_str = json.dumps(record, default=str)
        print(f"  ✓ JSON serialization OK")
    except Exception as e:
        print(f"  ✗ JSON serialization FAILED: {e}")
        continue

    # Try to insert
    try:
        response = client.table('transactions').upsert(record).execute()
        print(f"  ✓ INSERT SUCCESSFUL")
    except Exception as e:
        error_msg = str(e)
        print(f"  ✗ INSERT FAILED: {error_msg}")

        # If it's a data type issue, try converting gl_account to string
        if 'type' in error_msg.lower() or 'json' in error_msg.lower():
            print(f"  → Retrying with gl_account as string...")
            record['gl_account'] = str(record['gl_account'])
            try:
                response = client.table('transactions').upsert(record).execute()
                print(f"  ✓ INSERT SUCCESSFUL after converting gl_account to string")
            except Exception as e2:
                print(f"  ✗ Still failed: {e2}")

print("\n" + "=" * 80)
print("Test complete")
print("=" * 80)
