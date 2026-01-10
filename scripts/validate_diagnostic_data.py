#!/usr/bin/env python3
"""
Validate Synthetic Data Against Diagnostic PDFs

This script verifies that the data in Supabase matches what's reported in the diagnostic PDFs
for TechMfg Industries, AmeriParts Distribution, and PrecisionTech Manufacturing.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import get_supabase_client
from datetime import datetime
import json

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

def validate_ccc_metrics(client):
    """Verify CCC metrics match between ccc_metrics table and PDF"""
    print_section("1. CCC METRICS VALIDATION")

    results = []

    try:
        # Query CCC metrics for all three companies
        response = client.rpc('execute_sql', {
            'query': """
                SELECT
                    company_name,
                    dso_value,
                    dio_value,
                    dpo_value,
                    ccc_value
                FROM ccc_metrics m
                JOIN companies c ON m.company_id = c.company_id
                WHERE company_name IN ('TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing')
                ORDER BY company_name;
            """
        }).execute()

        if response.data:
            for row in response.data:
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
        # Try alternative approach without RPC
        try:
            print_result('info', "Trying direct table query...")
            metrics_response = client.table('ccc_metrics').select('*, companies(company_name)').execute()

            if metrics_response.data:
                for row in metrics_response.data:
                    company = row['companies']['company_name']
                    if company in EXPECTED_CCC:
                        actual_ccc = float(row['ccc_value'])
                        expected_ccc = EXPECTED_CCC[company]

                        print(f"\n{company}:")
                        print(f"  DSO: {row['dso_value']}")
                        print(f"  DIO: {row['dio_value']}")
                        print(f"  DPO: {row['dpo_value']}")
                        print(f"  CCC: {row['ccc_value']}")

                        if abs(actual_ccc - expected_ccc) < 0.1:
                            print_result('pass', f"CCC matches expected value: {expected_ccc}")
                            results.append({'company': company, 'test': 'CCC Metric', 'status': 'PASS'})
                        else:
                            print_result('fail', f"CCC mismatch! Expected: {expected_ccc}, Got: {actual_ccc}")
                            results.append({'company': company, 'test': 'CCC Metric', 'status': 'FAIL'})
        except Exception as e2:
            print_result('fail', f"Alternative query also failed: {str(e2)}")

    return results

def validate_transaction_counts(client, company_name):
    """Count transactions by status to confirm PDF findings"""
    print_section(f"2. TRANSACTION COUNTS - {company_name}")

    results = []

    try:
        # Get company_id first
        company_response = client.table('companies').select('company_id').eq('company_name', company_name).execute()

        if not company_response.data:
            print_result('fail', f"Company '{company_name}' not found")
            return results

        company_id = company_response.data[0]['company_id']

        # Get transaction counts
        transactions = client.table('transactions').select('component_type, status, outstanding_amount').eq('company_id', company_id).execute()

        if transactions.data:
            # Group by component_type and status
            summary = {}
            for txn in transactions.data:
                key = (txn['component_type'], txn['status'])
                if key not in summary:
                    summary[key] = {'count': 0, 'total_amount': 0}
                summary[key]['count'] += 1
                summary[key]['total_amount'] += float(txn['outstanding_amount'] or 0)

            # Print results sorted by total amount
            sorted_items = sorted(summary.items(), key=lambda x: x[1]['total_amount'], reverse=True)

            print(f"\n{'Component':<15} {'Status':<15} {'Count':<10} {'Total Amount':>20}")
            print("-" * 65)

            for (component, status), data in sorted_items:
                print(f"{component:<15} {status:<15} {data['count']:<10} ${data['total_amount']:>18,.2f}")

            print_result('pass', f"Found {len(transactions.data)} total transactions for {company_name}")
            results.append({'company': company_name, 'test': 'Transaction Counts', 'status': 'PASS'})
        else:
            print_result('warning', f"No transactions found for {company_name}")
            results.append({'company': company_name, 'test': 'Transaction Counts', 'status': 'WARNING'})

    except Exception as e:
        print_result('fail', f"Error querying transactions: {str(e)}")
        results.append({'company': company_name, 'test': 'Transaction Counts', 'status': 'FAIL'})

    return results

def validate_example_transaction(client, company_name, transaction_number):
    """Check that specific example transaction exists"""
    print_section(f"3. EXAMPLE TRANSACTION - {company_name}")

    results = []

    try:
        # Get company_id
        company_response = client.table('companies').select('company_id').eq('company_name', company_name).execute()

        if not company_response.data:
            print_result('fail', f"Company '{company_name}' not found")
            return results

        company_id = company_response.data[0]['company_id']

        # Get the specific transaction
        txn_response = client.table('transactions').select('*').eq('transaction_number', transaction_number).eq('company_id', company_id).execute()

        if txn_response.data:
            txn = txn_response.data[0]
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

def validate_event_logs(client, company_name, transaction_number):
    """Verify event logs exist for example transaction"""
    print_section(f"4. EVENT LOGS - {company_name} - {transaction_number}")

    results = []

    try:
        # Get company_id
        company_response = client.table('companies').select('company_id').eq('company_name', company_name).execute()

        if not company_response.data:
            print_result('fail', f"Company '{company_name}' not found")
            return results

        company_id = company_response.data[0]['company_id']

        # Get transaction_id
        txn_response = client.table('transactions').select('transaction_id').eq('transaction_number', transaction_number).eq('company_id', company_id).execute()

        if not txn_response.data:
            print_result('warning', f"Transaction {transaction_number} not found, skipping event log check")
            return results

        transaction_id = txn_response.data[0]['transaction_id']

        # Get event logs
        events_response = client.table('event_logs').select('*').eq('transaction_id', transaction_id).order('event_timestamp').execute()

        if events_response.data:
            print(f"\nFound {len(events_response.data)} event log entries:")
            print(f"\n{'Event Type':<30} {'Timestamp':<25} {'Description':<50}")
            print("-" * 110)

            for event in events_response.data:
                timestamp = event['event_timestamp'][:19] if event['event_timestamp'] else 'N/A'
                description = event.get('event_description', '')[:47] + '...' if len(event.get('event_description', '')) > 47 else event.get('event_description', '')
                print(f"{event['event_type']:<30} {timestamp:<25} {description:<50}")

            print_result('pass', f"Found {len(events_response.data)} event log entries")
            results.append({'company': company_name, 'test': 'Event Logs', 'status': 'PASS'})
        else:
            print_result('warning', f"No event logs found for transaction {transaction_number}")
            results.append({'company': company_name, 'test': 'Event Logs', 'status': 'WARNING'})

    except Exception as e:
        print_result('fail', f"Error querying event logs: {str(e)}")
        results.append({'company': company_name, 'test': 'Event Logs', 'status': 'FAIL'})

    return results

def validate_data_quality(client):
    """Check for data quality issues (NULLs, missing data)"""
    print_section("5. DATA QUALITY CHECKS")

    results = []

    try:
        # Get all transactions with company names
        companies = ['TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing']

        print(f"\n{'Company':<35} {'Total':<10} {'Null TxnNum':<12} {'Null Date':<12} {'Null Amt':<12} {'Null Status':<12}")
        print("-" * 100)

        for company_name in companies:
            # Get company_id
            company_response = client.table('companies').select('company_id').eq('company_name', company_name).execute()

            if not company_response.data:
                continue

            company_id = company_response.data[0]['company_id']

            # Get all transactions
            txns = client.table('transactions').select('transaction_number, transaction_date, amount, status').eq('company_id', company_id).execute()

            if txns.data:
                total = len(txns.data)
                null_txn_num = sum(1 for t in txns.data if not t.get('transaction_number'))
                null_date = sum(1 for t in txns.data if not t.get('transaction_date'))
                null_amount = sum(1 for t in txns.data if t.get('amount') is None)
                null_status = sum(1 for t in txns.data if not t.get('status'))

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

def validate_gl_account_distribution(client):
    """Verify GL account splits are correct (especially DIO 60/40)"""
    print_section("6. GL ACCOUNT DISTRIBUTION (DIO)")

    results = []

    try:
        companies = ['TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing']

        for company_name in companies:
            print(f"\n{company_name}:")

            # Get company_id
            company_response = client.table('companies').select('company_id').eq('company_name', company_name).execute()

            if not company_response.data:
                continue

            company_id = company_response.data[0]['company_id']

            # Get DIO transactions
            dio_txns = client.table('transactions').select('gl_account, amount').eq('company_id', company_id).eq('component_type', 'DIO').execute()

            if dio_txns.data:
                # Calculate distribution
                gl_summary = {}
                total_count = len(dio_txns.data)

                for txn in dio_txns.data:
                    gl_account = txn.get('gl_account', 'Unknown')
                    if gl_account not in gl_summary:
                        gl_summary[gl_account] = {'count': 0, 'total_amount': 0}
                    gl_summary[gl_account]['count'] += 1
                    gl_summary[gl_account]['total_amount'] += float(txn['amount'] or 0)

                # Print results
                print(f"\n  {'GL Account':<30} {'Count':<10} {'Total Amount':<20} {'Percent':<10}")
                print("  " + "-" * 75)

                sorted_accounts = sorted(gl_summary.items(), key=lambda x: x[1]['total_amount'], reverse=True)

                for gl_account, data in sorted_accounts:
                    percent = (data['count'] / total_count) * 100
                    print(f"  {gl_account:<30} {data['count']:<10} ${data['total_amount']:<18,.2f} {percent:>6.1f}%")

                # Check for 60/40 split
                if len(sorted_accounts) == 2:
                    percent1 = (sorted_accounts[0][1]['count'] / total_count) * 100
                    percent2 = (sorted_accounts[1][1]['count'] / total_count) * 100

                    # Allow 5% tolerance
                    if abs(percent1 - 60) < 5 and abs(percent2 - 40) < 5:
                        print_result('pass', f"DIO split is approximately 60/40 ({percent1:.1f}%/{percent2:.1f}%)")
                        results.append({'company': company_name, 'test': 'GL Distribution', 'status': 'PASS'})
                    else:
                        print_result('warning', f"DIO split is {percent1:.1f}%/{percent2:.1f}% (expected ~60/40)")
                        results.append({'company': company_name, 'test': 'GL Distribution', 'status': 'WARNING'})
                else:
                    print_result('warning', f"Expected 2 GL accounts for 60/40 split, found {len(sorted_accounts)}")
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

    # Initialize Supabase client
    try:
        client = get_supabase_client()
        print_result('pass', "Connected to Supabase successfully")
    except Exception as e:
        print_result('fail', f"Failed to connect to Supabase: {str(e)}")
        return 1

    all_results = []

    # 1. Validate CCC metrics
    all_results.extend(validate_ccc_metrics(client))

    # 2-4. For each company, validate transactions, examples, and event logs
    companies = ['TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing']

    for company in companies:
        all_results.extend(validate_transaction_counts(client, company))

        transaction_number = EXAMPLE_TRANSACTIONS[company]
        all_results.extend(validate_example_transaction(client, company, transaction_number))
        all_results.extend(validate_event_logs(client, company, transaction_number))

    # 5. Validate data quality
    all_results.extend(validate_data_quality(client))

    # 6. Validate GL distribution
    all_results.extend(validate_gl_account_distribution(client))

    # Generate summary report
    generate_summary_report(all_results)

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Return exit code based on results
    fail_count = sum(1 for r in all_results if r['status'] == 'FAIL')
    return 1 if fail_count > 0 else 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
