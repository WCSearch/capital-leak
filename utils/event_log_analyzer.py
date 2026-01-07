"""
Event Log Analysis Module - Phase 2 DSO Forensics

This module provides event-level forensics to identify TRUE root causes of cash delays,
moving beyond rule-based classification to actual system event analysis.

Key capabilities:
1. Sequence inversions (events in wrong order)
2. Workflow bottlenecks (stuck approvals, departed approvers)
3. System change correlation (config changes → issue spikes)
4. Abandoned processes (no activity for extended periods)
5. Root cause synthesis (definitive attribution with evidence)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


# Valid event sequences for different workflows
VALID_SEQUENCES = {
    'sales_order': [
        'ORDER_CREATED',
        'CREDIT_CHECK_PASSED',
        'SHIPPED',
        'BILLED',
        'PAYMENT_RECEIVED'
    ],
    'goods_receipt': [
        'GOODS_RECEIPT',
        'QUALITY_CHECK',
        'UNRESTRICTED',
        'GOODS_ISSUE'
    ],
    'purchase_order': [
        'PURCHASE_ORDER',
        'GOODS_RECEIPT',
        'INVOICE_RECEIPT',
        'PAYMENT_MADE'
    ]
}

# Inversion patterns and their business impact
INVERSION_PATTERNS = {
    'ship_before_credit_check': {
        'prerequisite': 'CREDIT_CHECK_PASSED',
        'dependent': 'SHIPPED',
        'severity': 'HIGH',
        'description': 'Goods shipped before credit approval'
    },
    'bill_before_ship': {
        'prerequisite': 'SHIPPED',
        'dependent': 'BILLED',
        'severity': 'MEDIUM',
        'description': 'Invoice created before delivery'
    },
    'payment_before_bill': {
        'prerequisite': 'BILLED',
        'dependent': 'PAYMENT_RECEIVED',
        'severity': 'HIGH',
        'description': 'Payment received with no invoice'
    }
}


def detect_sequence_inversions(transactions_df: pd.DataFrame, event_logs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect events that occurred in wrong order (temporal paradoxes).

    Valid sequences:
    - ORDER_CREATED → CREDIT_CHECK_PASSED → SHIPPED → BILLED → PAYMENT_RECEIVED
    - GOODS_RECEIPT → QUALITY_CHECK → UNRESTRICTED → GOODS_ISSUE
    - PURCHASE_ORDER → GOODS_RECEIPT → INVOICE_RECEIPT → PAYMENT_MADE

    Returns DataFrame with columns:
    - transaction_id
    - inversion_pattern (e.g., "ship_before_credit_check")
    - prerequisite_event (should have happened first)
    - dependent_event (happened too early)
    - time_gap_seconds (negative = inversion)
    - first_occurrence_date (when this pattern started appearing)
    - user_id (who triggered it)
    - module (which ERP module)
    - transaction_amount
    """

    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()

    inversions = []

    # Group events by transaction
    for txn_id in transactions_df['transaction_id'].unique():
        txn_events = event_logs_df[event_logs_df['transaction_id'] == txn_id].copy()

        if len(txn_events) == 0:
            continue

        # Get transaction amount
        txn_amount = transactions_df[transactions_df['transaction_id'] == txn_id]['amount'].iloc[0]

        # Ensure event_timestamp is datetime
        txn_events['event_timestamp'] = pd.to_datetime(txn_events['event_timestamp'])

        # Create event lookup by type
        event_lookup = {}
        for _, event in txn_events.iterrows():
            event_type = event['event_type']
            if event_type not in event_lookup:
                event_lookup[event_type] = event

        # Check for known inversion patterns
        for pattern_name, pattern_def in INVERSION_PATTERNS.items():
            prereq = pattern_def['prerequisite']
            dependent = pattern_def['dependent']

            # Check if both events exist
            if prereq in event_lookup and dependent in event_lookup:
                prereq_event = event_lookup[prereq]
                dependent_event = event_lookup[dependent]

                prereq_time = prereq_event['event_timestamp']
                dependent_time = dependent_event['event_timestamp']

                # Check if dependent happened BEFORE prerequisite (inversion!)
                if dependent_time < prereq_time:
                    time_gap_seconds = (prereq_time - dependent_time).total_seconds()

                    inversions.append({
                        'transaction_id': txn_id,
                        'inversion_pattern': pattern_name,
                        'prerequisite_event': prereq,
                        'dependent_event': dependent,
                        'time_gap_seconds': -time_gap_seconds,  # Negative to indicate inversion
                        'first_occurrence_date': dependent_time,
                        'user_id': dependent_event['user_id'],
                        'module': dependent_event['module'],
                        'transaction_amount': txn_amount,
                        'severity': pattern_def['severity'],
                        'description': pattern_def['description']
                    })

    if len(inversions) > 0:
        return pd.DataFrame(inversions)
    else:
        return pd.DataFrame()


def analyze_workflow_bottlenecks(transactions_df: pd.DataFrame, event_logs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Find transactions stuck in approval workflows.

    Detects:
    - Approvals pending >30 days with no activity
    - Approver left company (last event from user >90 days ago, workflow still assigned)
    - Workflow never reassigned after approver departure
    - Multiple timeout events

    Returns DataFrame with columns:
    - transaction_id
    - workflow_status (stuck/timeout/reassignment_needed)
    - assigned_approver_id
    - days_stuck
    - last_activity_date
    - approver_last_seen_date (from other transactions)
    - root_cause (e.g., "Approver left company, workflow not reassigned")
    - transaction_amount
    """

    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()

    bottlenecks = []
    now = datetime.now()

    # Identify all approvers and their last activity
    approver_activity = {}
    for _, event in event_logs_df.iterrows():
        user_id = event['user_id']
        event_time = pd.to_datetime(event['event_timestamp'])

        if user_id not in approver_activity or event_time > approver_activity[user_id]:
            approver_activity[user_id] = event_time

    # Group events by transaction
    for txn_id in transactions_df['transaction_id'].unique():
        txn_events = event_logs_df[event_logs_df['transaction_id'] == txn_id].copy()

        if len(txn_events) == 0:
            continue

        # Get transaction details
        txn_data = transactions_df[transactions_df['transaction_id'] == txn_id].iloc[0]
        txn_amount = txn_data['amount']

        # Ensure event_timestamp is datetime
        txn_events['event_timestamp'] = pd.to_datetime(txn_events['event_timestamp'])

        # Check for workflow-related events
        approval_events = txn_events[
            txn_events['event_type'].str.contains('APPROVAL|WORKFLOW', case=False, na=False)
        ]

        if len(approval_events) == 0:
            continue

        # Get last approval-related event
        last_approval = approval_events.sort_values('event_timestamp').iloc[-1]
        last_activity_date = last_approval['event_timestamp']
        days_stuck = (now - last_activity_date).days

        # Check if stuck for >30 days
        if days_stuck > 30:
            assigned_approver = last_approval['user_id']
            approver_last_seen = approver_activity.get(assigned_approver, last_activity_date)

            # Check if approver has left (no activity in 90 days)
            days_since_approver_active = (now - approver_last_seen).days

            if days_since_approver_active > 90:
                # Approver left company, workflow stuck
                bottlenecks.append({
                    'transaction_id': txn_id,
                    'workflow_status': 'reassignment_needed',
                    'assigned_approver_id': assigned_approver,
                    'days_stuck': days_stuck,
                    'last_activity_date': last_activity_date,
                    'approver_last_seen_date': approver_last_seen,
                    'root_cause': f'Approver {assigned_approver} left company, workflow not reassigned',
                    'transaction_amount': txn_amount
                })
            else:
                # Approval just stuck (approver still active)
                timeout_events = txn_events[
                    txn_events['event_type'].str.contains('TIMEOUT|EXPIRED', case=False, na=False)
                ]

                if len(timeout_events) > 0:
                    bottlenecks.append({
                        'transaction_id': txn_id,
                        'workflow_status': 'timeout',
                        'assigned_approver_id': assigned_approver,
                        'days_stuck': days_stuck,
                        'last_activity_date': last_activity_date,
                        'approver_last_seen_date': approver_last_seen,
                        'root_cause': f'Multiple timeouts, approver not responding',
                        'transaction_amount': txn_amount
                    })
                else:
                    bottlenecks.append({
                        'transaction_id': txn_id,
                        'workflow_status': 'stuck',
                        'assigned_approver_id': assigned_approver,
                        'days_stuck': days_stuck,
                        'last_activity_date': last_activity_date,
                        'approver_last_seen_date': approver_last_seen,
                        'root_cause': f'Approval pending >{days_stuck} days',
                        'transaction_amount': txn_amount
                    })

    if len(bottlenecks) > 0:
        return pd.DataFrame(bottlenecks)
    else:
        return pd.DataFrame()


def correlate_system_changes(transactions_df: pd.DataFrame, event_logs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Link transaction issues to system configuration changes.

    Detects:
    - Spike in specific issue type after SYSTEM_CONFIG_CHANGE event
    - Billing delays starting on specific date (billing trigger disabled)
    - Credit hold issues after credit policy update

    Returns DataFrame with columns:
    - change_date
    - change_type (billing_config/credit_policy/workflow_update)
    - change_description
    - transactions_affected_count
    - total_amount_trapped
    - issue_pattern (e.g., "fulfilled_not_invoiced")
    - evidence (list of transaction_ids showing pattern started after this date)
    """

    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()

    # Find all system config change events
    config_changes = event_logs_df[
        event_logs_df['event_type'] == 'SYSTEM_CONFIG_CHANGE'
    ].copy()

    if len(config_changes) == 0:
        return pd.DataFrame()

    correlations = []

    # Ensure timestamps are datetime
    config_changes['event_timestamp'] = pd.to_datetime(config_changes['event_timestamp'])
    transactions_df = transactions_df.copy()
    transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])

    # Group by change date and analyze impact
    for _, change_event in config_changes.iterrows():
        change_date = change_event['event_timestamp']
        change_description = change_event.get('event_description', 'Unknown change')

        # Determine change type from description
        change_type = 'unknown'
        if 'billing' in change_description.lower() or 'invoice' in change_description.lower():
            change_type = 'billing_config'
            issue_pattern = 'fulfilled_not_invoiced'
        elif 'credit' in change_description.lower():
            change_type = 'credit_policy'
            issue_pattern = 'credit_hold_lag'
        elif 'workflow' in change_description.lower() or 'approval' in change_description.lower():
            change_type = 'workflow_update'
            issue_pattern = 'workflow_bottleneck'
        else:
            change_type = 'other'
            issue_pattern = 'unknown'

        # Find transactions created after this change that have issues
        # Look for transactions in 30-day window after change
        window_end = change_date + timedelta(days=30)
        affected_txns = transactions_df[
            (transactions_df['transaction_date'] >= change_date) &
            (transactions_df['transaction_date'] <= window_end)
        ]

        # Filter to transactions with actual issues (high days outstanding)
        problematic_txns = affected_txns[affected_txns['days_outstanding'] > 15]

        if len(problematic_txns) > 0:
            correlations.append({
                'change_date': change_date,
                'change_type': change_type,
                'change_description': change_description,
                'transactions_affected_count': len(problematic_txns),
                'total_amount_trapped': problematic_txns['amount'].sum(),
                'issue_pattern': issue_pattern,
                'evidence': problematic_txns['transaction_id'].tolist()[:10]  # Sample of evidence
            })

    if len(correlations) > 0:
        return pd.DataFrame(correlations)
    else:
        return pd.DataFrame()


def identify_abandoned_processes(transactions_df: pd.DataFrame, event_logs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Find transactions with no activity for extended period.

    Detects:
    - No events for >90 days (abandoned)
    - Last event was error/rejection with no follow-up
    - Payment received but not applied (payment event exists, invoice still open)

    Returns DataFrame with columns:
    - transaction_id
    - last_event_date
    - days_since_last_activity
    - last_event_type
    - abandonment_reason (no_follow_up/error_unresolved/payment_unapplied)
    - transaction_amount
    """

    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()

    abandoned = []
    now = datetime.now()

    # Group events by transaction
    for txn_id in transactions_df['transaction_id'].unique():
        txn_events = event_logs_df[event_logs_df['transaction_id'] == txn_id].copy()

        if len(txn_events) == 0:
            # No events at all - truly abandoned
            txn_data = transactions_df[transactions_df['transaction_id'] == txn_id].iloc[0]
            txn_date = pd.to_datetime(txn_data['transaction_date'])
            days_since_creation = (now - txn_date).days

            if days_since_creation > 90:
                abandoned.append({
                    'transaction_id': txn_id,
                    'last_event_date': txn_date,
                    'days_since_last_activity': days_since_creation,
                    'last_event_type': 'NONE',
                    'abandonment_reason': 'no_follow_up',
                    'transaction_amount': txn_data['amount']
                })
            continue

        # Get transaction details
        txn_data = transactions_df[transactions_df['transaction_id'] == txn_id].iloc[0]
        txn_amount = txn_data['amount']
        txn_status = txn_data.get('status', '')

        # Ensure event_timestamp is datetime
        txn_events['event_timestamp'] = pd.to_datetime(txn_events['event_timestamp'])

        # Get last event
        last_event = txn_events.sort_values('event_timestamp').iloc[-1]
        last_event_date = last_event['event_timestamp']
        last_event_type = last_event['event_type']
        days_since_last = (now - last_event_date).days

        # Check for abandonment scenarios
        if days_since_last > 90:
            # Check if last event was error/rejection
            if 'ERROR' in last_event_type or 'REJECT' in last_event_type or 'FAIL' in last_event_type:
                abandoned.append({
                    'transaction_id': txn_id,
                    'last_event_date': last_event_date,
                    'days_since_last_activity': days_since_last,
                    'last_event_type': last_event_type,
                    'abandonment_reason': 'error_unresolved',
                    'transaction_amount': txn_amount
                })
            else:
                abandoned.append({
                    'transaction_id': txn_id,
                    'last_event_date': last_event_date,
                    'days_since_last_activity': days_since_last,
                    'last_event_type': last_event_type,
                    'abandonment_reason': 'no_follow_up',
                    'transaction_amount': txn_amount
                })

        # Check for payment received but not applied
        payment_events = txn_events[txn_events['event_type'] == 'PAYMENT_RECEIVED']
        if len(payment_events) > 0 and txn_status not in ['CLEARED', 'PAID']:
            payment_date = payment_events.iloc[-1]['event_timestamp']
            days_since_payment = (now - payment_date).days

            if days_since_payment > 5:
                abandoned.append({
                    'transaction_id': txn_id,
                    'last_event_date': payment_date,
                    'days_since_last_activity': days_since_payment,
                    'last_event_type': 'PAYMENT_RECEIVED',
                    'abandonment_reason': 'payment_unapplied',
                    'transaction_amount': txn_amount
                })

    if len(abandoned) > 0:
        return pd.DataFrame(abandoned)
    else:
        return pd.DataFrame()


def synthesize_root_causes(transactions_df: pd.DataFrame, event_logs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run all analyses and assign definitive root cause to each transaction.

    Priority order (first match wins):
    1. Sequence inversion (systemic issue)
    2. Workflow bottleneck (approval stuck)
    3. System change correlation (configuration issue)
    4. Abandoned process (process failure)
    5. Rule-based classification (if no event log evidence)

    Returns DataFrame with columns:
    - transaction_id
    - root_cause_type (fulfilled_not_invoiced/credit_hold_lag/etc.)
    - root_cause_confidence (HIGH/MEDIUM/LOW based on evidence quality)
    - evidence_source (event_log_pattern/system_change/rule_based)
    - evidence_detail (specific finding, e.g., "Billing trigger disabled 2024-03-17")
    - fix_type (system/policy/process/behavioral)
    - fix_owner (IT/Finance/AR Team/etc.)
    - fix_days_estimate
    - recovery_confidence (CERTAIN/PROBABLE/CONTESTED)

    Also includes all fields from original transaction.
    """

    # Import the rule-based classifier for fallback
    from utils.root_cause_classifier import classify_root_causes

    # Initialize result with all transactions
    result_df = transactions_df.copy()

    # Add default columns
    result_df['root_cause_type'] = 'unknown'
    result_df['root_cause_confidence'] = 'LOW'
    result_df['evidence_source'] = 'rule_based'
    result_df['evidence_detail'] = ''
    result_df['fix_type'] = 'manual_review'
    result_df['fix_owner'] = 'Finance'
    result_df['fix_days_estimate'] = None
    result_df['recovery_confidence'] = 'CONTESTED'

    if event_logs_df is None or len(event_logs_df) == 0:
        # No event logs - use rule-based classification
        return classify_root_causes(transactions_df)

    # Run all forensic analyses
    inversions_df = detect_sequence_inversions(transactions_df, event_logs_df)
    bottlenecks_df = analyze_workflow_bottlenecks(transactions_df, event_logs_df)
    system_changes_df = correlate_system_changes(transactions_df, event_logs_df)
    abandoned_df = identify_abandoned_processes(transactions_df, event_logs_df)

    # PRIORITY 1: Sequence inversions (highest confidence)
    if len(inversions_df) > 0:
        for _, inversion in inversions_df.iterrows():
            txn_id = inversion['transaction_id']
            mask = result_df['transaction_id'] == txn_id

            result_df.loc[mask, 'root_cause_type'] = 'sequence_inversion'
            result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
            result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
            result_df.loc[mask, 'evidence_detail'] = f"{inversion['description']} ({inversion['inversion_pattern']})"
            result_df.loc[mask, 'fix_type'] = 'system'
            result_df.loc[mask, 'fix_owner'] = 'IT'
            result_df.loc[mask, 'fix_days_estimate'] = 5
            result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'

    # PRIORITY 2: Workflow bottlenecks
    if len(bottlenecks_df) > 0:
        for _, bottleneck in bottlenecks_df.iterrows():
            txn_id = bottleneck['transaction_id']
            mask = result_df['transaction_id'] == txn_id

            # Only assign if not already assigned higher priority
            if result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                result_df.loc[mask, 'root_cause_type'] = 'workflow_bottleneck'
                result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = bottleneck['root_cause']
                result_df.loc[mask, 'fix_type'] = 'policy'
                result_df.loc[mask, 'fix_owner'] = 'Finance'
                result_df.loc[mask, 'fix_days_estimate'] = 2
                result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'

    # PRIORITY 3: System changes
    if len(system_changes_df) > 0:
        for _, change in system_changes_df.iterrows():
            affected_txn_ids = change['evidence']

            for txn_id in affected_txn_ids:
                mask = result_df['transaction_id'] == txn_id

                if len(result_df[mask]) == 0:
                    continue

                # Only assign if not already assigned higher priority
                if result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                    change_date_str = pd.to_datetime(change['change_date']).strftime('%Y-%m-%d')

                    result_df.loc[mask, 'root_cause_type'] = change['issue_pattern']
                    result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
                    result_df.loc[mask, 'evidence_source'] = 'system_change'
                    result_df.loc[mask, 'evidence_detail'] = f"{change['change_description']} (System change {change_date_str})"
                    result_df.loc[mask, 'fix_type'] = 'system'
                    result_df.loc[mask, 'fix_owner'] = 'IT'
                    result_df.loc[mask, 'fix_days_estimate'] = 5
                    result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'

    # PRIORITY 4: Abandoned processes
    if len(abandoned_df) > 0:
        for _, abandoned in abandoned_df.iterrows():
            txn_id = abandoned['transaction_id']
            mask = result_df['transaction_id'] == txn_id

            # Only assign if not already assigned higher priority
            if result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                abandonment_type = abandoned['abandonment_reason']

                if abandonment_type == 'payment_unapplied':
                    root_cause = 'paid_unapplied_cash'
                    fix_type = 'process'
                    fix_owner = 'AR Team'
                    fix_days = 3
                    confidence = 'CERTAIN'
                elif abandonment_type == 'error_unresolved':
                    root_cause = 'error_unresolved'
                    fix_type = 'process'
                    fix_owner = 'IT'
                    fix_days = 10
                    confidence = 'PROBABLE'
                else:
                    root_cause = 'abandoned_process'
                    fix_type = 'process'
                    fix_owner = 'AR Team'
                    fix_days = 15
                    confidence = 'PROBABLE'

                result_df.loc[mask, 'root_cause_type'] = root_cause
                result_df.loc[mask, 'root_cause_confidence'] = 'MEDIUM'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = f"No activity for {abandoned['days_since_last_activity']} days (last: {abandoned['last_event_type']})"
                result_df.loc[mask, 'fix_type'] = fix_type
                result_df.loc[mask, 'fix_owner'] = fix_owner
                result_df.loc[mask, 'fix_days_estimate'] = fix_days
                result_df.loc[mask, 'recovery_confidence'] = confidence

    # PRIORITY 5: Rule-based fallback for remaining transactions
    unclassified_mask = result_df['root_cause_confidence'] == 'LOW'
    if unclassified_mask.sum() > 0:
        unclassified_txns = result_df[unclassified_mask]
        rule_based_results = classify_root_causes(unclassified_txns)

        # Merge rule-based results back
        for col in ['root_cause_type', 'root_cause_confidence', 'evidence_source',
                    'evidence_detail', 'fix_type', 'fix_owner', 'fix_days_estimate', 'recovery_confidence']:
            result_df.loc[unclassified_mask, col] = rule_based_results[col].values

    return result_df
