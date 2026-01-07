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


# ============================================================================
# PHASE 2: RECOVERY CONFIDENCE SCORING
# ============================================================================

def calculate_recovery_confidence(transaction: Dict, time_state: str) -> Dict:
    """
    Calculate recovery confidence level for a transaction.

    Returns:
        Dictionary with:
        - confidence: 'CERTAIN', 'PROBABLE', or 'CONTESTED'
        - days: Expected days to recover
        - reason: Explanation of confidence level
    """

    metadata = transaction.get('erp_metadata') or {}
    days_outstanding = transaction.get('days_outstanding', 0)

    # CERTAIN: System/process fix, no customer action needed
    if time_state == 'fulfilled_not_invoiced':
        return {
            'confidence': 'CERTAIN',
            'days': 5,
            'reason': 'Trigger invoice batch'
        }

    if time_state == 'paid_unapplied':
        return {
            'confidence': 'CERTAIN',
            'days': 3,
            'reason': 'Manual cash application'
        }

    if time_state == 'credit_hold' and days_outstanding > 30:
        return {
            'confidence': 'CERTAIN',
            'days': 2,
            'reason': 'Reset credit limit'
        }

    # PROBABLE: Fixable with clear action, some coordination
    if time_state == 'invoiced_not_sent':
        return {
            'confidence': 'PROBABLE',
            'days': 1,
            'reason': 'Release invoice'
        }

    if time_state == 'sent_disputed':
        dispute_reason = metadata.get('dispute_reason')
        if dispute_reason in ['pricing_error', 'quantity_mismatch', 'billing_error']:
            return {
                'confidence': 'PROBABLE',
                'days': 10,
                'reason': 'Correct and reissue'
            }
        else:
            return {
                'confidence': 'CONTESTED',
                'days': 45,
                'reason': 'Negotiation required'
            }

    # Check payment terms exceptions
    payment_terms = metadata.get('payment_terms_days', 30)
    if payment_terms > 60 and days_outstanding < payment_terms:
        return {
            'confidence': 'PROBABLE',
            'days': 15,
            'reason': 'Enforce credit policy'
        }

    # CONTESTED: Behavioral, requires customer action
    if time_state == 'undisputed_unpaid' and days_outstanding > 90:
        return {
            'confidence': 'CONTESTED',
            'days': 60,
            'reason': 'Collections effort'
        }

    # Default for undisputed_unpaid
    if time_state == 'undisputed_unpaid':
        return {
            'confidence': 'CONTESTED',
            'days': 30,
            'reason': 'Collections effort'
        }

    # Fallback
    return {
        'confidence': 'CONTESTED',
        'days': 30,
        'reason': 'Manual review required'
    }


def analyze_recovery_confidence(time_state_groups: Dict) -> Dict:
    """
    Analyze recovery confidence across all time states.

    Args:
        time_state_groups: Output from analyze_dso_time_states()

    Returns:
        Dictionary with confidence breakdown:
        {
            'certain': {
                'total_amount': float,
                'percentage': float,
                'states': [...],
                'expected_timeline': str
            },
            'probable': {...},
            'contested': {...}
        }
    """

    confidence_groups = {
        'CERTAIN': {
            'total_amount': 0,
            'percentage': 0,
            'states': [],
            'expected_timeline': '2-5 days + customer payment cycle'
        },
        'PROBABLE': {
            'total_amount': 0,
            'percentage': 0,
            'states': [],
            'expected_timeline': '7-15 days + customer payment cycle'
        },
        'CONTESTED': {
            'total_amount': 0,
            'percentage': 0,
            'states': [],
            'expected_timeline': '30-60 days'
        }
    }

    # Calculate confidence for each transaction in each time state
    for state_key, group in time_state_groups.items():
        if state_key == 'normal':
            continue

        for txn in group['transactions']:
            confidence_data = calculate_recovery_confidence(txn, state_key)
            confidence_level = confidence_data['confidence']

            if confidence_level in confidence_groups:
                confidence_groups[confidence_level]['total_amount'] += txn.get('outstanding_amount', 0) or 0

    # Calculate totals and percentages
    total_amount = sum(g['total_amount'] for g in confidence_groups.values())

    if total_amount > 0:
        for level, data in confidence_groups.items():
            data['percentage'] = (data['total_amount'] / total_amount) * 100

    # Add state-level details
    for state_key, group in time_state_groups.items():
        if state_key == 'normal' or group['count'] == 0:
            continue

        # Determine dominant confidence for this state
        state_amount = group['total_amount']
        state_name = group['config']['name']

        # Use first transaction as representative
        if group['transactions']:
            sample_txn = group['transactions'][0]
            confidence_data = calculate_recovery_confidence(sample_txn, state_key)
            confidence_level = confidence_data['confidence']

            confidence_groups[confidence_level]['states'].append({
                'state_key': state_key,
                'state_name': state_name,
                'amount': state_amount,
                'fix_action': confidence_data['reason']
            })

    return confidence_groups


# ============================================================================
# PHASE 3: ROOT CAUSE CLASSIFICATION
# ============================================================================

# Root cause definitions with metadata
ROOT_CAUSE_CONFIG = {
    'delayed_invoicing': {
        'name': 'Delayed invoicing',
        'fix_type': 'system',
        'owner': 'IT',
        'fix_days': 5,
        'effort_hours': 8,
        'action': 'Run invoice batch job for deliveries >7 days old'
    },
    'credit_hold_lag': {
        'name': 'Credit hold lag',
        'fix_type': 'policy',
        'owner': 'Finance',
        'fix_days': 2,
        'effort_hours': 4,
        'action': 'Reset credit limits in system'
    },
    'paid_unapplied_cash': {
        'name': 'Paid but unapplied',
        'fix_type': 'system',
        'owner': 'AR Team',
        'fix_days': 3,
        'effort_hours': 12,
        'action': 'Manual cash application'
    },
    'invoice_release_lag': {
        'name': 'Invoice release lag',
        'fix_type': 'process',
        'owner': 'AR Team',
        'fix_days': 1,
        'effort_hours': 2,
        'action': 'Release pending invoices'
    },
    'pricing_mismatch': {
        'name': 'Pricing mismatch',
        'fix_type': 'master_data',
        'owner': 'Finance',
        'fix_days': 10,
        'effort_hours': 6,
        'action': 'Correct pricing and reissue invoice'
    },
    'payment_term_exception': {
        'name': 'Payment term exception',
        'fix_type': 'policy',
        'owner': 'Sales',
        'fix_days': 15,
        'effort_hours': 4,
        'action': 'Enforce standard payment terms'
    },
    'dispute_legitimate': {
        'name': 'Disputes (legitimate)',
        'fix_type': 'process',
        'owner': 'AR Team',
        'fix_days': 30,
        'effort_hours': 8,
        'action': 'Resolve dispute with customer'
    },
    'late_payer_behavioral': {
        'name': 'Late payers (behavioral)',
        'fix_type': 'behavioral',
        'owner': 'Collections',
        'fix_days': 60,
        'effort_hours': 6,
        'action': 'Collections campaign'
    }
}


def classify_root_cause(transaction: Dict, time_state: str, event_logs: List[Dict]) -> Dict:
    """
    Classify the root cause for a transaction.

    Args:
        transaction: Transaction record
        time_state: Time state classification
        event_logs: Event logs for this transaction

    Returns:
        Dictionary with root cause details
    """

    metadata = transaction.get('erp_metadata') or {}

    # Map time states to root causes
    if time_state == 'fulfilled_not_invoiced':
        return {**ROOT_CAUSE_CONFIG['delayed_invoicing'], 'type': 'delayed_invoicing'}

    if time_state == 'credit_hold':
        # Check if there have been credit reviews
        credit_review_events = [
            e for e in event_logs
            if e.get('event_type') == 'CREDIT_REVIEW'
            and e.get('transaction_id') == transaction.get('transaction_id')
        ]
        if len(credit_review_events) == 0:
            return {**ROOT_CAUSE_CONFIG['credit_hold_lag'], 'type': 'credit_hold_lag'}

    if time_state == 'paid_unapplied':
        return {**ROOT_CAUSE_CONFIG['paid_unapplied_cash'], 'type': 'paid_unapplied_cash'}

    if time_state == 'invoiced_not_sent':
        return {**ROOT_CAUSE_CONFIG['invoice_release_lag'], 'type': 'invoice_release_lag'}

    if time_state == 'sent_disputed':
        dispute_reason = metadata.get('dispute_reason')
        if dispute_reason in ['pricing_error', 'billing_error']:
            return {**ROOT_CAUSE_CONFIG['pricing_mismatch'], 'type': 'pricing_mismatch'}
        else:
            return {**ROOT_CAUSE_CONFIG['dispute_legitimate'], 'type': 'dispute_legitimate'}

    # Check payment terms
    payment_terms = metadata.get('payment_terms_days', 30)
    if payment_terms > 60:
        return {**ROOT_CAUSE_CONFIG['payment_term_exception'], 'type': 'payment_term_exception'}

    if time_state == 'undisputed_unpaid':
        return {**ROOT_CAUSE_CONFIG['late_payer_behavioral'], 'type': 'late_payer_behavioral'}

    # Fallback
    return {
        'type': 'unknown',
        'name': 'Unknown',
        'fix_type': 'manual_review',
        'owner': 'Finance',
        'fix_days': None,
        'effort_hours': 8,
        'action': 'Manual investigation required'
    }


def analyze_root_causes(transactions_df: pd.DataFrame, event_logs_df: pd.DataFrame) -> List[Dict]:
    """
    Analyze transactions and group by root cause.

    Returns:
        List of root cause groups sorted by amount
    """

    transactions = transactions_df.to_dict('records')
    event_logs = event_logs_df.to_dict('records')

    # Group transactions by root cause
    root_cause_groups = {}

    for txn in transactions:
        # Classify time state first
        time_state = classify_dso_time_state(txn, event_logs)

        # Then classify root cause
        root_cause = classify_root_cause(txn, time_state, event_logs)
        root_cause_type = root_cause['type']

        if root_cause_type not in root_cause_groups:
            root_cause_groups[root_cause_type] = {
                'type': root_cause_type,
                'name': root_cause['name'],
                'fix_type': root_cause['fix_type'],
                'owner': root_cause['owner'],
                'fix_days': root_cause['fix_days'],
                'effort_hours': root_cause['effort_hours'],
                'action': root_cause['action'],
                'transactions': [],
                'total_amount': 0,
                'count': 0,
                'avg_days': 0
            }

        root_cause_groups[root_cause_type]['transactions'].append(txn)
        root_cause_groups[root_cause_type]['total_amount'] += txn.get('outstanding_amount', 0) or 0
        root_cause_groups[root_cause_type]['count'] += 1

    # Calculate average days for each group
    for group in root_cause_groups.values():
        if group['count'] > 0:
            total_days = sum(t.get('days_outstanding', 0) or 0 for t in group['transactions'])
            group['avg_days'] = total_days / group['count']

    # Convert to list and sort by total amount (descending)
    root_cause_list = list(root_cause_groups.values())
    root_cause_list.sort(key=lambda x: x['total_amount'], reverse=True)

    return root_cause_list


# ============================================================================
# PHASE 4: EFFICIENCY CALCULATION & EXECUTION QUEUE
# ============================================================================

def calculate_efficiency(root_cause_group: Dict) -> float:
    """
    Calculate recovery efficiency ($ per day per hour of effort).

    Args:
        root_cause_group: Root cause group dictionary

    Returns:
        Efficiency score (dollars per day per hour)
    """

    total_impact = root_cause_group['total_amount']
    fix_days = root_cause_group['fix_days']
    effort_hours = root_cause_group['effort_hours']

    if not fix_days or fix_days == 0 or effort_hours == 0:
        return 0

    # Dollars recovered per day per hour of effort
    efficiency = total_impact / (fix_days * effort_hours)

    return efficiency


def generate_execution_queue(root_cause_list: List[Dict]) -> List[Dict]:
    """
    Generate execution queue ranked by efficiency.

    Args:
        root_cause_list: List of root cause groups

    Returns:
        List of execution items sorted by efficiency (highest first)
    """

    execution_queue = []

    for rc in root_cause_list:
        efficiency = calculate_efficiency(rc)

        execution_queue.append({
            'rank': 0,  # Will be assigned after sorting
            'root_cause_type': rc['type'],
            'root_cause_name': rc['name'],
            'total_impact': rc['total_amount'],
            'transaction_count': rc['count'],
            'avg_days': rc['avg_days'],
            'fix_days': rc['fix_days'],
            'effort_hours': rc['effort_hours'],
            'efficiency': efficiency,
            'fix_type': rc['fix_type'],
            'owner': rc['owner'],
            'action': rc['action']
        })

    # Sort by efficiency (highest first)
    execution_queue.sort(key=lambda x: x['efficiency'], reverse=True)

    # Assign ranks
    for i, item in enumerate(execution_queue):
        item['rank'] = i + 1

    return execution_queue
