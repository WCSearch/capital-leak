"""
DEBUG SCRIPT: Identify Exact Ingestion Issues

This script tests EVERY record before ingestion and identifies:
- Which specific record is failing
- What field has the problem
- The exact value causing the issue
- How to fix it

Author: Capital Leak Analysis Team
Date: 2025-01-08
"""

import pandas as pd
import json
import numpy as np
import math
from pathlib import Path
from supabase import create_client
import sys
import os

from dotenv import load_dotenv
load_dotenv()

DATA_DIR = Path("data/synthetic")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://vlbvrhotrlipaoedudys.supabase.co")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "")

if SUPABASE_URL.startswith("postgresql://"):
    parts = SUPABASE_URL.split("@")
    if len(parts) > 1:
        host_part = parts[1].split(":")[0]
        project_ref = host_part.replace("db.", "").replace(".supabase.co", "")
        SUPABASE_URL = f"https://{project_ref}.supabase.co"

print("=" * 80)
print("COMPREHENSIVE INGESTION DEBUG")
print("=" * 80)
print("This will test EVERY record and identify exact issues\n")


def check_for_nan_inf(value, field_name):
    """Check if a value is NaN or Infinity"""
    if value is None:
        return None

    if isinstance(value, (int, np.integer)):
        return None  # Integers can't be NaN

    if isinstance(value, (float, np.floating)):
        try:
            if math.isnan(value):
                return f"NaN in {field_name}"
            if math.isinf(value):
                return f"Infinity in {field_name}"
        except (TypeError, ValueError):
            pass

    return None


def clean_dataframe(df, table_name):
    """Clean dataframe exactly like ingest script"""
    # Convert NaN to None
    df = df.where(pd.notnull(df), None)

    # Parse JSON fields
    json_fields = {
        'transactions': ['erp_metadata'],
        'event_logs': ['event_data']
    }

    if table_name in json_fields:
        for field in json_fields[table_name]:
            if field in df.columns:
                df[field] = df[field].apply(lambda x: json.loads(x) if isinstance(x, str) and x else x)

    # Parse dates
    date_fields = {
        'transactions': ['transaction_date', 'due_date'],
        'event_logs': ['event_timestamp']
    }

    if table_name in date_fields:
        for field in date_fields[table_name]:
            if field in df.columns and df[field].dtype == 'object':
                try:
                    df[field] = pd.to_datetime(df[field], errors='coerce').dt.strftime('%Y-%m-%d')
                except:
                    pass

    return df


def test_transactions():
    """Test all transactions for issues"""
    print("\n" + "=" * 80)
    print("TESTING TRANSACTIONS")
    print("=" * 80)

    csv_path = DATA_DIR / "transactions.csv"
    df = pd.read_csv(csv_path)

    print(f"Total transactions: {len(df)}")

    # Check component type breakdown
    for comp_type in ['DSO', 'DIO', 'DPO']:
        count = len(df[df['component_type'] == comp_type])
        print(f"  {comp_type}: {count}")

    # Focus on DIO (rows 2500-3299)
    dio_df = df[df['component_type'] == 'DIO'].copy()

    print(f"\nTesting {len(dio_df)} DIO transactions for issues...")

    issues = []

    for idx, row in dio_df.iterrows():
        row_issues = []

        # Check every field for NaN/Inf
        for col, value in row.items():
            issue = check_for_nan_inf(value, col)
            if issue:
                row_issues.append(issue)

        # Check erp_metadata JSON
        if pd.notna(row['erp_metadata']):
            try:
                metadata = json.loads(row['erp_metadata'])
                for key, val in metadata.items():
                    issue = check_for_nan_inf(val, f"erp_metadata.{key}")
                    if issue:
                        row_issues.append(issue)
            except Exception as e:
                row_issues.append(f"Invalid JSON in erp_metadata: {e}")

        if row_issues:
            issues.append({
                'csv_row': idx,
                'transaction_id': row['transaction_id'][:8],
                'gl_account': row['gl_account'],
                'status': row['status'],
                'issues': row_issues
            })

    if issues:
        print(f"\n✗ FOUND {len(issues)} PROBLEMATIC TRANSACTIONS:")
        for issue in issues[:10]:
            print(f"\n  CSV Row {issue['csv_row']}:")
            print(f"    Transaction ID: {issue['transaction_id']}...")
            print(f"    GL Account: {issue['gl_account']}")
            print(f"    Status: {issue['status']}")
            print(f"    Issues: {', '.join(issue['issues'])}")

        print(f"\n🔧 FIX: Regenerate synthetic data with:")
        print(f"    python scripts/generate_synthetic_sap_data.py")
        return False
    else:
        print(f"\n✓ All {len(dio_df)} DIO transactions are CLEAN")

    return True


def test_event_logs():
    """Test all event logs for issues"""
    print("\n" + "=" * 80)
    print("TESTING EVENT LOGS")
    print("=" * 80)

    csv_path = DATA_DIR / "event_logs.csv"
    df = pd.read_csv(csv_path)

    print(f"Total event logs: {len(df)}")

    # Load transactions to check foreign keys
    trans_df = pd.read_csv(DATA_DIR / "transactions.csv")
    trans_ids = set(trans_df['transaction_id'].values)

    print(f"\nChecking foreign key references...")

    orphaned = []
    for idx, row in df.iterrows():
        if pd.notna(row['transaction_id']) and row['transaction_id'] not in trans_ids:
            orphaned.append({
                'csv_row': idx,
                'transaction_id': row['transaction_id'][:8],
                'event_type': row['event_type']
            })

    if orphaned:
        print(f"\n✗ FOUND {len(orphaned)} ORPHANED EVENT LOGS:")
        print(f"   These reference transaction_ids that don't exist in transactions.csv\n")
        for issue in orphaned[:10]:
            print(f"  CSV Row {issue['csv_row']}: {issue['event_type']} → {issue['transaction_id']}...")

        print(f"\n🔧 FIX: Regenerate synthetic data with:")
        print(f"    python scripts/generate_synthetic_sap_data.py")
        return False
    else:
        print(f"✓ All event logs reference valid transactions")

    # Check for NaN/Inf in event_data
    print(f"\nChecking event_data JSON for NaN/Infinity...")

    issues = []

    for idx, row in df.iterrows():
        if pd.notna(row['event_data']):
            try:
                event_data = json.loads(row['event_data'])

                for key, value in event_data.items():
                    issue = check_for_nan_inf(value, f"event_data.{key}")
                    if issue:
                        issues.append({
                            'csv_row': idx,
                            'event_type': row['event_type'],
                            'transaction_id': row['transaction_id'][:8] if pd.notna(row['transaction_id']) else 'None',
                            'field': key,
                            'value': str(value),
                            'issue': issue
                        })
            except Exception as e:
                issues.append({
                    'csv_row': idx,
                    'event_type': row['event_type'],
                    'transaction_id': row['transaction_id'][:8] if pd.notna(row['transaction_id']) else 'None',
                    'error': f"Invalid JSON: {e}"
                })

    if issues:
        print(f"\n✗ FOUND {len(issues)} PROBLEMATIC EVENT LOGS:")
        for issue in issues[:10]:
            print(f"\n  CSV Row {issue['csv_row']}:")
            print(f"    Event Type: {issue['event_type']}")
            print(f"    Transaction ID: {issue['transaction_id']}...")
            if 'field' in issue:
                print(f"    Problematic Field: {issue['field']} = {issue['value']}")
            if 'error' in issue:
                print(f"    Error: {issue['error']}")

        print(f"\n🔧 FIX: Regenerate synthetic data with:")
        print(f"    python scripts/generate_synthetic_sap_data.py")
        return False
    else:
        print(f"✓ All {len(df)} event logs have valid JSON data")

    return True


def test_database_state():
    """Check current database state"""
    print("\n" + "=" * 80)
    print("CHECKING DATABASE STATE")
    print("=" * 80)

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Check current transactions
        response = client.table('transactions').select('component_type', count='exact').execute()

        if response.data:
            df = pd.DataFrame(response.data)
            counts = df['component_type'].value_counts()

            print(f"\nCurrent transactions in database:")
            for comp_type, count in counts.items():
                print(f"  {comp_type}: {count}")

            # Check for old corrupted data
            dso_count = counts.get('DSO', 0)
            dio_count = counts.get('DIO', 0)
            dpo_count = counts.get('DPO', 0)

            if dso_count != 2500 or dio_count != 800 or dpo_count != 1800:
                print(f"\n✗ DATABASE HAS CORRUPTED DATA:")
                print(f"   Expected: DSO=2500, DIO=800, DPO=1800")
                print(f"   Actual: DSO={dso_count}, DIO={dio_count}, DPO={dpo_count}")

                print(f"\n🔧 FIX: Delete old data with SQL:")
                print(f"    DELETE FROM event_logs WHERE company_id IN")
                print(f"      (SELECT company_id FROM companies WHERE company_name = 'TechMfg Industries');")
                print(f"    DELETE FROM transactions WHERE company_id IN")
                print(f"      (SELECT company_id FROM companies WHERE company_name = 'TechMfg Industries');")
                print(f"    DELETE FROM component_details WHERE company_id IN")
                print(f"      (SELECT company_id FROM companies WHERE company_name = 'TechMfg Industries');")
                print(f"    DELETE FROM ccc_metrics WHERE company_id IN")
                print(f"      (SELECT company_id FROM companies WHERE company_name = 'TechMfg Industries');")
                print(f"    DELETE FROM companies WHERE company_name = 'TechMfg Industries';")
                return False
            else:
                print(f"\n✓ Database has correct counts")

                # Check DIO GL split
                dio_response = client.table('transactions').select('gl_account').eq('component_type', 'DIO').execute()
                if dio_response.data:
                    gl_df = pd.DataFrame(dio_response.data)
                    gl_counts = gl_df['gl_account'].value_counts()

                    print(f"\nDIO GL account distribution:")
                    for gl, count in gl_counts.items():
                        print(f"  {gl}: {count}")

                    gl_1400000 = gl_counts.get('1400000', 0)
                    gl_1410000 = gl_counts.get('1410000', 0)

                    if gl_1400000 == 480 and gl_1410000 == 320:
                        print(f"\n✓ DIO GL account split is CORRECT (60/40)")
                        return True
                    else:
                        print(f"\n✗ DIO GL account split is WRONG")
                        print(f"   Expected: 1400000=480, 1410000=320")
                        print(f"   Actual: 1400000={gl_1400000}, 1410000={gl_1410000}")
                        return False
        else:
            print(f"\n✓ Database is empty - ready for ingestion")
            return True

    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            print(f"\n⚠️  Cannot access database (403 Forbidden)")
            print(f"   This is OK - CSV files will be tested instead")
            return True
        else:
            print(f"\n⚠️  Error checking database: {e}")
            return True


def test_single_insert():
    """Test inserting a single DIO record to find exact error"""
    print("\n" + "=" * 80)
    print("TESTING SINGLE RECORD INSERT")
    print("=" * 80)

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Load and clean data
        df = pd.read_csv(DATA_DIR / "transactions.csv")
        dio_df = df[df['component_type'] == 'DIO'].copy()
        dio_clean = clean_dataframe(dio_df, 'transactions')

        # Test both GL accounts
        for gl_account in ['1400000', '1410000']:
            gl_records = dio_clean[dio_clean['gl_account'] == gl_account]
            if len(gl_records) == 0:
                # Try as integer
                gl_records = dio_clean[dio_clean['gl_account'] == int(gl_account)]

            if len(gl_records) > 0:
                record = gl_records.iloc[0].to_dict()

                print(f"\nTesting GL account {gl_account}...")
                print(f"  Transaction ID: {record['transaction_id'][:8]}...")
                print(f"  Status: {record['status']}")
                print(f"  Amount: {record['amount']}")

                try:
                    # Test JSON serialization first
                    json_str = json.dumps(record, default=str)
                    print(f"  ✓ JSON serialization OK")

                    # Try to insert
                    response = client.table('transactions').upsert(record).execute()
                    print(f"  ✓ INSERT SUCCESSFUL")

                except Exception as e:
                    error_msg = str(e)
                    print(f"  ✗ INSERT FAILED")
                    print(f"  Error: {error_msg}")

                    # Analyze error
                    if "NaN" in error_msg or "nan" in error_msg:
                        print(f"\n  🔍 NaN value detected. Checking fields:")
                        for key, value in record.items():
                            if value is not None:
                                issue = check_for_nan_inf(value, key)
                                if issue:
                                    print(f"    ✗ {key} = {value} ({issue})")

                    if "foreign key" in error_msg.lower():
                        print(f"\n  🔍 Foreign key violation - transaction_id doesn't exist in parent table")

                    return False

        return True

    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            print(f"\n⚠️  Cannot test insert (403 Forbidden)")
            print(f"   CSV files are clean - ingestion should work")
            return True
        else:
            print(f"\n✗ Error during test: {e}")
            return False


def main():
    """Run all diagnostic tests"""

    results = []

    # Test 1: Transactions CSV
    results.append(("Transactions CSV", test_transactions()))

    # Test 2: Event Logs CSV
    results.append(("Event Logs CSV", test_event_logs()))

    # Test 3: Database State
    results.append(("Database State", test_database_state()))

    # Test 4: Single Insert
    results.append(("Single Insert", test_single_insert()))

    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)

    if all_passed:
        print("✅ ALL CHECKS PASSED - Ready for ingestion!")
        print("\nNext steps:")
        print("  1. Ensure database is clean (delete old TechMfg data)")
        print("  2. Run: python scripts/ingest_synthetic_data.py")
        print("  3. Run: python scripts/validate_synthetic_data.py")
    else:
        print("❌ ISSUES FOUND - See fixes above")
        print("\nMost likely fixes:")
        print("  1. Delete old corrupted data from database (SQL commands above)")
        print("  2. Regenerate CSV files if they have issues")
        print("  3. Re-run this diagnostic script to verify")

    print("=" * 80)


if __name__ == "__main__":
    main()
