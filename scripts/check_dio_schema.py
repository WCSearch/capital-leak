"""
Check Supabase Schema for DIO Transaction Ingestion Issues

This script diagnoses why DIO transactions aren't being ingested by:
1. Checking the transactions table schema
2. Comparing CSV data against schema requirements
3. Identifying missing or invalid fields
4. Testing a sample DIO record insertion

Author: Capital Leak Analysis Team
Date: 2025-01-08
"""

import pandas as pd
import json
from pathlib import Path
from supabase import create_client, Client
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
DATA_DIR = Path("data/synthetic")

# Supabase connection
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://vlbvrhotrlipaoedudys.supabase.co")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "")

# For Supabase, we need the API URL and key, not the PostgreSQL URL
if SUPABASE_URL.startswith("postgresql://"):
    parts = SUPABASE_URL.split("@")
    if len(parts) > 1:
        host_part = parts[1].split(":")[0]
        project_ref = host_part.replace("db.", "").replace(".supabase.co", "")
        SUPABASE_URL = f"https://{project_ref}.supabase.co"

print("=" * 80)
print("DIO TRANSACTION SCHEMA DIAGNOSTIC")
print("=" * 80)
print(f"Supabase URL: {SUPABASE_URL}")
print("=" * 80)


def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    try:
        secrets_file = Path(".streamlit/secrets.toml")
        if secrets_file.exists():
            import toml
            secrets = toml.load(secrets_file)
            url = secrets.get('supabase', {}).get('url', SUPABASE_URL)
            key = secrets.get('supabase', {}).get('key', SUPABASE_KEY)
        else:
            url = SUPABASE_URL
            key = SUPABASE_KEY

        client = create_client(url, key)
        print(f"✓ Connected to Supabase\n")
        return client
    except Exception as e:
        print(f"✗ Failed to connect to Supabase: {e}")
        sys.exit(1)


def check_existing_transactions(client: Client):
    """Check what's currently in the transactions table"""
    print("\n" + "=" * 80)
    print("STEP 1: Check Existing Transactions")
    print("=" * 80)

    try:
        # Count by component type
        response = client.table('transactions').select('component_type', count='exact').execute()

        df = pd.DataFrame(response.data)
        if len(df) > 0:
            counts = df['component_type'].value_counts()
            print(f"\nCurrent transaction counts in database:")
            for comp_type, count in counts.items():
                print(f"  {comp_type}: {count}")

            # Check for DIO specifically
            dio_count = counts.get('DIO', 0)
            print(f"\n{'✓' if dio_count > 0 else '✗'} DIO transactions: {dio_count}")

            if dio_count == 0:
                print("  ⚠️  DIO transactions are MISSING from database")
        else:
            print("  ⚠️  No transactions found in database at all")

    except Exception as e:
        print(f"  ✗ Error querying transactions: {e}")


def check_csv_data():
    """Check DIO data in CSV file"""
    print("\n" + "=" * 80)
    print("STEP 2: Check DIO Data in CSV")
    print("=" * 80)

    csv_path = DATA_DIR / "transactions.csv"

    if not csv_path.exists():
        print(f"  ✗ CSV file not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path)

    # Filter DIO transactions
    dio_df = df[df['component_type'] == 'DIO'].copy()

    print(f"\n✓ CSV file loaded: {len(df)} total transactions")
    print(f"✓ DIO transactions in CSV: {len(dio_df)}")

    # Check GL account distribution
    if len(dio_df) > 0:
        gl_dist = dio_df['gl_account'].value_counts()
        print(f"\nGL Account Distribution:")
        for gl, count in gl_dist.items():
            pct = (count / len(dio_df) * 100)
            print(f"  {gl}: {count} transactions ({pct:.1f}%)")

        # Verify 60/40 split
        gl_1400000 = int(gl_dist.get(1400000, 0))
        gl_1410000 = int(gl_dist.get(1410000, 0))

        if gl_1400000 == 480 and gl_1410000 == 320:
            print(f"\n✓ GL account split is CORRECT (60/40)")
        else:
            # Could be string keys
            gl_1400000_str = int(gl_dist.get('1400000', 0))
            gl_1410000_str = int(gl_dist.get('1410000', 0))

            if gl_1400000_str == 480 and gl_1410000_str == 320:
                print(f"\n✓ GL account split is CORRECT (60/40)")
            else:
                print(f"\n✗ GL account split is INCORRECT")
                print(f"  Expected: 480 (1400000) / 320 (1410000)")
                print(f"  Actual: {gl_1400000 or gl_1400000_str} (1400000) / {gl_1410000 or gl_1410000_str} (1410000)")

    # Show sample DIO records
    print(f"\nSample DIO records from CSV:")
    print(f"-" * 80)

    sample_dio = dio_df.head(3)
    for idx, row in sample_dio.iterrows():
        print(f"\nRecord {idx}:")
        print(f"  transaction_id: {row['transaction_id']}")
        print(f"  component_type: {row['component_type']}")
        print(f"  gl_account: {row['gl_account']}")
        print(f"  amount: {row['amount']}")
        print(f"  status: {row['status']}")
        print(f"  transaction_date: {row['transaction_date']}")

    return dio_df


def check_schema_fields(client: Client, dio_df):
    """Check if CSV fields match database schema"""
    print("\n" + "=" * 80)
    print("STEP 3: Schema Field Validation")
    print("=" * 80)

    if dio_df is None or len(dio_df) == 0:
        print("  ✗ No DIO data to validate")
        return

    # Get CSV columns
    csv_columns = set(dio_df.columns)
    print(f"\nCSV columns ({len(csv_columns)}):")
    for col in sorted(csv_columns):
        print(f"  - {col}")

    # Check for required fields (based on the schema)
    required_fields = [
        'transaction_id',
        'company_id',
        'component_type',
        'transaction_number',
        'transaction_date',
        'amount',
        'outstanding_amount',
        'days_outstanding',
        'gl_account',
        'status'
    ]

    print(f"\nRequired field validation:")
    missing_fields = []
    for field in required_fields:
        exists = field in csv_columns
        status = "✓" if exists else "✗"
        print(f"  {status} {field}")
        if not exists:
            missing_fields.append(field)

    if missing_fields:
        print(f"\n✗ Missing required fields: {missing_fields}")
    else:
        print(f"\n✓ All required fields present")

    # Check for null values in critical fields
    print(f"\nNull value check:")
    for field in required_fields:
        if field in dio_df.columns:
            null_count = dio_df[field].isnull().sum()
            status = "✓" if null_count == 0 else "✗"
            print(f"  {status} {field}: {null_count} nulls")


def test_single_dio_insert(client: Client, dio_df):
    """Test inserting a single DIO transaction"""
    print("\n" + "=" * 80)
    print("STEP 4: Test Single DIO Record Insertion")
    print("=" * 80)

    if dio_df is None or len(dio_df) == 0:
        print("  ✗ No DIO data to test")
        return

    # Get first DIO record with GL 1410000 (Finished Goods)
    gl_1410000_records = dio_df[dio_df['gl_account'] == '1410000']
    if len(gl_1410000_records) > 0:
        test_record = gl_1410000_records.iloc[0].to_dict()
    else:
        # Fallback to any DIO record
        print("  ⚠️  No GL 1410000 records found, using first DIO record")
        test_record = dio_df.iloc[0].to_dict()

    # Clean the record (handle NaN, parse JSON)
    test_record = {k: (None if pd.isna(v) else v) for k, v in test_record.items()}

    # Parse JSON fields
    if 'erp_metadata' in test_record and isinstance(test_record['erp_metadata'], str):
        try:
            test_record['erp_metadata'] = json.loads(test_record['erp_metadata'])
        except:
            pass

    print(f"\nTest record details:")
    print(f"  transaction_id: {test_record['transaction_id']}")
    print(f"  component_type: {test_record['component_type']}")
    print(f"  gl_account: {test_record['gl_account']}")
    print(f"  amount: {test_record['amount']}")
    print(f"  status: {test_record['status']}")

    print(f"\nAttempting to insert test record...")

    try:
        response = client.table('transactions').upsert(test_record).execute()
        print(f"✓ Test insertion SUCCESSFUL")
        print(f"  Response: {len(response.data)} record(s) inserted")

        # Verify it's in the database
        verify = client.table('transactions').select('*').eq('transaction_id', test_record['transaction_id']).execute()
        if len(verify.data) > 0:
            print(f"✓ Test record verified in database")
            record = verify.data[0]
            print(f"  GL Account: {record['gl_account']}")
            print(f"  Amount: {record['amount']}")
        else:
            print(f"✗ Test record NOT found in database after insertion")

    except Exception as e:
        print(f"✗ Test insertion FAILED")
        print(f"  Error: {e}")

        # Check if it's a permissions issue
        if "403" in str(e) or "Forbidden" in str(e):
            print(f"\n⚠️  PERMISSIONS ISSUE DETECTED")
            print(f"  The API key doesn't have permission to insert records")
            print(f"  Solution: Disable Row Level Security (RLS) or update policies")
            print(f"\n  SQL to disable RLS:")
            print(f"  ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;")


def check_orphaned_events(client: Client):
    """Check for orphaned event logs"""
    print("\n" + "=" * 80)
    print("STEP 5: Check for Orphaned Event Logs")
    print("=" * 80)

    try:
        # Get all transaction IDs
        trans_response = client.table('transactions').select('transaction_id').execute()
        trans_ids = set([t['transaction_id'] for t in trans_response.data])

        # Get all event transaction IDs
        events_response = client.table('event_logs').select('transaction_id').execute()
        event_trans_ids = [e['transaction_id'] for e in events_response.data if e['transaction_id']]

        # Find orphaned events
        orphaned = [tid for tid in event_trans_ids if tid not in trans_ids]

        print(f"\nEvent log analysis:")
        print(f"  Total event logs: {len(event_trans_ids)}")
        print(f"  Total transactions: {len(trans_ids)}")
        print(f"  Orphaned event logs: {len(orphaned)}")

        if len(orphaned) > 0:
            print(f"\n✗ ORPHANED EVENT LOGS DETECTED")
            print(f"  This causes foreign key constraint violations")
            print(f"\n  SQL to fix:")
            print(f"  DELETE FROM event_logs")
            print(f"  WHERE transaction_id NOT IN (")
            print(f"      SELECT transaction_id FROM transactions")
            print(f"  );")
        else:
            print(f"\n✓ No orphaned event logs")

    except Exception as e:
        print(f"  ✗ Error checking orphaned events: {e}")


def generate_summary():
    """Generate summary and recommendations"""
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)

    print(f"\nIf DIO transactions are missing from database:")
    print(f"\n1. Check for permissions issues (403 Forbidden)")
    print(f"   → Disable RLS: ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;")

    print(f"\n2. Clean up orphaned event logs")
    print(f"   → DELETE FROM event_logs WHERE transaction_id NOT IN")
    print(f"     (SELECT transaction_id FROM transactions);")

    print(f"\n3. Regenerate and reingest data")
    print(f"   → python scripts/generate_synthetic_sap_data.py")
    print(f"   → python scripts/ingest_synthetic_data.py")

    print(f"\n4. Verify GL account split")
    print(f"   → SELECT gl_account, COUNT(*) FROM transactions")
    print(f"     WHERE component_type = 'DIO' GROUP BY gl_account;")


def main():
    """Main diagnostic function"""

    # Initialize client
    client = get_supabase_client()

    # Run diagnostic steps
    check_existing_transactions(client)
    dio_df = check_csv_data()
    check_schema_fields(client, dio_df)
    test_single_dio_insert(client, dio_df)
    check_orphaned_events(client)
    generate_summary()

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
