"""
Ingest Synthetic SAP Data into Supabase

This script loads the generated CSV files into the Supabase database,
handling proper ordering, validation, and error handling.

Author: Capital Leak Analysis Team
Date: 2025-01-07
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client
from tqdm import tqdm
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
DATA_DIR = Path("data/synthetic")
BATCH_SIZE = 100

# Supabase connection
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://vlbvrhotrlipaoedudys.supabase.co")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "")

# For Supabase, we need the API URL and key, not the PostgreSQL URL
# Extract from DATABASE_URL if needed
if SUPABASE_URL.startswith("postgresql://"):
    # Extract project ref from DATABASE_URL
    # Format: postgresql://postgres:password@db.PROJECT_REF.supabase.co:5432/postgres
    parts = SUPABASE_URL.split("@")
    if len(parts) > 1:
        host_part = parts[1].split(":")[0]  # db.PROJECT_REF.supabase.co
        project_ref = host_part.replace("db.", "").replace(".supabase.co", "")
        SUPABASE_URL = f"https://{project_ref}.supabase.co"

print("=" * 80)
print("SYNTHETIC SAP DATA INGESTION")
print("=" * 80)
print(f"Data Directory: {DATA_DIR.absolute()}")
print(f"Supabase URL: {SUPABASE_URL}")
print(f"Batch Size: {BATCH_SIZE}")
print("=" * 80)


def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    try:
        # Try to get from .streamlit/secrets.toml first
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
        print(f"✓ Connected to Supabase: {url}")
        return client
    except Exception as e:
        print(f"✗ Failed to connect to Supabase: {e}")
        sys.exit(1)


def clean_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Clean and prepare dataframe for insertion"""

    # Parse JSON fields FIRST (before converting NaN to None)
    json_fields = {
        'transactions': ['erp_metadata'],
        'event_logs': ['event_data']
    }

    if table_name in json_fields:
        for field in json_fields[table_name]:
            if field in df.columns:
                df[field] = df[field].apply(lambda x: json.loads(x) if isinstance(x, str) and x else x)

    # Parse dates (handle None/NaN properly)
    date_fields = {
        'companies': ['analysis_date'],
        'transactions': ['transaction_date', 'due_date'],
        'event_logs': ['event_timestamp'],
        'ccc_metrics': ['calculation_date'],
        'inventory_movements': ['movement_date'],
        'purchase_orders': ['po_date']
    }

    if table_name in date_fields:
        for field in date_fields[table_name]:
            if field in df.columns:
                try:
                    # Only parse non-null values
                    df[field] = df[field].apply(
                        lambda x: pd.to_datetime(x).strftime('%Y-%m-%d') if pd.notnull(x) else None
                    )
                except:
                    # If parsing fails, convert NaN to None
                    df[field] = df[field].apply(lambda x: x if pd.notnull(x) else None)

    # Convert ALL remaining NaN to None for proper NULL handling
    # This MUST be done last to ensure all NaN are caught
    df = df.where(pd.notnull(df), None)

    return df


def batch_insert(client: Client, table_name: str, df: pd.DataFrame, desc: str = None) -> dict:
    """
    Insert data in batches with progress tracking

    Returns:
        dict: Statistics including success count, error count, and errors list
    """
    total_rows = len(df)
    success_count = 0
    error_count = 0
    errors = []

    print(f"\n[{table_name}] Inserting {total_rows} rows...")

    # Convert DataFrame to list of dicts
    records = df.to_dict('records')

    # Process in batches
    with tqdm(total=total_rows, desc=desc or table_name) as pbar:
        for i in range(0, total_rows, BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]

            try:
                # Upsert batch
                response = client.table(table_name).upsert(batch).execute()
                success_count += len(batch)
            except Exception as e:
                error_count += len(batch)
                error_msg = f"Batch {i}-{i+len(batch)}: {str(e)}"
                errors.append(error_msg)
                print(f"\n   ✗ Error: {error_msg}")

            pbar.update(len(batch))

    stats = {
        'total': total_rows,
        'success': success_count,
        'errors': error_count,
        'error_details': errors
    }

    if success_count > 0:
        print(f"   ✓ Successfully inserted {success_count}/{total_rows} rows")
    if error_count > 0:
        print(f"   ✗ Failed to insert {error_count}/{total_rows} rows")

    return stats


def ingest_companies(client: Client):
    """Ingest companies data"""
    csv_path = DATA_DIR / "companies.csv"

    if not csv_path.exists():
        print(f"✗ File not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path)
    df = clean_dataframe(df, 'companies')

    stats = batch_insert(client, 'companies', df, "Companies")
    return df['company_id'].iloc[0] if len(df) > 0 else None


def ingest_transactions(client: Client, company_id: str):
    """Ingest transactions data"""
    csv_path = DATA_DIR / "transactions.csv"

    if not csv_path.exists():
        print(f"✗ File not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path)
    df = clean_dataframe(df, 'transactions')

    # Validate company_id exists
    if company_id and df['company_id'].iloc[0] != company_id:
        print(f"   ⚠ Warning: Company ID mismatch in transactions")

    stats = batch_insert(client, 'transactions', df, "Transactions")
    return stats


def ingest_event_logs(client: Client):
    """Ingest event logs data"""
    csv_path = DATA_DIR / "event_logs.csv"

    if not csv_path.exists():
        print(f"✗ File not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path)
    df = clean_dataframe(df, 'event_logs')

    stats = batch_insert(client, 'event_logs', df, "Event Logs")
    return stats


def ingest_ccc_metrics(client: Client):
    """Ingest CCC metrics data"""
    csv_path = DATA_DIR / "ccc_metrics.csv"

    if not csv_path.exists():
        print(f"✗ File not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path)
    df = clean_dataframe(df, 'ccc_metrics')

    stats = batch_insert(client, 'ccc_metrics', df, "CCC Metrics")
    return stats


def ingest_component_details(client: Client):
    """Ingest component details data"""
    csv_path = DATA_DIR / "component_details.csv"

    if not csv_path.exists():
        print(f"✗ File not found: {csv_path}")
        return None

    df = pd.read_csv(csv_path)
    df = clean_dataframe(df, 'component_details')

    stats = batch_insert(client, 'component_details', df, "Component Details")
    return stats


def verify_csv_files():
    """Verify all required CSV files exist"""
    required_files = [
        "companies.csv",
        "transactions.csv",
        "event_logs.csv",
        "ccc_metrics.csv",
        "component_details.csv"
    ]

    print("\n[VERIFICATION] Checking CSV files...")
    all_exist = True

    for file in required_files:
        path = DATA_DIR / file
        exists = path.exists()
        status = "✓" if exists else "✗"
        print(f"   {status} {file}")

        if not exists:
            all_exist = False

    if not all_exist:
        print("\n✗ Missing required CSV files. Run generate_synthetic_sap_data.py first.")
        sys.exit(1)

    print("   ✓ All required files found")


def main():
    """Main execution function"""

    # Verify CSV files exist
    verify_csv_files()

    # Initialize Supabase client
    client = get_supabase_client()

    # Track overall stats
    all_stats = {}

    try:
        # Step 1: Ingest companies (must be first due to foreign keys)
        print("\n" + "=" * 80)
        print("STEP 1: Ingesting Companies")
        print("=" * 80)
        company_id = ingest_companies(client)
        if not company_id:
            print("✗ Failed to ingest companies. Aborting.")
            sys.exit(1)

        # Step 2: Ingest transactions (before event logs due to foreign keys)
        print("\n" + "=" * 80)
        print("STEP 2: Ingesting Transactions")
        print("=" * 80)
        trans_stats = ingest_transactions(client, company_id)
        all_stats['transactions'] = trans_stats

        # Step 3: Ingest event logs
        print("\n" + "=" * 80)
        print("STEP 3: Ingesting Event Logs")
        print("=" * 80)
        event_stats = ingest_event_logs(client)
        all_stats['event_logs'] = event_stats

        # Step 4: Ingest CCC metrics
        print("\n" + "=" * 80)
        print("STEP 4: Ingesting CCC Metrics")
        print("=" * 80)
        ccc_stats = ingest_ccc_metrics(client)
        all_stats['ccc_metrics'] = ccc_stats

        # Step 5: Ingest component details
        print("\n" + "=" * 80)
        print("STEP 5: Ingesting Component Details")
        print("=" * 80)
        comp_stats = ingest_component_details(client)
        all_stats['component_details'] = comp_stats

        # Print summary
        print("\n" + "=" * 80)
        print("INGESTION COMPLETE")
        print("=" * 80)

        print("\nSummary:")
        total_success = 0
        total_errors = 0

        for table, stats in all_stats.items():
            if stats:
                total_success += stats['success']
                total_errors += stats['errors']
                print(f"  {table}:")
                print(f"    ✓ Success: {stats['success']}")
                if stats['errors'] > 0:
                    print(f"    ✗ Errors: {stats['errors']}")

        print(f"\n📊 Total Records Inserted: {total_success}")
        if total_errors > 0:
            print(f"⚠️  Total Errors: {total_errors}")
        else:
            print("✅ No errors!")

        print("\n✅ Data ingestion complete!")
        print("\nNext step: python scripts/validate_synthetic_data.py")

    except Exception as e:
        print(f"\n✗ Fatal error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
