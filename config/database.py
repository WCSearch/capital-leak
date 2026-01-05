"""Database connection and configuration for Supabase API"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_client():
    """Get the Supabase client instance"""
    return supabase

def test_connection():
    """Test the Supabase connection"""
    try:
        # Try a simple query to check connection
        result = supabase.table('companies').select('company_id').limit(1).execute()
        return True, "Connected to Supabase"
    except Exception as e:
        return False, str(e)
