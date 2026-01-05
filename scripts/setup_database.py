"""Initialize database using Supabase

Note: Database schema should be created through Supabase Dashboard or SQL Editor.
This script is for testing the connection and verifying setup.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_database():
    """
    Test Supabase connection and verify database setup.

    Note: For Supabase, you should create tables using:
    1. Supabase Dashboard → SQL Editor
    2. Run the schema from database/schema.sql
    3. Or use Supabase migrations
    """
    print("=" * 60)
    print("Supabase Database Setup Verification")
    print("=" * 60)

    try:
        # Import after adding parent to path
        from config.database import get_supabase_client, test_connection

        print("\n1. Initializing Supabase client...")
        client = get_supabase_client()
        print("✓ Supabase client initialized")

        print("\n2. Testing connection...")
        success, msg = test_connection(client)

        if not success:
            print(f"❌ Connection failed: {msg}")
            print("\nTroubleshooting:")
            print("- Verify Supabase URL and key in .streamlit/secrets.toml")
            print("- Check network connectivity")
            print("- Ensure Supabase project is active")
            return

        print(f"✓ {msg}")

        print("\n3. Verifying tables...")
        # Check if main tables exist by attempting to query them
        tables = ['companies', 'ccc_metrics', 'transactions']
        for table in tables:
            try:
                client.table(table).select('*').limit(1).execute()
                print(f"✓ Table '{table}' exists and is accessible")
            except Exception as e:
                print(f"⚠ Table '{table}' not accessible: {str(e)}")
                print(f"  → Create it using Supabase Dashboard → SQL Editor")

        print("\n" + "=" * 60)
        print("Setup verification complete!")
        print("=" * 60)
        print("\nTo create tables:")
        print("1. Go to Supabase Dashboard → SQL Editor")
        print("2. Run the SQL from database/schema.sql")
        print("3. Or use Supabase CLI: supabase db push")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure:")
        print("1. .streamlit/secrets.toml exists with Supabase credentials")
        print("2. Supabase project is active and accessible")
        import traceback
        print("\nFull error:")
        traceback.print_exc()

if __name__ == '__main__':
    setup_database()
