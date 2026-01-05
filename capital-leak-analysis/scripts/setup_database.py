"""
Database setup script
Creates database and initializes schema
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config.database import DatabaseConfig
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_database():
    """Create the database if it doesn't exist"""
    config = DatabaseConfig()

    # Connect to PostgreSQL server (postgres database)
    try:
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with conn.cursor() as cursor:
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (config.database,)
            )
            exists = cursor.fetchone()

            if not exists:
                logger.info(f"Creating database: {config.database}")
                cursor.execute(f"CREATE DATABASE {config.database}")
                logger.info(f"Database {config.database} created successfully")
            else:
                logger.info(f"Database {config.database} already exists")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        return False


def run_schema_script():
    """Execute the schema.sql file"""
    config = DatabaseConfig()
    schema_file = Path(__file__).parent.parent / 'database' / 'schema.sql'

    if not schema_file.exists():
        logger.error(f"Schema file not found: {schema_file}")
        return False

    try:
        # Read schema file
        with open(schema_file, 'r') as f:
            schema_sql = f.read()

        # Connect to the database
        conn = psycopg2.connect(**config.get_psycopg2_params())

        with conn.cursor() as cursor:
            logger.info("Executing schema script...")
            cursor.execute(schema_sql)
            conn.commit()
            logger.info("Schema created successfully")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error executing schema: {str(e)}")
        return False


def verify_setup():
    """Verify that tables were created"""
    config = DatabaseConfig()

    try:
        conn = psycopg2.connect(**config.get_psycopg2_params())

        with conn.cursor() as cursor:
            # Check for main tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = [
                'customers',
                'vendors',
                'products',
                'invoices',
                'inventory_movements',
                'payables',
                'revenue',
                'analysis_results'
            ]

            logger.info("\nDatabase Tables:")
            logger.info("-" * 50)
            for table in tables:
                status = "✓" if table in expected_tables else " "
                logger.info(f"{status} {table}")

            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                logger.warning(f"\nMissing tables: {missing_tables}")
                return False

            # Check for views
            cursor.execute("""
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            views = [row[0] for row in cursor.fetchall()]
            logger.info("\nDatabase Views:")
            logger.info("-" * 50)
            for view in views:
                logger.info(f"✓ {view}")

            # Check for functions
            cursor.execute("""
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = 'public'
                  AND routine_type = 'FUNCTION'
                ORDER BY routine_name
            """)

            functions = [row[0] for row in cursor.fetchall()]
            logger.info("\nDatabase Functions:")
            logger.info("-" * 50)
            for func in functions:
                logger.info(f"✓ {func}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error verifying setup: {str(e)}")
        return False


def insert_sample_data():
    """Insert sample data for testing"""
    config = DatabaseConfig()

    sample_data = {
        'customers': [
            ("C001", "Acme Corporation", "Enterprise", 100000.00, 30),
            ("C002", "TechStart Inc", "SMB", 50000.00, 45),
            ("C003", "Global Industries", "Enterprise", 200000.00, 60),
        ],
        'vendors': [
            ("V001", "Supplier One", "Raw Materials", 30),
            ("V002", "Supplier Two", "Components", 45),
            ("V003", "Logistics Inc", "Services", 15),
        ],
        'products': [
            ("SKU001", "Product A", "Electronics", "Gadgets", 50.00, 100.00),
            ("SKU002", "Product B", "Electronics", "Accessories", 20.00, 40.00),
            ("SKU003", "Product C", "Hardware", "Tools", 30.00, 60.00),
        ]
    }

    try:
        conn = psycopg2.connect(**config.get_psycopg2_params())

        with conn.cursor() as cursor:
            # Insert customers
            logger.info("Inserting sample customers...")
            for customer in sample_data['customers']:
                cursor.execute("""
                    INSERT INTO customers (customer_id, customer_name, customer_type, credit_limit, payment_terms_days)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (customer_id) DO NOTHING
                """, customer)

            # Insert vendors
            logger.info("Inserting sample vendors...")
            for vendor in sample_data['vendors']:
                cursor.execute("""
                    INSERT INTO vendors (vendor_id, vendor_name, vendor_type, payment_terms_days)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (vendor_id) DO NOTHING
                """, vendor)

            # Insert products
            logger.info("Inserting sample products...")
            for product in sample_data['products']:
                cursor.execute("""
                    INSERT INTO products (sku, product_name, category, subcategory, unit_cost, unit_price)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sku) DO NOTHING
                """, product)

            conn.commit()
            logger.info("Sample data inserted successfully")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error inserting sample data: {str(e)}")
        return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("Capital Leak Analysis - Database Setup")
    print("=" * 60)
    print()

    # Step 1: Create database
    print("Step 1: Creating database...")
    if not create_database():
        print("❌ Failed to create database")
        sys.exit(1)
    print("✓ Database ready")
    print()

    # Step 2: Run schema
    print("Step 2: Creating schema...")
    if not run_schema_script():
        print("❌ Failed to create schema")
        sys.exit(1)
    print("✓ Schema created")
    print()

    # Step 3: Verify setup
    print("Step 3: Verifying setup...")
    if not verify_setup():
        print("❌ Verification failed")
        sys.exit(1)
    print("✓ Verification successful")
    print()

    # Step 4: Ask about sample data
    response = input("Insert sample data for testing? (y/n): ").lower()
    if response == 'y':
        print("\nStep 4: Inserting sample data...")
        if insert_sample_data():
            print("✓ Sample data inserted")
        else:
            print("⚠ Failed to insert sample data (non-critical)")
    print()

    print("=" * 60)
    print("Database setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Load your ERP data using the ETL pipeline")
    print("2. Run analysis: python app/main.py")
    print()


if __name__ == "__main__":
    main()
