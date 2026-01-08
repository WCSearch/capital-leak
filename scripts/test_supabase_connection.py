"""
Test Supabase Connection and Policies

This script tests the Supabase connection and checks if RLS policies are working.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from supabase import create_client
import toml

def test_connection():
    """Test Supabase connection and policies"""

    print("=" * 80)
    print("SUPABASE CONNECTION TEST")
    print("=" * 80)

    # Load credentials
    secrets_file = Path(".streamlit/secrets.toml")
    if secrets_file.exists():
        secrets = toml.load(secrets_file)
        url = secrets.get('supabase', {}).get('url')
        key = secrets.get('supabase', {}).get('key')
    else:
        print("❌ .streamlit/secrets.toml not found")
        return

    print(f"\n1. Connecting to: {url}")
    print(f"2. Using key: {key[:20]}...")

    try:
        client = create_client(url, key)
        print("✅ Client created successfully")
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        return

    # Test SELECT
    print("\n3. Testing SELECT on companies table...")
    try:
        response = client.table('companies').select('*').limit(5).execute()
        print(f"✅ SELECT works - Found {len(response.data)} rows")
    except Exception as e:
        print(f"❌ SELECT failed: {e}")

    # Test INSERT
    print("\n4. Testing INSERT on companies table...")
    test_data = {
        'company_name': 'Test Company',
        'erp_system': 'SAP ECC 6.0',
        'analysis_date': '2025-01-07',
        'revenue_annual': 1000000
    }

    try:
        response = client.table('companies').insert(test_data).execute()
        print(f"✅ INSERT works - Inserted {len(response.data)} row(s)")

        # Clean up test data
        if response.data:
            company_id = response.data[0]['company_id']
            client.table('companies').delete().eq('company_id', company_id).execute()
            print(f"✅ Cleaned up test data")
    except Exception as e:
        print(f"❌ INSERT failed: {e}")
        print("\nThis means RLS policies are not properly configured.")
        print("Please verify you ran the SQL from database/rls_policies.sql")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_connection()
