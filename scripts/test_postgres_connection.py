#!/usr/bin/env python3
"""
Test direct PostgreSQL database connection using psycopg2.
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

print("Testing Direct PostgreSQL Connection")
print("=" * 60)
print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'hidden'}")
print()

try:
    # Connect to database
    print("1. Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cursor = conn.cursor()
    print("   ✅ Connection successful!")

    # Test SELECT - list all tables
    print("\n2. Listing all tables in public schema...")
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()
    print(f"   ✅ Found {len(tables)} tables:")
    for table in tables:
        print(f"      - {table[0]}")

    # Test SELECT from companies table
    print("\n3. Testing SELECT from companies table...")
    cursor.execute("SELECT COUNT(*) FROM companies;")
    count = cursor.fetchone()[0]
    print(f"   ✅ Companies table has {count} rows")

    # Check RLS status
    print("\n4. Checking Row Level Security status...")
    cursor.execute("""
        SELECT tablename,
               CASE WHEN rowsecurity THEN 'ENABLED' ELSE 'DISABLED' END as rls_status
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)
    rls_status = cursor.fetchall()
    print("   Current RLS status:")
    for table, status in rls_status:
        symbol = "🔒" if status == "ENABLED" else "🔓"
        print(f"      {symbol} {table}: {status}")

    # Test INSERT (we'll rollback after)
    print("\n5. Testing INSERT operation...")
    cursor.execute("""
        INSERT INTO companies (company_id, company_name, industry, region)
        VALUES ('00000000-0000-0000-0000-000000000099', 'DIRECT_DB_TEST', 'TEST', 'TEST')
        RETURNING company_id, company_name;
    """)
    inserted = cursor.fetchone()
    print(f"   ✅ INSERT successful: {inserted}")

    print("\n6. Rolling back test INSERT...")
    conn.rollback()
    print(f"   ✅ Rollback successful (test data not persisted)")

    # Check current user/role
    print("\n7. Checking database user and roles...")
    cursor.execute("SELECT current_user, session_user;")
    user_info = cursor.fetchone()
    print(f"   Current user: {user_info[0]}")
    print(f"   Session user: {user_info[1]}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ DIRECT DATABASE ACCESS CONFIRMED!")
    print("✅ All PostgreSQL operations working!")
    print("=" * 60)
    print("\nReady to:")
    print("  • Ingest synthetic data")
    print("  • Re-enable RLS security")
    print("  • Validate data integrity")

except Exception as e:
    print(f"\n❌ Database Error: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
