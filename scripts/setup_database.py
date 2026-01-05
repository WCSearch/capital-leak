"""Test Supabase connection and provide setup instructions"""
import os
from config.database import get_client, test_connection
from dotenv import load_dotenv

load_dotenv()

def setup_database():
    """Test connection and provide schema setup instructions"""
    print("Testing Supabase connection...")
    success, msg = test_connection()

    if not success:
        print(f"❌ Connection failed: {msg}")
        print("\nPlease check your .env file contains:")
        print("  SUPABASE_URL=https://your-project.supabase.co")
        print("  SUPABASE_KEY=your-anon-key")
        return

    print(f"✓ {msg}")
    print("\nTo set up the database schema:")
    print("1. Go to your Supabase Dashboard")
    print("2. Navigate to SQL Editor")
    print("3. Run the SQL script from database/schema.sql")
    print("\nAlternatively, create the tables through the Supabase Table Editor UI")

if __name__ == '__main__':
    setup_database()
