"""Initialize database"""
import os
from config.database import get_engine, test_connection
from dotenv import load_dotenv

load_dotenv()

def setup_database():
    success, msg = test_connection()
    if not success:
        print(f"❌ {msg}")
        return

    print("✓ Connected to database")

    with open('database/schema.sql', 'r') as f:
        schema = f.read()

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(schema)
        conn.commit()

    print("✓ Schema created")

if __name__ == '__main__':
    setup_database()
