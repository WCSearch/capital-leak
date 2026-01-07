"""
Setup RLS Policies for Supabase

This script provides instructions and SQL for setting up Row Level Security policies
to allow the synthetic data ingestion to work with the anon API key.

Author: Capital Leak Analysis Team
Date: 2025-01-07
"""

from pathlib import Path
import os

def print_instructions():
    """Print instructions for setting up RLS policies"""

    sql_file = Path(__file__).parent.parent / "database" / "rls_policies.sql"

    print("=" * 80)
    print("SUPABASE RLS POLICY SETUP")
    print("=" * 80)
    print()
    print("The data ingestion failed with 403 Forbidden errors because Supabase has")
    print("Row Level Security (RLS) enabled, but no policies allow inserts via the API.")
    print()
    print("=" * 80)
    print("SETUP INSTRUCTIONS")
    print("=" * 80)
    print()
    print("1. Go to your Supabase Dashboard:")
    print("   https://app.supabase.com/project/vlbvrhotrlipaoedudys")
    print()
    print("2. Navigate to: SQL Editor (left sidebar)")
    print()
    print("3. Click 'New Query'")
    print()
    print("4. Copy and paste the SQL from:")
    print(f"   {sql_file}")
    print()
    print("5. Click 'Run' to execute the SQL")
    print()
    print("6. Verify success - you should see:")
    print("   'Success. No rows returned'")
    print()
    print("7. Re-run the ingestion script:")
    print("   python scripts/ingest_synthetic_data.py")
    print()
    print("=" * 80)
    print("SQL PREVIEW")
    print("=" * 80)
    print()

    # Read and display first few lines of SQL
    if sql_file.exists():
        with open(sql_file, 'r') as f:
            lines = f.readlines()[:30]
            for line in lines:
                print(line.rstrip())
        print()
        print(f"... (see full SQL in {sql_file})")
    else:
        print(f"❌ SQL file not found: {sql_file}")
        return

    print()
    print("=" * 80)
    print("ALTERNATIVE: Copy SQL to Clipboard")
    print("=" * 80)
    print()
    print("Run this command to copy the SQL to your clipboard:")
    print(f"  cat {sql_file} | pbcopy    # macOS")
    print(f"  cat {sql_file} | xclip     # Linux")
    print()
    print("=" * 80)

def main():
    print_instructions()

if __name__ == "__main__":
    main()
