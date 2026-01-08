"""
Test manual insertion of a single DIO transaction to identify the exact error
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
print("MANUAL DIO TRANSACTION INSERT TEST")
print("=" * 80)

# Load data
df = pd.read_csv('data/synthetic/transactions.csv')
dio = df[df['component_type'] == 'DIO'].copy()

print(f"Total DIO transactions in CSV: {len(dio)}")

# Test with GL 1410000 first (Finished Goods - this is the one that's missing)
gl_1410000 = dio[dio['gl_account'] == 1410000]
gl_1400000 = dio[dio['gl_account'] == 1400000]

print(f"GL 1400000 (Raw Materials): {len(gl_1400000)} transactions")
print(f"GL 1410000 (Finished Goods): {len(gl_1410000)} transactions")

# Try both GL accounts
for gl_account_num in [1410000, 1400000]:
    print("\n" + "=" * 80)
    print(f"Testing GL Account: {gl_account_num}")
    print("=" * 80)

    test_df = dio[dio['gl_account'] == gl_account_num]
    if len(test_df) == 0:
        print(f"No records found for GL {gl_account_num}")
        continue

    # Get first record
    record = test_df.iloc[0].to_dict()

    # Clean it
    record = {k: (None if pd.isna(v) else v) for k, v in record.items()}

    # Parse JSON fields
    if 'erp_metadata' in record and isinstance(record['erp_metadata'], str):
        record['erp_metadata'] = json.loads(record['erp_metadata'])

    # Convert gl_account to string (might be the issue)
    record['gl_account'] = str(record['gl_account'])

    print(f"\nRecord to insert:")
    print(f"  transaction_id: {record['transaction_id']}")
    print(f"  gl_account: {record['gl_account']} (type: {type(record['gl_account'])})")
    print(f"  amount: {record['amount']}")
    print(f"  status: {record['status']}")
    print(f"  due_date: {record['due_date']}")
    print(f"  customer_vendor: {record['customer_vendor']}")

    # Try to insert
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = client.table('transactions').upsert(record).execute()
        print(f"\n✓ INSERT SUCCESSFUL for GL {gl_account_num}")
        print(f"  Response: {len(response.data)} record inserted")

        # Verify
        verify = client.table('transactions').select('*').eq('transaction_id', record['transaction_id']).execute()
        if len(verify.data) > 0:
            print(f"✓ Record verified in database")

    except Exception as e:
        print(f"\n✗ INSERT FAILED for GL {gl_account_num}")
        print(f"  Error: {e}")
        print(f"  Error type: {type(e).__name__}")

        # Try with gl_account as int
        print(f"\n  Retrying with gl_account as integer...")
        record['gl_account'] = int(record['gl_account'])
        try:
            response = client.table('transactions').upsert(record).execute()
            print(f"  ✓ INSERT SUCCESSFUL with integer gl_account")
        except Exception as e2:
            print(f"  ✗ Still failed: {e2}")

print("\n" + "=" * 80)
print("Test complete")
