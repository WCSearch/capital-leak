"""
Debug Supabase 403 Error - Get Detailed Error Message
"""

import os
import sys
from pathlib import Path
import toml
import traceback

sys.path.append(str(Path(__file__).parent.parent))

from supabase import create_client

# Load credentials
secrets_file = Path(".streamlit/secrets.toml")
secrets = toml.load(secrets_file)
url = secrets.get('supabase', {}).get('url')
key = secrets.get('supabase', {}).get('key')

print("=" * 80)
print("DETAILED SUPABASE ERROR DEBUG")
print("=" * 80)
print(f"URL: {url}")
print(f"Key (first 30 chars): {key[:30]}...")
print()

# Create client
client = create_client(url, key)
print("✅ Client created")

# Try a simple select with detailed error
print("\n1. Testing SELECT...")
try:
    response = client.table('companies').select('*').limit(1).execute()
    print(f"✅ SELECT succeeded: {len(response.data)} rows")
    print(f"   Response: {response.data}")
except Exception as e:
    print(f"❌ SELECT failed")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Error message: {str(e)}")
    print(f"\nFull traceback:")
    traceback.print_exc()

# Try a simple insert with detailed error
print("\n2. Testing INSERT...")
test_data = {
    'company_name': 'Debug Test Company',
    'erp_system': 'SAP',
    'analysis_date': '2025-01-07',
    'revenue_annual': 999999
}

try:
    response = client.table('companies').insert(test_data).execute()
    print(f"✅ INSERT succeeded")
    print(f"   Inserted: {response.data}")

    # Clean up
    if response.data:
        client.table('companies').delete().eq('company_name', 'Debug Test Company').execute()
        print(f"   ✅ Cleaned up test data")
except Exception as e:
    print(f"❌ INSERT failed")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Error message: {str(e)}")

    # Check if there's more detail in the exception
    if hasattr(e, 'args') and len(e.args) > 0:
        print(f"   Error args: {e.args}")
    if hasattr(e, '__dict__'):
        print(f"   Error attributes: {e.__dict__}")

    print(f"\nFull traceback:")
    traceback.print_exc()

print("\n" + "=" * 80)
