"""
Validate Synthetic SAP Data in Supabase

This script verifies that the synthetic data was loaded correctly
and that all intentional issues are present for testing.

Author: Capital Leak Analysis Team
Date: 2025-01-07
"""

import pandas as pd
from pathlib import Path
from supabase import create_client, Client
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
DATA_DIR = Path("data/synthetic")
OUTPUT_FILE = DATA_DIR / "validation_report.txt"

# Supabase connection
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://vlbvrhotrlipaoedudys.supabase.co")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "")

# For Supabase, we need the API URL and key, not the PostgreSQL URL
if SUPABASE_URL.startswith("postgresql://"):
    parts = SUPABASE_URL.split("@")
    if len(parts) > 1:
        host_part = parts[1].split(":")[0]
        project_ref = host_part.replace("db.", "").replace(".supabase.co", "")
        SUPABASE_URL = f"https://{project_ref}.supabase.co"

print("=" * 80)
print("SYNTHETIC SAP DATA VALIDATION")
print("=" * 80)


def get_supabase_client() -> Client:
    """Initialize Supabase client"""
    try:
        # Try to get from .streamlit/secrets.toml first
        secrets_file = Path(".streamlit/secrets.toml")
        if secrets_file.exists():
            import toml
            secrets = toml.load(secrets_file)
            url = secrets.get('supabase', {}).get('url', SUPABASE_URL)
            key = secrets.get('supabase', {}).get('key', SUPABASE_KEY)
        else:
            url = SUPABASE_URL
            key = SUPABASE_KEY

        client = create_client(url, key)
        print(f"✓ Connected to Supabase: {url}\n")
        return client
    except Exception as e:
        print(f"✗ Failed to connect to Supabase: {e}")
        sys.exit(1)


class ValidationReport:
    """Manages validation report output"""

    def __init__(self):
        self.lines = []
        self.checks_passed = 0
        self.checks_failed = 0

    def add_header(self, text):
        self.lines.append("=" * 80)
        self.lines.append(text)
        self.lines.append("=" * 80)

    def add_section(self, text):
        self.lines.append(f"\n{text}")
        self.lines.append("-" * 80)

    def add_check(self, name, expected, actual, passed=None):
        if passed is None:
            passed = expected == actual

        status = "✅" if passed else "❌"
        self.lines.append(f"{status} {name}")
        self.lines.append(f"   Expected: {expected}")
        self.lines.append(f"   Actual:   {actual}")

        if passed:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return passed

    def add_info(self, text):
        self.lines.append(f"   {text}")

    def add_line(self, text=""):
        self.lines.append(text)

    def save(self, filepath):
        with open(filepath, 'w') as f:
            f.write('\n'.join(self.lines))
        print(f"\n📄 Validation report saved to: {filepath}")

    def print_summary(self):
        self.add_line()
        self.add_header("VALIDATION SUMMARY")
        self.add_line(f"Total Checks: {self.checks_passed + self.checks_failed}")
        self.add_line(f"✅ Passed: {self.checks_passed}")
        self.add_line(f"❌ Failed: {self.checks_failed}")

        if self.checks_failed == 0:
            self.add_line("\n🎯 All validation checks passed!")
            self.add_line("✅ Dashboard ready for testing")
        else:
            self.add_line(f"\n⚠️  {self.checks_failed} validation check(s) failed")
            self.add_line("Please review the issues above before using the dashboard")

    def print_report(self):
        print('\n'.join(self.lines))


def validate_row_counts(client: Client, report: ValidationReport):
    """Validate row counts match CSV files"""
    report.add_section("Row Count Validation")

    tables = {
        'companies': 'companies.csv',
        'transactions': 'transactions.csv',
        'event_logs': 'event_logs.csv',
        'ccc_metrics': 'ccc_metrics.csv',
        'component_details': 'component_details.csv'
    }

    for table, csv_file in tables.items():
        csv_path = DATA_DIR / csv_file

        if csv_path.exists():
            csv_count = len(pd.read_csv(csv_path))

            try:
                response = client.table(table).select('*', count='exact').limit(1).execute()
                db_count = response.count
            except Exception as e:
                db_count = f"Error: {e}"
                report.add_check(f"{table} row count", csv_count, db_count, False)
                continue

            report.add_check(f"{table} row count", csv_count, db_count)
        else:
            report.add_info(f"⚠️  CSV file not found: {csv_file}")


def validate_referential_integrity(client: Client, report: ValidationReport):
    """Validate foreign key relationships"""
    report.add_section("Referential Integrity Validation")

    try:
        # Check: All transaction_ids in event_logs exist in transactions
        events_response = client.table('event_logs').select('transaction_id').execute()
        event_trans_ids = set([e['transaction_id'] for e in events_response.data if e['transaction_id']])

        trans_response = client.table('transactions').select('transaction_id').execute()
        trans_ids = set([t['transaction_id'] for t in trans_response.data])

        orphaned_events = event_trans_ids - trans_ids

        report.add_check(
            "Event logs reference valid transactions",
            0,
            len(orphaned_events),
            len(orphaned_events) == 0
        )

        if len(orphaned_events) > 0:
            report.add_info(f"Found {len(orphaned_events)} orphaned event logs")

        # Check: All company_ids are valid
        companies_response = client.table('companies').select('company_id').execute()
        company_ids = set([c['company_id'] for c in companies_response.data])

        # Check transactions
        trans_company_ids = set([t['company_id'] for t in trans_response.data])
        invalid_trans_companies = trans_company_ids - company_ids

        report.add_check(
            "Transactions reference valid companies",
            0,
            len(invalid_trans_companies),
            len(invalid_trans_companies) == 0
        )

    except Exception as e:
        report.add_info(f"❌ Error during referential integrity check: {e}")


def validate_date_ranges(client: Client, report: ValidationReport):
    """Validate date ranges are correct"""
    report.add_section("Date Range Validation")

    try:
        # Check transaction dates
        trans_response = client.table('transactions').select('transaction_date').execute()
        dates = pd.to_datetime([t['transaction_date'] for t in trans_response.data if t['transaction_date']])

        min_date = dates.min()
        max_date = dates.max()

        expected_start = "2024-01-01"
        expected_end = "2024-12-31"

        start_match = min_date.strftime('%Y-%m-%d') == expected_start
        end_match = max_date.strftime('%Y-%m-%d') <= expected_end

        report.add_check(
            "Transaction date range (start)",
            expected_start,
            min_date.strftime('%Y-%m-%d'),
            start_match
        )

        report.add_check(
            "Transaction date range (end)",
            f"<= {expected_end}",
            max_date.strftime('%Y-%m-%d'),
            end_match
        )

    except Exception as e:
        report.add_info(f"❌ Error during date range check: {e}")


def validate_dso_issues(client: Client, report: ValidationReport):
    """Validate DSO intentional issues are present"""
    report.add_section("DSO Issue Validation")

    try:
        # Issue #1: Billing trigger disabled (143 invoices)
        billing_disabled = client.table('transactions').select('*').eq('component_type', 'DSO').eq('status', 'FULFILLED_NOT_BILLED').execute()
        billing_count = len(billing_disabled.data)

        report.add_check(
            "DSO: Fulfilled but not billed (billing trigger disabled)",
            143,
            billing_count,
            130 <= billing_count <= 150  # Allow some tolerance
        )

        # Issue #2: Approver left company (31 invoices stuck in approval)
        approval_stuck = client.table('transactions').select('*').eq('component_type', 'DSO').eq('status', 'PENDING_APPROVAL').execute()
        approval_count = len(approval_stuck.data)

        report.add_check(
            "DSO: Stuck in approval (approver BWILSON left)",
            31,
            approval_count,
            25 <= approval_count <= 35  # Allow some tolerance
        )

        # Issue #3: Credit holds
        credit_holds = client.table('transactions').select('*').eq('component_type', 'DSO').eq('status', 'CREDIT_HOLD').execute()
        credit_count = len(credit_holds.data)

        report.add_check(
            "DSO: Credit holds (policy change)",
            "~150-200",
            credit_count,
            credit_count > 0
        )

        # Issue #4: Late payers
        late_payers = client.table('transactions').select('*').eq('component_type', 'DSO').eq('status', 'OVERDUE').execute()
        late_count = len(late_payers.data)

        report.add_check(
            "DSO: Late payers (behavioral)",
            187,
            late_count,
            170 <= late_count <= 200  # Allow some tolerance
        )

    except Exception as e:
        report.add_info(f"❌ Error during DSO issue validation: {e}")


def validate_dio_issues(client: Client, report: ValidationReport):
    """Validate DIO intentional issues are present"""
    report.add_section("DIO Issue Validation")

    try:
        # Issue #1: Goods receipt without valuation (87 items)
        gr_no_val = client.table('transactions').select('*').eq('component_type', 'DIO').eq('status', 'RECEIVED_NOT_VALUED').execute()
        gr_no_val_count = len(gr_no_val.data)

        report.add_check(
            "DIO: Goods receipts without valuation",
            87,
            gr_no_val_count,
            80 <= gr_no_val_count <= 95  # Allow some tolerance
        )

        # Issue #2: Quality hold stall (43 items)
        quality_hold = client.table('transactions').select('*').eq('component_type', 'DIO').eq('status', 'QUALITY_HOLD').execute()
        quality_count = len(quality_hold.data)

        report.add_check(
            "DIO: Quality hold stall (>48 hours)",
            43,
            quality_count,
            40 <= quality_count <= 50  # Allow some tolerance
        )

        # Issue #3: Ghost allocations (28 items)
        ghost_alloc = client.table('transactions').select('*').eq('component_type', 'DIO').eq('status', 'RESERVED_CANCELLED_ORDER').execute()
        ghost_count = len(ghost_alloc.data)

        report.add_check(
            "DIO: Ghost allocations (reserved for cancelled orders)",
            28,
            ghost_count,
            25 <= ghost_count <= 35  # Allow some tolerance
        )

        # Issue #4: Obsolete inventory (34 items)
        obsolete = client.table('transactions').select('*').eq('component_type', 'DIO').eq('status', 'OBSOLETE').execute()
        obsolete_count = len(obsolete.data)

        report.add_check(
            "DIO: Obsolete inventory (no movement >180 days)",
            34,
            obsolete_count,
            30 <= obsolete_count <= 40  # Allow some tolerance
        )

    except Exception as e:
        report.add_info(f"❌ Error during DIO issue validation: {e}")


def validate_dpo_issues(client: Client, report: ValidationReport):
    """Validate DPO intentional issues are present"""
    report.add_section("DPO Issue Validation")

    try:
        # Issue #1: Approval workflow bottleneck (56 invoices)
        approval_stuck = client.table('transactions').select('*').eq('component_type', 'DPO').eq('status', 'PENDING_APPROVAL').execute()
        approval_count = len(approval_stuck.data)

        report.add_check(
            "DPO: Stuck in approval (approver JSMITH left)",
            56,
            approval_count,
            50 <= approval_count <= 65  # Allow some tolerance
        )

        # Issue #2: Variance holds (34 invoices)
        variance_hold = client.table('transactions').select('*').eq('component_type', 'DPO').eq('status', 'VARIANCE_HOLD').execute()
        variance_count = len(variance_hold.data)

        report.add_check(
            "DPO: Variance holds (price mismatches)",
            34,
            variance_count,
            30 <= variance_count <= 40  # Allow some tolerance
        )

        # Issue #3: Discount risks (23 invoices)
        discount_risk = client.table('transactions').select('*').eq('component_type', 'DPO').eq('status', 'DISCOUNT_AT_RISK').execute()
        discount_count = len(discount_risk.data)

        report.add_check(
            "DPO: Discount at risk (approaching 2/10 net 30 deadline)",
            23,
            discount_count,
            20 <= discount_count <= 30  # Allow some tolerance
        )

        # Issue #4: GR/IR mismatches (41 invoices)
        gr_ir = client.table('transactions').select('*').eq('component_type', 'DPO').eq('status', 'GR_IR_MISMATCH').execute()
        gr_ir_count = len(gr_ir.data)

        report.add_check(
            "DPO: GR/IR mismatches (waiting for 3-way match)",
            41,
            gr_ir_count,
            35 <= gr_ir_count <= 50  # Allow some tolerance
        )

    except Exception as e:
        report.add_info(f"❌ Error during DPO issue validation: {e}")


def validate_component_breakdown(client: Client, report: ValidationReport):
    """Validate component type breakdown"""
    report.add_section("Component Type Breakdown")

    try:
        # Count by component type
        dso_response = client.table('transactions').select('*', count='exact').eq('component_type', 'DSO').limit(1).execute()
        dio_response = client.table('transactions').select('*', count='exact').eq('component_type', 'DIO').limit(1).execute()
        dpo_response = client.table('transactions').select('*', count='exact').eq('component_type', 'DPO').limit(1).execute()

        dso_count = dso_response.count
        dio_count = dio_response.count
        dpo_count = dpo_response.count

        total = dso_count + dio_count + dpo_count

        report.add_info(f"DSO Transactions: {dso_count}")
        report.add_info(f"DIO Transactions: {dio_count}")
        report.add_info(f"DPO Transactions: {dpo_count}")
        report.add_info(f"Total Transactions: {total}")

        # Validate counts are in expected ranges
        report.add_check("DSO transaction count", 2500, dso_count, 2400 <= dso_count <= 2600)
        report.add_check("DIO transaction count", 800, dio_count, 750 <= dio_count <= 850)
        report.add_check("DPO transaction count", 1800, dpo_count, 1750 <= dpo_count <= 1850)

    except Exception as e:
        report.add_info(f"❌ Error during component breakdown validation: {e}")


def main():
    """Main validation function"""

    # Initialize client and report
    client = get_supabase_client()
    report = ValidationReport()

    report.add_header("SYNTHETIC SAP DATA VALIDATION REPORT")
    report.add_line(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run all validation checks
    validate_row_counts(client, report)
    validate_referential_integrity(client, report)
    validate_date_ranges(client, report)
    validate_component_breakdown(client, report)
    validate_dso_issues(client, report)
    validate_dio_issues(client, report)
    validate_dpo_issues(client, report)

    # Print summary
    report.print_summary()

    # Save report
    report.save(OUTPUT_FILE)

    # Print to console
    report.print_report()

    # Exit with appropriate code
    if report.checks_failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
