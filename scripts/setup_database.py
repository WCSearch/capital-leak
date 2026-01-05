"""Test Supabase connection"""
import os
from config.database import get_client, test_connection
from dotenv import load_dotenv

load_dotenv()

def setup_database():
    """
    Note: With Supabase free tier, database schema must be created via:
    1. Supabase Dashboard UI (recommended for free tier)
    2. SQL Editor in Supabase Dashboard
    3. Direct PostgreSQL connection (requires paid plan with direct access)

    This script only tests the API connection.
    """
    success, msg = test_connection()
    if not success:
        print(f"❌ Connection failed: {msg}")
        print("\nMake sure:")
        print("1. SUPABASE_URL and SUPABASE_KEY are set in .env")
        print("2. Your Supabase project is active")
        print("3. Tables are created in Supabase Dashboard")
        return

    print("✓ Connected to Supabase via API")
    print("\nTo create database schema:")
    print("1. Go to Supabase Dashboard > SQL Editor")
    print("2. Run the SQL from database/schema.sql")

    client = get_client()

    # Try to list existing tables
    try:
        # This will show what tables exist
        companies = client.table('companies').select('count').limit(0).execute()
        print("✓ 'companies' table exists")
    except Exception as e:
        print("⚠ 'companies' table not found - create schema first")

if __name__ == '__main__':
    setup_database()
