#!/usr/bin/env python3
"""
Test direct database access with Pro tier capabilities.
"""
import os
import sys
from supabase import create_client

def test_api_access():
    """Test if API access works now with Pro tier."""
    url = "https://vlbvrhotrlipaoedudys.supabase.co"

    # Try with service role key
    with open('.streamlit/secrets.toml', 'r') as f:
        content = f.read()
        # Extract key from TOML
        for line in content.split('\n'):
            if 'key =' in line:
                key = line.split('=')[1].strip().strip('"')
                break

    print("Testing API access with service_role key...")
    print(f"URL: {url}")
    print(f"Key: {key[:20]}...")

    try:
        client = create_client(url, key)

        # Test SELECT
        print("\n1. Testing SELECT query...")
        response = client.table('companies').select('*').limit(1).execute()
        print(f"   ✅ SELECT successful! Found {len(response.data)} rows")
        if response.data:
            print(f"   Sample: {response.data[0]}")

        # Test INSERT (we'll delete it right after)
        print("\n2. Testing INSERT operation...")
        test_data = {
            'company_id': '00000000-0000-0000-0000-000000000001',
            'company_name': 'API_TEST_COMPANY',
            'industry': 'TEST',
            'region': 'TEST'
        }
        insert_response = client.table('companies').insert(test_data).execute()
        print(f"   ✅ INSERT successful!")

        # Clean up test data
        print("\n3. Cleaning up test data...")
        client.table('companies').delete().eq('company_id', '00000000-0000-0000-0000-000000000001').execute()
        print(f"   ✅ DELETE successful!")

        print("\n✅ All API operations working with Pro tier!")
        return True

    except Exception as e:
        print(f"\n❌ API Error: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def check_database_info():
    """Check what database connection information is available."""
    print("\n" + "="*60)
    print("CHECKING DATABASE CONNECTION OPTIONS")
    print("="*60)

    # Check for environment variables
    print("\nEnvironment variables (database-related):")
    for key in os.environ.keys():
        if any(x in key.upper() for x in ['SUPABASE', 'DATABASE', 'POSTGRES', 'DB_']):
            value = os.environ[key]
            if 'PASSWORD' in key.upper() or 'KEY' in key.upper():
                value = value[:20] + '...' if len(value) > 20 else value
            print(f"  {key} = {value}")

    print("\nChecking for .env files:")
    for env_file in ['.env', '.env.local', 'supabase/.env']:
        if os.path.exists(env_file):
            print(f"  ✅ Found: {env_file}")
        else:
            print(f"  ❌ Not found: {env_file}")

if __name__ == '__main__':
    print("Testing Direct Database Access (Pro Tier)")
    print("=" * 60)

    # First test API access
    api_works = test_api_access()

    # Check database connection info
    check_database_info()

    if api_works:
        print("\n" + "="*60)
        print("✅ DATABASE ACCESS CONFIRMED - Ready to proceed!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("⚠️  API still blocked - checking for direct PostgreSQL access...")
        print("="*60)
