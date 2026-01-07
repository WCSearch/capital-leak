"""
DIO Time-State Analysis Module

Transforms DIO from a single metric into a diagnostic tool that identifies:
1. WHERE inventory time is accumulating (time states)
2. WHICH dollars are actually recoverable (confidence levels)
3. WHAT to fix first (efficiency-ranked by $/day/hour)
4. HOW to fix it (specific action + owner)

Parallel structure to DSO analysis but for inventory management.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd


# Time-state definitions with metadata (DIO-specific)
TIME_STATE_CONFIG = {
    'received_not_valued': {
        'name': 'Received but Not Valued',
        'priority': 'CRITICAL',
        'color': 'red',
        'fix_action': 'Post valuations for received goods',
        'timeline': '7 days',
        'order': 1
    },
    'quality_hold_stall': {
        'name': 'Quality Hold Stall',
        'priority': 'CRITICAL',
        'color': 'red',
        'fix_action': 'Complete QA inspections',
        'timeline': '2 days',
        'order': 2
    },
    'ghost_allocation': {
        'name': 'Ghost Allocations (Unreleased Reservations)',
        'priority': 'CRITICAL',
        'color': 'red',
        'fix_action': 'Release cancelled order reservations',
        'timeline': '3 days',
        'order': 3
    },
    'obsolete_unwritten': {
        'name': 'Obsolete but Not Written Off',
        'priority': 'MEDIUM',
        'color': 'amber',
        'fix_action': 'Write off obsolete inventory',
        'timeline': '15 days',
        'order': 4
    },
    'slow_moving': {
        'name': 'Slow-Moving Inventory',
        'priority': 'MEDIUM',
        'color': 'amber',
        'fix_action': 'Liquidate or repurpose',
        'timeline': '30 days',
        'order': 5
    },
    'excess_inventory': {
        'name': 'Excess Inventory',
        'priority': 'LOW',
        'color': 'green',
        'fix_action': 'Reduce procurement',
        'timeline': '45 days',
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


def classify_dio_time_state(transaction: Dict, event_logs: List[Dict]) -> str:
    """
    Classify a DIO transaction into one of 6 mutually exclusive time states.

    Args:
        transaction: Inventory record
        event_logs: List of event log records for this material

    Returns:
        Time state key (e.g., 'received_not_valued', 'quality_hold_stall', etc.)
    """

    metadata = transaction.get('erp_metadata') or {}
    status = transaction.get('status', '').upper()
    days_outstanding = transaction.get('days_outstanding', 0) or 0
    amount = transaction.get('amount', 0) or 0
    outstanding_amount = transaction.get('outstanding_amount', 0) or 0  # quantity proxy

    # Check for received but not valued
    if amount == 0 and outstanding_amount > 0:
        return 'received_not_valued'

    # Check if in quality hold
    stock_type = metadata.get('stock_type', '') if isinstance(metadata, dict) else ''
    if (status == 'QUALITY_HOLD' or stock_type == 'quality_inspection') and days_outstanding > 2:
        return 'quality_hold_stall'

    # Check for ghost allocations
    if 'RESERVED' in status and days_outstanding > 7:
        return 'ghost_allocation'

    # Check for obsolete inventory
    if days_outstanding > 180 and amount > 10000:
        return 'obsolete_unwritten'

    # Check for slow-moving inventory
    if days_outstanding > 90:
        return 'slow_moving'

    # Check for excess inventory
    if days_outstanding > 60:
        return 'excess_inventory'

    # Default: slow-moving to ensure visibility
    return 'slow_moving'


def analyze_dio_time_states(
    inventory_df: pd.DataFrame,
    movements_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> Dict:
    """
    Analyze all DIO inventory and group by time state.

    Args:
        inventory_df: DataFrame of inventory transactions
        movements_df: DataFrame of inventory movements (optional)
        event_logs_df: DataFrame of event logs

    Returns:
        Dictionary with time state breakdown (same structure as DSO)
    """

    # Convert DataFrames to list of dicts for processing
    inventory = inventory_df.to_dict('records')
    event_logs = event_logs_df.to_dict('records') if event_logs_df is not None and len(event_logs_df) > 0 else []

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

    # Also track normal inventory
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

    # Classify each inventory item
    for item in inventory:
        time_state = classify_dio_time_state(item, event_logs)

        if time_state in time_state_groups:
            time_state_groups[time_state]['transactions'].append(item)
            time_state_groups[time_state]['total_amount'] += item.get('amount', 0) or 0
            time_state_groups[time_state]['count'] += 1

    # Calculate average days for each group
    for state_key, group in time_state_groups.items():
        if group['count'] > 0:
            total_days = sum(t.get('days_outstanding', 0) or 0 for t in group['transactions'])
            group['avg_days'] = total_days / group['count']

    return time_state_groups


def get_dio_time_state_summary(time_state_groups: Dict) -> List[Dict]:
    """
    Get a summary of DIO time states for dashboard display.

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
    Calculate recovery confidence level for an inventory item.

    Returns:
        Dictionary with confidence, days, and reason
    """

    days_outstanding = transaction.get('days_outstanding', 0) or 0

    # CERTAIN: System/process fix, no coordination needed
    if time_state == 'received_not_valued':
        return {
            'confidence': 'CERTAIN',
            'days': 7,
            'reason': 'Post valuation in system'
        }

    if time_state == 'quality_hold_stall':
        return {
            'confidence': 'CERTAIN',
            'days': 2,
            'reason': 'Complete QA inspection'
        }

    if time_state == 'ghost_allocation':
        return {
            'confidence': 'CERTAIN',
            'days': 3,
            'reason': 'Release reservation'
        }

    # PROBABLE: Clear action but requires coordination
    if time_state == 'obsolete_unwritten':
        return {
            'confidence': 'PROBABLE',
            'days': 15,
            'reason': 'Write-off approval needed'
        }

    if time_state == 'slow_moving':
        return {
            'confidence': 'PROBABLE',
            'days': 30,
            'reason': 'Liquidation or repurposing'
        }

    # CONTESTED: Requires business decision
    if time_state == 'excess_inventory':
        return {
            'confidence': 'CONTESTED',
            'days': 45,
            'reason': 'Procurement policy change'
        }

    # Default
    return {
        'confidence': 'CONTESTED',
        'days': 30,
        'reason': 'Manual review required'
    }


def analyze_dio_recovery_confidence(time_state_groups: Dict) -> Dict:
    """
    Analyze recovery confidence across all DIO time states.

    Returns:
        Dictionary with confidence breakdown (same structure as DSO)
    """

    confidence_groups = {
        'CERTAIN': {
            'total_amount': 0,
            'percentage': 0,
            'states': [],
            'expected_timeline': '2-7 days'
        },
        'PROBABLE': {
            'total_amount': 0,
            'percentage': 0,
            'states': [],
            'expected_timeline': '15-30 days'
        },
        'CONTESTED': {
            'total_amount': 0,
            'percentage': 0,
            'states': [],
            'expected_timeline': '45+ days'
        }
    }

    # Calculate confidence for each inventory item in each time state
    for state_key, group in time_state_groups.items():
        if state_key == 'normal':
            continue

        for item in group['transactions']:
            confidence_data = calculate_recovery_confidence(item, state_key)
            confidence_level = confidence_data['confidence']

            if confidence_level in confidence_groups:
                confidence_groups[confidence_level]['total_amount'] += item.get('amount', 0) or 0

    # Calculate totals and percentages
    total_amount = sum(g['total_amount'] for g in confidence_groups.values())

    if total_amount > 0:
        for level, data in confidence_groups.items():
            data['percentage'] = (data['total_amount'] / total_amount) * 100

    # Add state-level details
    for state_key, group in time_state_groups.items():
        if state_key == 'normal' or group['count'] == 0:
            continue

        state_amount = group['total_amount']
        state_name = group['config']['name']

        if group['transactions']:
            sample_item = group['transactions'][0]
            confidence_data = calculate_recovery_confidence(sample_item, state_key)
            confidence_level = confidence_data['confidence']

            confidence_groups[confidence_level]['states'].append({
                'state_key': state_key,
                'state_name': state_name,
                'amount': state_amount,
                'fix_action': confidence_data['reason']
            })

    return confidence_groups


# ============================================================================
# PHASE 3: ROOT CAUSE ANALYSIS
# ============================================================================

def analyze_dio_root_causes(
    inventory_df: pd.DataFrame,
    movements_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> List[Dict]:
    """
    Analyze inventory and group by root cause.

    If event_logs_df has data:
        → Use event_log_analyzer_dio.synthesize_dio_root_causes()
        → Returns evidence-based root causes with HIGH/MEDIUM confidence

    If event_logs_df is empty or None:
        → Fall back to rule-based classification
        → Returns threshold-based classifications with LOW confidence

    Returns:
        List of root cause groups sorted by amount
    """

    # Check if we have event logs to work with
    has_event_logs = event_logs_df is not None and len(event_logs_df) > 0

    if has_event_logs:
        # PHASE 2: Event log forensics
        from utils.event_log_analyzer_dio import synthesize_dio_root_causes

        # Get detailed root cause classification for each item
        classified_df = synthesize_dio_root_causes(
            inventory_df,
            movements_df if movements_df is not None else pd.DataFrame(),
            event_logs_df
        )

    else:
        # PHASE 1: Rule-based fallback
        from utils.root_cause_classifier_dio import classify_dio_root_causes

        inventory = inventory_df.to_dict('records')
        movements = movements_df.to_dict('records') if movements_df is not None else []

        classified_df = classify_dio_root_causes(
            inventory_df,
            movements_df if movements_df is not None else pd.DataFrame()
        )

    # Aggregate classified items by root cause type
    root_cause_groups = {}

    for _, row in classified_df.iterrows():
        root_cause_type = row['root_cause_type']

        if root_cause_type not in root_cause_groups:
            # Estimate effort hours based on fix type
            effort_hours = {
                'system': 8,
                'policy': 4,
                'process': 6,
                'master_data': 6,
                'behavioral': 6,
                'manual_review': 8,
                'none': 0
            }.get(row['fix_type'], 8)

            # Create human-readable name from type
            name = root_cause_type.replace('_', ' ').title()

            # Get evidence detail
            evidence_detail = row.get('evidence_detail', '')

            root_cause_groups[root_cause_type] = {
                'type': root_cause_type,
                'name': name,
                'fix_type': row['fix_type'],
                'owner': row['fix_owner'],
                'fix_days': row['fix_days_estimate'],
                'effort_hours': effort_hours,
                'action': evidence_detail if evidence_detail else f'Address {name}',
                'transactions': [],
                'total_amount': 0,
                'count': 0,
                'avg_days': 0,
                'evidence_source': row.get('evidence_source', 'rule_based'),
                'evidence_detail': evidence_detail
            }

        # Add item to group
        root_cause_groups[root_cause_type]['transactions'].append(row.to_dict())
        root_cause_groups[root_cause_type]['total_amount'] += row.get('amount', 0) or 0
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


def generate_dio_execution_queue(root_cause_list: List[Dict]) -> List[Dict]:
    """
    Generate DIO execution queue ranked by efficiency.

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
