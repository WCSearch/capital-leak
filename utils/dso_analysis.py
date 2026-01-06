"""
DSO Time-State Analysis Module

Transforms DSO from a single metric into a diagnostic tool that identifies:
1. WHERE invoice time is accumulating (time states)
2. WHICH dollars are actually recoverable (confidence levels)
3. WHAT to fix first (efficiency-ranked by $/day/hour)
4. HOW to fix it (specific action + owner)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd


# Time-state definitions with metadata
TIME_STATE_CONFIG = {
    'fulfilled_not_invoiced': {
        'name': 'Fulfilled but Not Invoiced',
        'priority': 'CRITICAL',
        'color': 'red',
        'fix_action': 'Trigger invoice batch',
        'timeline': '3-5 days',
        'order': 1
    },
    'credit_hold': {
        'name': 'Credit Holds (Auto-Applied, Never Cleared)',
        'priority': 'CRITICAL',
        'color': 'red',
        'fix_action': 'Reset credit limits',
        'timeline': '1-2 days',
        'order': 2
    },
    'paid_unapplied': {
        'name': 'Paid but Unapplied',
        'priority': 'CRITICAL',
        'color': 'red',
        'fix_action': 'Manual cash application',
        'timeline': '3-5 days',
        'order': 3
    },
    'invoiced_not_sent': {
        'name': 'Invoiced but Not Sent',
        'priority': 'MEDIUM',
        'color': 'amber',
        'fix_action': 'Release invoices',
        'timeline': '1 day',
        'order': 4
    },
    'sent_disputed': {
        'name': 'Sent but Disputed (Pricing/Data Errors)',
        'priority': 'MEDIUM',
        'color': 'amber',
        'fix_action': 'Correct and reissue',
        'timeline': '7-10 days',
        'order': 5
    },
    'undisputed_unpaid': {
        'name': 'Undisputed but Unpaid (Late Payers)',
        'priority': 'LOW',
        'color': 'green',
        'fix_action': 'Collections effort',
        'timeline': '30-60 days',
        'order': 6
    }
}


def days_between(date1, date2) -> int:
    """Calculate days between two dates."""
    if isinstance(date1, str):
        date1 = datetime.fromisoformat(date1.replace('Z', '+00:00'))
    if isinstance(date2, str):
        date2 = datetime.fromisoformat(date2.replace('Z', '+00:00'))

    if isinstance(date1, datetime) and isinstance(date2, datetime):
        return abs((date2 - date1).days)
    return 0


def classify_dso_time_state(transaction: Dict, event_logs: List[Dict]) -> str:
    """
    Classify a DSO transaction into one of 6 mutually exclusive time states.

    Args:
        transaction: Transaction record with fields:
            - transaction_id
            - transaction_date
            - due_date
            - outstanding_amount
            - days_outstanding
            - status (OPEN, CREATED, PENDING_SEND, SENT, DISPUTED, CLEARED)
            - erp_metadata (JSONB with delivery_date, payment_terms_days, credit_hold, dispute_reason)
        event_logs: List of event log records for this transaction

    Returns:
        Time state key (e.g., 'fulfilled_not_invoiced', 'credit_hold', etc.)
    """

    # Get metadata
    metadata = transaction.get('erp_metadata') or {}
    status = transaction.get('status', '').upper()
    days_outstanding = transaction.get('days_outstanding', 0)

    # Check if payment received but not applied
    payment_event = next(
        (e for e in event_logs if e.get('event_type') == 'PAYMENT_RECEIVED'
         and e.get('transaction_id') == transaction.get('transaction_id')),
        None
    )

    if payment_event and status != 'CLEARED':
        event_timestamp = payment_event.get('event_timestamp')
        if event_timestamp:
            days_since_payment = days_between(event_timestamp, datetime.now())
            if days_since_payment > 5:
                return 'paid_unapplied'

    # Check if disputed
    if status == 'DISPUTED':
        return 'sent_disputed'

    # Check if invoiced but not sent
    if status in ['CREATED', 'PENDING_SEND']:
        transaction_date = transaction.get('transaction_date')
        if transaction_date:
            days_since_creation = days_between(transaction_date, datetime.now())
            if days_since_creation > 3:
                return 'invoiced_not_sent'

    # Check if fulfilled but not invoiced
    delivery_date = metadata.get('delivery_date')
    transaction_date = transaction.get('transaction_date')

    if delivery_date and not transaction_date:
        days_since_delivery = days_between(delivery_date, datetime.now())
        if days_since_delivery > 7:
            return 'fulfilled_not_invoiced'

    # Check if credit hold
    credit_hold = metadata.get('credit_hold', False)
    if credit_hold and days_outstanding > 30:
        # Check if there have been any credit reviews
        credit_review_events = [
            e for e in event_logs
            if e.get('event_type') == 'CREDIT_REVIEW'
            and e.get('transaction_id') == transaction.get('transaction_id')
        ]
        if len(credit_review_events) == 0:
            return 'credit_hold'

    # Check if past due (undisputed but unpaid)
    payment_terms_days = metadata.get('payment_terms_days', 30)
    grace_period = 7

    if days_outstanding > (payment_terms_days + grace_period):
        return 'undisputed_unpaid'

    # Default: normal (not excess time)
    return 'normal'


def analyze_dso_time_states(
    transactions_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> Dict:
    """
    Analyze all DSO transactions and group by time state.

    Args:
        transactions_df: DataFrame of DSO transactions
        event_logs_df: DataFrame of event logs

    Returns:
        Dictionary with time state breakdown:
        {
            'fulfilled_not_invoiced': {
                'transactions': [...],
                'total_amount': 1200000,
                'count': 143,
                'avg_days': 18.4,
                'config': {...}
            },
            ...
        }
    """

    # Convert DataFrames to list of dicts for processing
    transactions = transactions_df.to_dict('records')
    event_logs = event_logs_df.to_dict('records')

    # Group time states
    time_state_groups = {
        key: {
            'transactions': [],
            'total_amount': 0,
            'count': 0,
            'avg_days': 0,
            'config': config
        }
        for key, config in TIME_STATE_CONFIG.items()
    }

    # Also track normal transactions
    time_state_groups['normal'] = {
        'transactions': [],
        'total_amount': 0,
        'count': 0,
        'avg_days': 0,
        'config': {
            'name': 'Normal',
            'priority': 'NORMAL',
            'color': 'gray',
            'fix_action': 'None',
            'timeline': 'N/A',
            'order': 7
        }
    }

    # Classify each transaction
    for txn in transactions:
        time_state = classify_dso_time_state(txn, event_logs)

        if time_state in time_state_groups:
            time_state_groups[time_state]['transactions'].append(txn)
            time_state_groups[time_state]['total_amount'] += txn.get('outstanding_amount', 0) or 0
            time_state_groups[time_state]['count'] += 1

    # Calculate average days for each group
    for state_key, group in time_state_groups.items():
        if group['count'] > 0:
            total_days = sum(t.get('days_outstanding', 0) or 0 for t in group['transactions'])
            group['avg_days'] = total_days / group['count']

    return time_state_groups


def get_time_state_summary(time_state_groups: Dict) -> List[Dict]:
    """
    Get a summary of time states for dashboard display.

    Returns list sorted by priority (critical first).
    """

    summary = []

    for state_key, group in time_state_groups.items():
        if state_key == 'normal':
            continue

        if group['count'] > 0:
            summary.append({
                'state_key': state_key,
                'name': group['config']['name'],
                'priority': group['config']['priority'],
                'color': group['config']['color'],
                'total_amount': group['total_amount'],
                'count': group['count'],
                'avg_days': group['avg_days'],
                'fix_action': group['config']['fix_action'],
                'timeline': group['config']['timeline'],
                'order': group['config']['order']
            })

    # Sort by order (critical first)
    summary.sort(key=lambda x: x['order'])

    return summary


def format_currency(amount: float) -> str:
    """Format amount as USD currency."""
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.1f}K"
    else:
        return f"${amount:.0f}"


def get_priority_emoji(priority: str) -> str:
    """Get emoji for priority level."""
    return {
        'CRITICAL': '🔴',
        'MEDIUM': '🟡',
        'LOW': '🟢',
        'NORMAL': '⚪'
    }.get(priority, '⚪')
