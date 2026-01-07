"""
Test DSO Time-State Classification

Generates realistic Acme Industrial Supply data and tests the time-state classification logic.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import uuid
import pandas as pd
from utils.dso_analysis import (
    classify_dso_time_state,
    analyze_dso_time_states,
    get_time_state_summary,
    analyze_recovery_confidence,
    analyze_root_causes,
    generate_execution_queue,
    format_currency
)


def generate_test_transactions():
    """
    Generate realistic DSO transaction data for Acme Industrial Supply.

    Expected distribution (from requirements):
    - Fulfilled not invoiced: ~$1.2M (143 transactions)
    - Credit holds: ~$760K (31 transactions)
    - Pricing disputes: ~$890K (62 transactions)
    - Payment term exceptions: ~$620K (47 transactions)
    - Invoiced not sent: ~$300K (47 transactions)
    - Late payers: ~$1.3M (187 transactions)
    Total: ~$5.3M
    """

    transactions = []
    event_logs = []
    base_date = datetime.now()

    # Helper function to create transaction
    def create_transaction(state_type, amount, days_old, status='OPEN', metadata=None):
        txn_id = str(uuid.uuid4())
        txn_date = base_date - timedelta(days=days_old)

        txn = {
            'transaction_id': txn_id,
            'company_id': str(uuid.uuid4()),
            'component_type': 'DSO',
            'transaction_number': f'INV-{len(transactions)+10001}',
            'transaction_date': txn_date.date().isoformat() if state_type != 'fulfilled_not_invoiced' else None,
            'due_date': (txn_date + timedelta(days=30)).date().isoformat(),
            'amount': amount,
            'outstanding_amount': amount,
            'days_outstanding': days_old,
            'gl_account': '1200',
            'customer_vendor': f'Customer-{len(transactions)+1}',
            'status': status,
            'erp_metadata': metadata or {}
        }

        return txn, txn_id

    # 1. FULFILLED NOT INVOICED: $1.2M, 143 transactions, avg 18.4 days
    print("Generating fulfilled_not_invoiced transactions...")
    for i in range(143):
        amount = 1_200_000 / 143
        days_old = 10 + (i % 25)  # Range 10-35 days, avg ~18
        metadata = {
            'delivery_date': (base_date - timedelta(days=days_old)).date().isoformat(),
            'payment_terms_days': 30
        }
        txn, txn_id = create_transaction('fulfilled_not_invoiced', amount, days_old,
                                         status='PENDING', metadata=metadata)
        transactions.append(txn)

    # 2. CREDIT HOLDS: $760K, 31 transactions, avg 35.7 days
    print("Generating credit_hold transactions...")
    for i in range(31):
        amount = 760_000 / 31
        days_old = 31 + (i % 10)  # Range 31-41 days, avg ~36
        metadata = {
            'credit_hold': True,
            'payment_terms_days': 30
        }
        txn, txn_id = create_transaction('credit_hold', amount, days_old,
                                         status='CREDIT_HOLD', metadata=metadata)
        transactions.append(txn)

        # No credit review events (this is what makes it stuck)

    # 3. PAID BUT UNAPPLIED: $400K, 31 payments, avg 12.1 days
    print("Generating paid_unapplied transactions...")
    for i in range(31):
        amount = 400_000 / 31
        days_old = 8 + (i % 8)  # Range 8-16 days, avg ~12
        metadata = {'payment_terms_days': 30}
        txn, txn_id = create_transaction('paid_unapplied', amount, days_old,
                                         status='OPEN', metadata=metadata)
        transactions.append(txn)

        # Add payment received event (ensure payment is >5 days old)
        payment_days_ago = max(6, days_old - 2)  # At least 6 days to trigger paid_unapplied
        event_logs.append({
            'event_id': str(uuid.uuid4()),
            'company_id': txn['company_id'],
            'transaction_id': txn_id,
            'event_type': 'PAYMENT_RECEIVED',
            'event_timestamp': (base_date - timedelta(days=payment_days_ago)).isoformat(),
            'user_id': 'SYSTEM',
            'event_description': 'Payment received but not applied',
            'module': 'AR',
            'event_data': {'amount': amount}
        })

    # 4. INVOICED NOT SENT: $300K, 47 invoices, avg 8.2 days
    print("Generating invoiced_not_sent transactions...")
    for i in range(47):
        amount = 300_000 / 47
        days_old = 4 + (i % 10)  # Range 4-14 days, avg ~8
        metadata = {'payment_terms_days': 30}
        txn, txn_id = create_transaction('invoiced_not_sent', amount, days_old,
                                         status='CREATED', metadata=metadata)
        transactions.append(txn)

    # 5. SENT BUT DISPUTED (Pricing/Data Errors): $890K, 62 invoices, avg 22.1 days
    print("Generating sent_disputed transactions...")
    dispute_reasons = ['pricing_error', 'quantity_mismatch', 'billing_error']
    for i in range(62):
        amount = 890_000 / 62
        days_old = 15 + (i % 15)  # Range 15-30 days, avg ~22
        metadata = {
            'payment_terms_days': 30,
            'dispute_reason': dispute_reasons[i % len(dispute_reasons)]
        }
        txn, txn_id = create_transaction('sent_disputed', amount, days_old,
                                         status='DISPUTED', metadata=metadata)
        transactions.append(txn)

    # 6. UNDISPUTED BUT UNPAID (Late Payers): $1.9M, 187 invoices, avg 41.2 days
    print("Generating undisputed_unpaid transactions...")
    for i in range(187):
        amount = 1_900_000 / 187
        days_old = 38 + (i % 20)  # Range 38-58 days (all past due), avg ~48
        metadata = {'payment_terms_days': 30}
        txn, txn_id = create_transaction('undisputed_unpaid', amount, days_old,
                                         status='SENT', metadata=metadata)
        transactions.append(txn)

    print(f"\nGenerated {len(transactions)} transactions")
    print(f"Generated {len(event_logs)} event logs")

    return pd.DataFrame(transactions), pd.DataFrame(event_logs)


def test_classification():
    """Test the DSO time-state classification logic."""

    print("\n" + "="*80)
    print("DSO TIME-STATE CLASSIFICATION TEST")
    print("="*80 + "\n")

    # Generate test data
    transactions_df, event_logs_df = generate_test_transactions()

    print("\n" + "-"*80)
    print("ANALYZING TIME STATES")
    print("-"*80 + "\n")

    # Analyze time states
    time_state_groups = analyze_dso_time_states(transactions_df, event_logs_df)

    # Get summary
    time_state_summary = get_time_state_summary(time_state_groups)

    # Print results by priority
    print("🔴 CRITICAL (System/Process Fixes - No Customer Action Needed)")
    print("-"*80)
    for state in time_state_summary:
        if state['priority'] == 'CRITICAL':
            print(f"\n{state['name']}")
            print(f"  Amount: {format_currency(state['total_amount'])} | " +
                  f"Count: {state['count']} | " +
                  f"Avg: {state['avg_days']:.1f} days")
            print(f"  Fix: {state['fix_action']} | Timeline: {state['timeline']}")

    print("\n🟡 MEDIUM (Process/Policy Fixes - Some Coordination Required)")
    print("-"*80)
    for state in time_state_summary:
        if state['priority'] == 'MEDIUM':
            print(f"\n{state['name']}")
            print(f"  Amount: {format_currency(state['total_amount'])} | " +
                  f"Count: {state['count']} | " +
                  f"Avg: {state['avg_days']:.1f} days")
            print(f"  Fix: {state['fix_action']} | Timeline: {state['timeline']}")

    print("\n🟢 LOW PRIORITY (Behavioral - Requires Customer Action)")
    print("-"*80)
    for state in time_state_summary:
        if state['priority'] == 'LOW':
            print(f"\n{state['name']}")
            print(f"  Amount: {format_currency(state['total_amount'])} | " +
                  f"Count: {state['count']} | " +
                  f"Avg: {state['avg_days']:.1f} days")
            print(f"  Fix: {state['fix_action']} | Timeline: {state['timeline']}")

    # Calculate totals
    total_amount = sum(s['total_amount'] for s in time_state_summary)
    total_count = sum(s['count'] for s in time_state_summary)

    print("\n" + "="*80)
    print(f"TOTAL EXCESS: {format_currency(total_amount)} across {total_count} transactions")
    print("="*80)

    # Verify against expected distribution
    print("\n" + "-"*80)
    print("VERIFICATION AGAINST EXPECTED DISTRIBUTION")
    print("-"*80 + "\n")

    expected = {
        'fulfilled_not_invoiced': {'amount': 1_200_000, 'count': 143},
        'credit_hold': {'amount': 760_000, 'count': 31},
        'paid_unapplied': {'amount': 400_000, 'count': 31},
        'invoiced_not_sent': {'amount': 300_000, 'count': 47},
        'sent_disputed': {'amount': 890_000, 'count': 62},
        'undisputed_unpaid': {'amount': 1_900_000, 'count': 187}
    }

    for state_key, exp in expected.items():
        actual_group = time_state_groups.get(state_key, {})
        actual_amount = actual_group.get('total_amount', 0)
        actual_count = actual_group.get('count', 0)

        amount_match = abs(actual_amount - exp['amount']) < 1000
        count_match = actual_count == exp['count']

        status = "✓" if (amount_match and count_match) else "✗"

        print(f"{status} {state_key}:")
        print(f"    Expected: {format_currency(exp['amount'])} ({exp['count']} txns)")
        print(f"    Actual:   {format_currency(actual_amount)} ({actual_count} txns)")

    # Test Phase 2: Recovery Confidence
    print("\n" + "="*80)
    print("PHASE 2: RECOVERY CONFIDENCE ANALYSIS")
    print("="*80 + "\n")

    confidence_groups = analyze_recovery_confidence(time_state_groups)

    print(f"🟢 CERTAIN: {format_currency(confidence_groups['CERTAIN']['total_amount'])} ({confidence_groups['CERTAIN']['percentage']:.0f}%)")
    print(f"   Recoverable without customer involvement")
    print(f"   Expected timeline: {confidence_groups['CERTAIN']['expected_timeline']}")
    for state in confidence_groups['CERTAIN']['states']:
        print(f"   - {state['state_name']}: {format_currency(state['amount'])}")

    print(f"\n🟡 PROBABLE: {format_currency(confidence_groups['PROBABLE']['total_amount'])} ({confidence_groups['PROBABLE']['percentage']:.0f}%)")
    print(f"   Clear fix path, requires coordination")
    print(f"   Expected timeline: {confidence_groups['PROBABLE']['expected_timeline']}")
    for state in confidence_groups['PROBABLE']['states']:
        print(f"   - {state['state_name']}: {format_currency(state['amount'])}")

    print(f"\n🔴 CONTESTED: {format_currency(confidence_groups['CONTESTED']['total_amount'])} ({confidence_groups['CONTESTED']['percentage']:.0f}%)")
    print(f"   Requires customer action/negotiation")
    print(f"   Expected timeline: {confidence_groups['CONTESTED']['expected_timeline']}")
    for state in confidence_groups['CONTESTED']['states']:
        print(f"   - {state['state_name']}: {format_currency(state['amount'])}")

    actionable = confidence_groups['CERTAIN']['total_amount'] + confidence_groups['PROBABLE']['total_amount']
    total_conf = sum(g['total_amount'] for g in confidence_groups.values())
    actionable_pct = (actionable / total_conf * 100) if total_conf > 0 else 0
    print(f"\n💰 ACTIONABLE RECOVERY: {format_currency(actionable)} (Certain + Probable = {actionable_pct:.0f}%)")

    # Test Phase 3: Root Cause Analysis
    print("\n" + "="*80)
    print("PHASE 3: ROOT CAUSE HEATMAP")
    print("="*80 + "\n")

    root_cause_list = analyze_root_causes(transactions_df, event_logs_df)

    print(f"{'Root Cause':<30} {'Count':>8} {'Avg Days':>10} {'$ Impact':>12} {'Owner':<12} {'Timeline':>10}")
    print("-"*95)
    for rc in root_cause_list:
        timeline = f"{rc['fix_days']}d" if rc['fix_days'] else 'TBD'
        print(f"{rc['name']:<30} {rc['count']:>8} {rc['avg_days']:>10.1f} {format_currency(rc['total_amount']):>12} {rc['owner']:<12} {timeline:>10}")

    print(f"\n🎯 SURGICAL TARGET: {root_cause_list[0]['name']}")
    print(f"   {root_cause_list[0]['count']} transactions | {format_currency(root_cause_list[0]['total_amount'])} impact | {root_cause_list[0]['fix_days']}-day fix")
    print(f"   ACTION: {root_cause_list[0]['action']}")
    print(f"   OWNER: {root_cause_list[0]['owner']}")

    # Test Phase 4: Execution Queue
    print("\n" + "="*80)
    print("PHASE 4: RECOVERY EXECUTION QUEUE")
    print("="*80)
    print("Sorted by: $ recovered per day per hour of effort\n")

    execution_queue = generate_execution_queue(root_cause_list)

    print(f"{'Rank':<6} {'Root Cause':<30} {'$ Impact':>12} {'Days':>6} {'Effort':>8} {'$/Day/Hr':>12} {'Owner':<12}")
    print("-"*100)
    for item in execution_queue:
        days = f"{item['fix_days']}d" if item['fix_days'] else 'TBD'
        effort = f"{item['effort_hours']}h"
        efficiency = format_currency(item['efficiency'])
        print(f"#{item['rank']:<5} {item['root_cause_name']:<30} {format_currency(item['total_impact']):>12} {days:>6} {effort:>8} {efficiency:>12} {item['owner']:<12}")

    print(f"\n🎯 NEXT ACTION: Fix #{execution_queue[0]['rank']} - {execution_queue[0]['root_cause_name']}")
    print(f"   Expected Recovery: {format_currency(execution_queue[0]['total_impact'])} in {execution_queue[0]['fix_days']} days")
    print(f"   Required Effort: {execution_queue[0]['effort_hours']} hours")
    print(f"   Owner: {execution_queue[0]['owner']}")
    print(f"   Efficiency: {format_currency(execution_queue[0]['efficiency'])} per day/hour")

    print("\n" + "="*80)
    print("ALL PHASES TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == '__main__':
    test_classification()
