"""
DIO Recovery Analysis - Calculate Net Recovery Potential

This module provides functions to calculate net recovery potential for DIO issues,
distinguishing between trapped capital (fully recoverable), partial recovery
(liquidation value), and recognized losses (write-offs required).

Author: Capital Leak Analysis Team
Date: 2025-01-10
"""

import json
import pandas as pd
from typing import Dict, List, Tuple


def calculate_dio_recovery(transactions_df: pd.DataFrame) -> Dict:
    """
    Calculate net recovery potential for DIO transactions

    Args:
        transactions_df: DataFrame containing DIO transactions with erp_metadata

    Returns:
        Dictionary containing:
            - total_value: Total value of all DIO issues
            - trapped_capital: Fully recoverable amount
            - partial_recovery: Liquidation value from excess/obsolete
            - recognized_losses: Write-offs required (negative variances, failed inspections, etc.)
            - net_recovery: trapped_capital + partial_recovery
            - recovery_rate: Percentage of total value that's recoverable
            - breakdown_by_status: Detailed breakdown by status
    """

    # Filter to DIO transactions only
    dio_df = transactions_df[transactions_df['component_type'] == 'DIO'].copy()

    if len(dio_df) == 0:
        return {
            'total_value': 0,
            'trapped_capital': 0,
            'partial_recovery': 0,
            'recognized_losses': 0,
            'net_recovery': 0,
            'recovery_rate': 0,
            'breakdown_by_status': {}
        }

    # Initialize accumulators
    trapped_capital = 0
    partial_recovery = 0
    recognized_losses = 0
    breakdown_by_status = {}

    # Process each transaction
    for _, row in dio_df.iterrows():
        amount = row['amount']
        status = row['status']

        # Parse erp_metadata if it exists
        recovery_category = None
        recovery_potential = amount  # Default: assume full recovery

        if pd.notna(row.get('erp_metadata')):
            try:
                metadata = json.loads(row['erp_metadata'])
                recovery_category = metadata.get('recovery_category')
                recovery_potential = metadata.get('recovery_potential', amount)
            except (json.JSONDecodeError, TypeError):
                pass

        # Categorize based on recovery_category or status
        if recovery_category == 'TRAPPED_CAPITAL':
            trapped_capital += recovery_potential
            category = 'Trapped Capital'
        elif recovery_category == 'PARTIAL_RECOVERY':
            partial_recovery += recovery_potential
            category = 'Partial Recovery'
        elif recovery_category == 'RECOGNIZED_LOSS':
            recognized_losses += amount
            category = 'Recognized Loss'
        else:
            # Fallback: categorize by status if no recovery_category
            category = _categorize_by_status(status, amount)
            if category == 'Trapped Capital':
                trapped_capital += amount
            elif category == 'Partial Recovery':
                # Estimate 65% liquidation value
                partial_recovery += amount * 0.65
            elif category == 'Recognized Loss':
                recognized_losses += amount
            else:
                # Default: assume trapped capital for unknown statuses
                trapped_capital += amount
                category = 'Trapped Capital'

        # Track breakdown by status
        if status not in breakdown_by_status:
            breakdown_by_status[status] = {
                'count': 0,
                'total_value': 0,
                'recovery_potential': 0,
                'category': category
            }
        breakdown_by_status[status]['count'] += 1
        breakdown_by_status[status]['total_value'] += amount
        breakdown_by_status[status]['recovery_potential'] += recovery_potential if recovery_category else (amount * 0.65 if category == 'Partial Recovery' else amount if category == 'Trapped Capital' else 0)

    # Calculate totals
    total_value = trapped_capital + partial_recovery + recognized_losses
    net_recovery = trapped_capital + partial_recovery
    recovery_rate = (net_recovery / total_value * 100) if total_value > 0 else 0

    return {
        'total_value': round(total_value, 2),
        'trapped_capital': round(trapped_capital, 2),
        'partial_recovery': round(partial_recovery, 2),
        'recognized_losses': round(recognized_losses, 2),
        'net_recovery': round(net_recovery, 2),
        'recovery_rate': round(recovery_rate, 2),
        'breakdown_by_status': breakdown_by_status
    }


def _categorize_by_status(status: str, amount: float) -> str:
    """
    Categorize transaction by status when recovery_category is not available

    Args:
        status: Transaction status
        amount: Transaction amount

    Returns:
        Category: 'Trapped Capital', 'Partial Recovery', or 'Recognized Loss'
    """

    # Trapped Capital statuses
    trapped_capital_statuses = [
        'COUNT_VARIANCE_POSITIVE',
        'RECEIVED_NOT_VALUED',
        'QUALITY_HOLD_RELEASABLE',
        'QUALITY_HOLD',  # Assume releasable if not specified
        'RESERVED_CANCELLED_ORDER',
        'STAGED_NOT_SHIPPED',
        'RELEASED_NOT_STARTED',
        'AT_SUBCONTRACTOR'
    ]

    # Recognized Loss statuses
    loss_statuses = [
        'COUNT_VARIANCE_NEGATIVE',
        'QUALITY_HOLD_FAILED',
        'OBSOLETE_ZERO_VALUE',
        'DAMAGED_RTV_PENDING'  # Assume rejected if not specified
    ]

    # Partial Recovery statuses
    partial_recovery_statuses = [
        'OBSOLETE_LIQUIDATION',
        'OBSOLETE'  # Assume liquidation value if not specified
    ]

    if status in trapped_capital_statuses:
        return 'Trapped Capital'
    elif status in loss_statuses:
        return 'Recognized Loss'
    elif status in partial_recovery_statuses:
        return 'Partial Recovery'
    else:
        # Default: trapped capital (conservative estimate)
        return 'Trapped Capital'


def format_recovery_summary(recovery_data: Dict) -> str:
    """
    Format recovery data as a human-readable summary

    Args:
        recovery_data: Dictionary returned by calculate_dio_recovery()

    Returns:
        Formatted string summary
    """

    summary = f"""
DIO RECOVERY ANALYSIS
{'='*60}

Total DIO Value:                    ${recovery_data['total_value']:,.2f}

BREAKDOWN:
├─ Trapped Capital (Fully Recoverable):  ${recovery_data['trapped_capital']:,.2f}
│  └─ Inventory exists, system can't allocate
├─ Partial Recovery (Liquidation):       ${recovery_data['partial_recovery']:,.2f}
│  └─ Excess/obsolete can be liquidated at discount
└─ Recognized Losses (Write-offs):       ${recovery_data['recognized_losses']:,.2f}
   └─ Shrinkage, damage, obsolete (zero value)

{'─'*60}
NET RECOVERY POTENTIAL:              ${recovery_data['net_recovery']:,.2f}
RECOVERY RATE:                       {recovery_data['recovery_rate']:.1f}%
{'='*60}

Balance Sheet Impact:
• Inventory currently overstated by: ${recovery_data['recognized_losses']:,.2f}
• Hidden assets to be recognized:    ${recovery_data['trapped_capital']:,.2f}
• Write-downs required:               ${recovery_data['recognized_losses']:,.2f}
"""

    return summary


def get_recovery_by_category(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get DIO transactions grouped by recovery category

    Args:
        transactions_df: DataFrame containing DIO transactions

    Returns:
        DataFrame with transactions grouped by recovery category
    """

    dio_df = transactions_df[transactions_df['component_type'] == 'DIO'].copy()

    if len(dio_df) == 0:
        return pd.DataFrame(columns=['recovery_category', 'count', 'total_value', 'recovery_potential'])

    # Add recovery_category column
    def get_category(row):
        if pd.notna(row.get('erp_metadata')):
            try:
                metadata = json.loads(row['erp_metadata'])
                return metadata.get('recovery_category', 'UNKNOWN')
            except (json.JSONDecodeError, TypeError):
                pass
        return _categorize_by_status(row['status'], row['amount']).upper().replace(' ', '_')

    dio_df['recovery_category'] = dio_df.apply(get_category, axis=1)

    # Group by recovery category
    grouped = dio_df.groupby('recovery_category').agg({
        'transaction_id': 'count',
        'amount': 'sum'
    }).rename(columns={'transaction_id': 'count', 'amount': 'total_value'})

    # Calculate recovery potential
    grouped['recovery_potential'] = grouped.apply(
        lambda row: row['total_value'] if row.name in ['TRAPPED_CAPITAL']
                    else row['total_value'] * 0.65 if row.name == 'PARTIAL_RECOVERY'
                    else 0,
        axis=1
    )

    return grouped.reset_index()
