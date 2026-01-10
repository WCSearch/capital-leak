#!/usr/bin/env python3
"""
Validate Synthetic Data Against Diagnostic PDFs using Direct PostgreSQL Connection

This script verifies that the data in Supabase matches what's reported in the diagnostic PDFs
for TechMfg Industries, AmeriParts Distribution, and PrecisionTech Manufacturing.
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Expected values from PDFs
EXPECTED_CCC = {
    'TechMfg Industries': 628.8,
    'AmeriParts Distribution': 124.8,
    'PrecisionTech Manufacturing': 2114.7
}

EXAMPLE_TRANSACTIONS = {
    'TechMfg Industries': 'INV-2024-000543',
    'AmeriParts Distribution': 'PART-515688',
    'PrecisionTech Manufacturing': 'ITEM-364255'
}

def get_db_connection():
    """Create a PostgreSQL database connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")

    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")

def print_result(status, message):
    """Print a validation result"""
    symbols = {
        'pass': '✅',
        'fail': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    print(f"{symbols.get(status, '•')} {message}")

def validate_ccc_metrics(conn):
    """Verify CCC metrics match between ccc_metrics table and PDF"""
    print_section("1. CCC METRICS VALIDATION")

    results = []

    try:
        with conn.cursor() as cur:
            query = """
                SELECT
                    c.company_name,
                    m.dso_value,
                    m.dio_value,
                    m.dpo_value,
                    m.ccc_value
                FROM ccc_metrics m
                JOIN companies c ON m.company_id = c.company_id
                WHERE c.company_name IN ('TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing')
                ORDER BY c.company_name;
            """
            cur.execute(query)
            rows = cur.fetchall()

            if rows:
                for row in rows:
                    company = row['company_name']
                    actual_ccc = float(row['ccc_value'])
                    expected_ccc = EXPECTED_CCC[company]

                    print(f"\n{company}:")
                    print(f"  DSO: {row['dso_value']}")
                    print(f"  DIO: {row['dio_value']}")
                    print(f"  DPO: {row['dpo_value']}")
                    print(f"  CCC: {row['ccc_value']}")

                    # Check if CCC matches (allow 0.1 tolerance for rounding)
                    if abs(actual_ccc - expected_ccc) < 0.1:
                        print_result('pass', f"CCC matches expected value: {expected_ccc}")
                        results.append({'company': company, 'test': 'CCC Metric', 'status': 'PASS'})
                    else:
                        print_result('fail', f"CCC mismatch! Expected: {expected_ccc}, Got: {actual_ccc}")
                        results.append({'company': company, 'test': 'CCC Metric', 'status': 'FAIL'})
            else:
                print_result('fail', "No CCC metrics found in database")

    except Exception as e:
        print_result('fail', f"Error querying CCC metrics: {str(e)}")

    return results

def validate_transaction_counts(conn, company_name):
    """Count transactions by status to confirm PDF findings"""
    print_section(f"2. TRANSACTION COUNTS - {company_name}")

    results = []

    try:
        with conn.cursor() as cur:
            # Get company_id first
            cur.execute("SELECT company_id FROM companies WHERE company_name = %s", (company_name,))
            company_row = cur.fetchone()

            if not company_row:
                print_result('fail', f"Company '{company_name}' not found")
                return results

            company_id = company_row['company_id']

            # Get transaction counts
            query = """
                SELECT
                    component_type,
                    status,
                    COUNT(*) as count,
                    SUM(outstanding_amount) as total_amount
                FROM transactions
                WHERE company_id = %s
                GROUP BY component_type, status
                ORDER BY total_amount DESC;
            """
            cur.execute(query, (company_id,))
            rows = cur.fetchall()

            if rows:
                print(f"\n{'Component':<15} {'Status':<15} {'Count':<10} {'Total Amount':>20}")
                print("-" * 65)

                for row in rows:
                    print(f"{row['component_type']:<15} {row['status']:<15} {row['count']:<10} ${float(row['total_amount']):>18,.2f}")

                total_txns = sum(row['count'] for row in rows)
                print_result('pass', f"Found {total_txns} total transactions for {company_name}")
                results.append({'company': company_name, 'test': 'Transaction Counts', 'status': 'PASS'})
            else:
                print_result('warning', f"No transactions found for {company_name}")
                results.append({'company': company_name, 'test': 'Transaction Counts', 'status': 'WARNING'})

    except Exception as e:
        print_result('fail', f"Error querying transactions: {str(e)}")
        results.append({'company': company_name, 'test': 'Transaction Counts', 'status': 'FAIL'})

    return results

def validate_example_transaction(conn, company_name, transaction_number):
    """Check that specific example transaction exists"""
    print_section(f"3. EXAMPLE TRANSACTION - {company_name}")

    results = []

    try:
        with conn.cursor() as cur:
            # Get company_id
            cur.execute("SELECT company_id FROM companies WHERE company_name = %s", (company_name,))
            company_row = cur.fetchone()

            if not company_row:
                print_result('fail', f"Company '{company_name}' not found")
                return results

            company_id = company_row['company_id']

            # Get the specific transaction
            query = """
                SELECT *
                FROM transactions
                WHERE transaction_number = %s AND company_id = %s
            """
            cur.execute(query, (transaction_number, company_id))
            txn = cur.fetchone()

            if txn:
                print(f"\nTransaction Number: {txn['transaction_number']}")
                print(f"Component Type: {txn['component_type']}")
                print(f"Amount: ${float(txn['amount']):,.2f}")
                print(f"Outstanding Amount: ${float(txn['outstanding_amount']):,.2f}")
                print(f"Status: {txn['status']}")
                print(f"Transaction Date: {txn['transaction_date']}")
                print(f"GL Account: {txn.get('gl_account', 'N/A')}")

                print_result('pass', f"Example transaction {transaction_number} exists")
                results.append({'company': company_name, 'test': 'Example Transaction', 'status': 'PASS'})
            else:
                print_result('fail', f"Example transaction {transaction_number} not found")
                results.append({'company': company_name, 'test': 'Example Transaction', 'status': 'FAIL'})

    except Exception as e:
        print_result('fail', f"Error querying example transaction: {str(e)}")
        results.append({'company': company_name, 'test': 'Example Transaction', 'status': 'FAIL'})

    return results

def validate_event_logs(conn, company_name, transaction_number):
    """Verify event logs exist for example transaction"""
    print_section(f"4. EVENT LOGS - {company_name} - {transaction_number}")

    results = []

    try:
        with conn.cursor() as cur:
            # Get company_id
            cur.execute("SELECT company_id FROM companies WHERE company_name = %s", (company_name,))
            company_row = cur.fetchone()

            if not company_row:
                print_result('fail', f"Company '{company_name}' not found")
                return results

            company_id = company_row['company_id']

            # Get transaction_id
            cur.execute(
                "SELECT transaction_id FROM transactions WHERE transaction_number = %s AND company_id = %s",
                (transaction_number, company_id)
            )
            txn_row = cur.fetchone()

            if not txn_row:
                print_result('warning', f"Transaction {transaction_number} not found, skipping event log check")
                return results

            transaction_id = txn_row['transaction_id']

            # Get event logs
            query = """
                SELECT *
                FROM event_logs
                WHERE transaction_id = %s
                ORDER BY event_timestamp
            """
            cur.execute(query, (transaction_id,))
            events = cur.fetchall()

            if events:
                print(f"\nFound {len(events)} event log entries:")
                print(f"\n{'Event Type':<30} {'Timestamp':<25} {'Description':<50}")
                print("-" * 110)

                for event in events:
                    timestamp = str(event['event_timestamp'])[:19] if event['event_timestamp'] else 'N/A'
                    description = event.get('event_description', '')
                    if len(description) > 47:
                        description = description[:47] + '...'
                    print(f"{event['event_type']:<30} {timestamp:<25} {description:<50}")

                print_result('pass', f"Found {len(events)} event log entries")
                results.append({'company': company_name, 'test': 'Event Logs', 'status': 'PASS'})
            else:
                print_result('warning', f"No event logs found for transaction {transaction_number}")
                results.append({'company': company_name, 'test': 'Event Logs', 'status': 'WARNING'})

    except Exception as e:
        print_result('fail', f"Error querying event logs: {str(e)}")
        results.append({'company': company_name, 'test': 'Event Logs', 'status': 'FAIL'})

    return results

def validate_data_quality(conn):
    """Check for data quality issues (NULLs, missing data)"""
    print_section("5. DATA QUALITY CHECKS")

    results = []

    try:
        companies = ['TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing']

        print(f"\n{'Company':<35} {'Total':<10} {'Null TxnNum':<12} {'Null Date':<12} {'Null Amt':<12} {'Null Status':<12}")
        print("-" * 100)

        with conn.cursor() as cur:
            for company_name in companies:
                # Get company_id
                cur.execute("SELECT company_id FROM companies WHERE company_name = %s", (company_name,))
                company_row = cur.fetchone()

                if not company_row:
                    continue

                company_id = company_row['company_id']

                # Get all transactions with NULL counts
                query = """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN transaction_number IS NULL THEN 1 ELSE 0 END) as null_txn_num,
                        SUM(CASE WHEN transaction_date IS NULL THEN 1 ELSE 0 END) as null_date,
                        SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) as null_amount,
                        SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END) as null_status
                    FROM transactions
                    WHERE company_id = %s
                """
                cur.execute(query, (company_id,))
                stats = cur.fetchone()

                if stats:
                    total = stats['total']
                    null_txn_num = stats['null_txn_num']
                    null_date = stats['null_date']
                    null_amount = stats['null_amount']
                    null_status = stats['null_status']

                    print(f"{company_name:<35} {total:<10} {null_txn_num:<12} {null_date:<12} {null_amount:<12} {null_status:<12}")

                    if null_txn_num == 0 and null_date == 0 and null_amount == 0 and null_status == 0:
                        print_result('pass', f"No NULL values found for {company_name}")
                        results.append({'company': company_name, 'test': 'Data Quality', 'status': 'PASS'})
                    else:
                        print_result('warning', f"Found NULL values for {company_name}")
                        results.append({'company': company_name, 'test': 'Data Quality', 'status': 'WARNING'})

    except Exception as e:
        print_result('fail', f"Error checking data quality: {str(e)}")
        results.append({'company': 'ALL', 'test': 'Data Quality', 'status': 'FAIL'})

    return results

def validate_gl_account_distribution(conn):
    """Verify GL account splits are correct (especially DIO 60/40)"""
    print_section("6. GL ACCOUNT DISTRIBUTION (DIO)")

    results = []

    try:
        companies = ['TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing']

        with conn.cursor() as cur:
            for company_name in companies:
                print(f"\n{company_name}:")

                # Get company_id
                cur.execute("SELECT company_id FROM companies WHERE company_name = %s", (company_name,))
                company_row = cur.fetchone()

                if not company_row:
                    continue

                company_id = company_row['company_id']

                # Get DIO transactions grouped by GL account
                query = """
                    SELECT
                        gl_account,
                        COUNT(*) as count,
                        SUM(amount) as total_amount
                    FROM transactions
                    WHERE company_id = %s AND component_type = 'DIO'
                    GROUP BY gl_account
                    ORDER BY total_amount DESC
                """
                cur.execute(query, (company_id,))
                gl_accounts = cur.fetchall()

                if gl_accounts:
                    total_count = sum(row['count'] for row in gl_accounts)

                    print(f"\n  {'GL Account':<30} {'Count':<10} {'Total Amount':<20} {'Percent':<10}")
                    print("  " + "-" * 75)

                    for row in gl_accounts:
                        percent = (row['count'] / total_count) * 100
                        print(f"  {row['gl_account']:<30} {row['count']:<10} ${float(row['total_amount']):<18,.2f} {percent:>6.1f}%")

                    # Check for 60/40 split
                    if len(gl_accounts) == 2:
                        percent1 = (gl_accounts[0]['count'] / total_count) * 100
                        percent2 = (gl_accounts[1]['count'] / total_count) * 100

                        # Allow 5% tolerance
                        if abs(percent1 - 60) < 5 and abs(percent2 - 40) < 5:
                            print_result('pass', f"DIO split is approximately 60/40 ({percent1:.1f}%/{percent2:.1f}%)")
                            results.append({'company': company_name, 'test': 'GL Distribution', 'status': 'PASS'})
                        else:
                            print_result('warning', f"DIO split is {percent1:.1f}%/{percent2:.1f}% (expected ~60/40)")
                            results.append({'company': company_name, 'test': 'GL Distribution', 'status': 'WARNING'})
                    else:
                        print_result('warning', f"Expected 2 GL accounts for 60/40 split, found {len(gl_accounts)}")
                        results.append({'company': company_name, 'test': 'GL Distribution', 'status': 'WARNING'})
                else:
                    print_result('warning', f"No DIO transactions found")
                    results.append({'company': company_name, 'test': 'GL Distribution', 'status': 'WARNING'})

    except Exception as e:
        print_result('fail', f"Error checking GL distribution: {str(e)}")
        results.append({'company': 'ALL', 'test': 'GL Distribution', 'status': 'FAIL'})

    return results

def generate_summary_report(all_results):
    """Generate summary report of all validation results"""
    print_section("VALIDATION SUMMARY REPORT")

    # Count by status
    pass_count = sum(1 for r in all_results if r['status'] == 'PASS')
    fail_count = sum(1 for r in all_results if r['status'] == 'FAIL')
    warning_count = sum(1 for r in all_results if r['status'] == 'WARNING')

    print(f"\nTotal Tests: {len(all_results)}")
    print(f"✅ Passed: {pass_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"⚠️  Warnings: {warning_count}")

    # Group by company
    print("\n\nResults by Company:")
    print("-" * 80)

    companies = ['TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing']

    for company in companies:
        company_results = [r for r in all_results if r['company'] == company]
        if company_results:
            print(f"\n{company}:")
            for result in company_results:
                status_symbol = {'PASS': '✅', 'FAIL': '❌', 'WARNING': '⚠️'}[result['status']]
                print(f"  {status_symbol} {result['test']}: {result['status']}")

    # Overall status
    print("\n" + "=" * 80)
    if fail_count == 0 and warning_count == 0:
        print_result('pass', "ALL VALIDATIONS PASSED! Data matches diagnostic PDFs perfectly.")
    elif fail_count == 0:
        print_result('warning', f"All critical tests passed, but {warning_count} warnings were found.")
    else:
        print_result('fail', f"VALIDATION FAILED: {fail_count} tests failed.")
    print("=" * 80)

def main():
    """Main validation function"""
    print("\n" + "="*80)
    print(" DIAGNOSTIC PDF DATA VALIDATION")
    print(" Validating synthetic data against diagnostic PDFs")
    print("="*80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize database connection
    try:
        conn = get_db_connection()
        print_result('pass', "Connected to PostgreSQL database successfully")
    except Exception as e:
        print_result('fail', f"Failed to connect to database: {str(e)}")
        return 1

    all_results = []

    try:
        # 1. Validate CCC metrics
        all_results.extend(validate_ccc_metrics(conn))

        # 2-4. For each company, validate transactions, examples, and event logs
        companies = ['TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing']

        for company in companies:
            all_results.extend(validate_transaction_counts(conn, company))

            transaction_number = EXAMPLE_TRANSACTIONS[company]
            all_results.extend(validate_example_transaction(conn, company, transaction_number))
            all_results.extend(validate_event_logs(conn, company, transaction_number))

        # 5. Validate data quality
        all_results.extend(validate_data_quality(conn))

        # 6. Validate GL distribution
        all_results.extend(validate_gl_account_distribution(conn))

        # Generate summary report
        generate_summary_report(all_results)

    finally:
        conn.close()

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Return exit code based on results
    fail_count = sum(1 for r in all_results if r['status'] == 'FAIL')
    return 1 if fail_count > 0 else 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
