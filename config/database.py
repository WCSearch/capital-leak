"""Database connection and configuration using Supabase API"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_client():
    """Returns the Supabase client instance"""
    return supabase

def test_connection():
    """Test Supabase connection by attempting a simple query"""
    try:
        # Try to query a table (will fail gracefully if no tables exist)
        result = supabase.table('companies').select('count').limit(0).execute()
        return True, "Connected to Supabase"
    except Exception as e:
        return False, str(e)
