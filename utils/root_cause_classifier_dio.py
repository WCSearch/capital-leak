"""
Rule-Based Root Cause Classifier - DIO Fallback

This module provides rule-based DIO classification using only transaction fields
when event logs are not available. It maintains the same output schema as
the event log analyzer but with lower confidence levels.

Classification rules (priority order):
1. received_not_valued: stock_value = 0 but has quantity
2. quality_hold_stall: status = 'QUALITY_HOLD' for >2 days
3. ghost_allocation: status = 'RESERVED' with no linked order
4. obsolete_unwritten: days_outstanding > 180, value > $10K
5. slow_moving: days_outstanding > 90, no recent activity
6. negative_stock: stock balance < 0
7. normal: everything else
"""

from datetime import datetime
import pandas as pd
import numpy as np


# Root cause definitions with fix metadata
ROOT_CAUSE_DEFINITIONS = {
    'received_not_valued': {
        'fix_type': 'system',
        'fix_owner': 'Finance',
        'fix_days_estimate': 7,
        'recovery_confidence': 'CERTAIN',
        'description': 'Goods received but valuation not posted'
    },
    'quality_hold_stall': {
        'fix_type': 'process',
        'fix_owner': 'Quality',
        'fix_days_estimate': 2,
        'recovery_confidence': 'CERTAIN',
        'description': 'Stock stuck in quality inspection'
    },
    'ghost_allocation': {
        'fix_type': 'system',
        'fix_owner': 'IT',
        'fix_days_estimate': 3,
        'recovery_confidence': 'CERTAIN',
        'description': 'Unreleased stock reservation'
    },
    'obsolete_unwritten': {
        'fix_type': 'policy',
        'fix_owner': 'Finance',
        'fix_days_estimate': 15,
        'recovery_confidence': 'PROBABLE',
        'description': 'Obsolete inventory not written off'
    },
    'slow_moving': {
        'fix_type': 'policy',
        'fix_owner': 'Procurement',
        'fix_days_estimate': 30,
        'recovery_confidence': 'PROBABLE',
        'description': 'Slow-moving inventory with no action'
    },
    'negative_stock': {
        'fix_type': 'system',
        'fix_owner': 'IT',
        'fix_days_estimate': 5,
        'recovery_confidence': 'CERTAIN',
        'description': 'Negative stock balance (system error)'
    },
    'excess_inventory': {
        'fix_type': 'policy',
        'fix_owner': 'Procurement',
        'fix_days_estimate': 45,
        'recovery_confidence': 'CONTESTED',
        'description': 'Excess inventory above demand forecast'
    },
    'normal': {
        'fix_type': 'none',
        'fix_owner': 'None',
        'fix_days_estimate': 0,
        'recovery_confidence': 'CERTAIN',
        'description': 'Normal inventory movement'
    }
}


def classify_dio_root_causes(inventory_df: pd.DataFrame, movements_df: pd.DataFrame) -> pd.DataFrame:
    """
    Rule-based DIO classification using only transaction fields (no event logs).

    Classification rules (priority order):
    1. negative_stock: outstanding_amount < 0
    2. received_not_valued: amount = 0 but outstanding_amount > 0
    3. quality_hold_stall: status = 'QUALITY_HOLD', days_outstanding > 2
    4. ghost_allocation: status contains 'RESERVED', days_outstanding > 7
    5. obsolete_unwritten: days_outstanding > 180, amount > $10K
    6. slow_moving: days_outstanding > 90
    7. excess_inventory: days_outstanding > 60
    8. normal: everything else

    Returns DataFrame with same structure as event log analyzer
    (but with root_cause_confidence='LOW' and evidence_source='rule_based')
    """

    result_df = inventory_df.copy()

    # Initialize result columns
    result_df['root_cause_type'] = 'normal'
    result_df['root_cause_confidence'] = 'LOW'
    result_df['evidence_source'] = 'rule_based'
    result_df['evidence_detail'] = ''
    result_df['fix_type'] = 'none'
    result_df['fix_owner'] = 'None'
    result_df['fix_days_estimate'] = 0
    result_df['recovery_confidence'] = 'CERTAIN'

    # Extract metadata fields (stored in erp_metadata JSONB)
    def safe_get_metadata(row, key, default=None):
        metadata = row.get('erp_metadata')
        if pd.isna(metadata) or metadata is None:
            return default
        if isinstance(metadata, dict):
            return metadata.get(key, default)
        return default

    # RULE 1: Negative stock (system error)
    for idx, row in result_df.iterrows():
        outstanding = row.get('outstanding_amount', 0) or 0
        amount = row.get('amount', 0) or 0

        if outstanding < 0:
            result_df.at[idx, 'root_cause_type'] = 'negative_stock'
            result_df.at[idx, 'evidence_detail'] = f'Negative stock balance ({outstanding} units)'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['negative_stock']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['negative_stock']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['negative_stock']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['negative_stock']['recovery_confidence']

    # RULE 2: Received but not valued
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'normal':
            continue

        outstanding = row.get('outstanding_amount', 0) or 0
        amount = row.get('amount', 0) or 0

        if amount == 0 and outstanding > 0:
            result_df.at[idx, 'root_cause_type'] = 'received_not_valued'
            result_df.at[idx, 'evidence_detail'] = f'Stock has {outstanding} units but zero valuation'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['received_not_valued']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['received_not_valued']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['received_not_valued']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['received_not_valued']['recovery_confidence']

    # RULE 3: Quality hold stall
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'normal':
            continue

        status = row.get('status', '')
        days_outstanding = row.get('days_outstanding', 0) or 0

        metadata = row.get('erp_metadata') or {}
        stock_type = metadata.get('stock_type', '') if isinstance(metadata, dict) else ''

        if (status == 'QUALITY_HOLD' or stock_type == 'quality_inspection') and days_outstanding > 2:
            result_df.at[idx, 'root_cause_type'] = 'quality_hold_stall'
            result_df.at[idx, 'evidence_detail'] = f'QA inspection pending for {days_outstanding} days'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['quality_hold_stall']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['quality_hold_stall']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['quality_hold_stall']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['quality_hold_stall']['recovery_confidence']

    # RULE 4: Ghost allocation
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'normal':
            continue

        status = row.get('status', '')
        days_outstanding = row.get('days_outstanding', 0) or 0

        if 'RESERVED' in status and days_outstanding > 7:
            result_df.at[idx, 'root_cause_type'] = 'ghost_allocation'
            result_df.at[idx, 'evidence_detail'] = f'Stock reserved for {days_outstanding} days with no release'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['ghost_allocation']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['ghost_allocation']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['ghost_allocation']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['ghost_allocation']['recovery_confidence']

    # RULE 5: Obsolete inventory not written off
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'normal':
            continue

        days_outstanding = row.get('days_outstanding', 0) or 0
        amount = row.get('amount', 0) or 0

        if days_outstanding > 180 and amount > 10000:
            result_df.at[idx, 'root_cause_type'] = 'obsolete_unwritten'
            result_df.at[idx, 'evidence_detail'] = f'No movement for {days_outstanding} days, ${amount:,.0f} potentially obsolete'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['obsolete_unwritten']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['obsolete_unwritten']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['obsolete_unwritten']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['obsolete_unwritten']['recovery_confidence']

    # RULE 6: Slow-moving inventory
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'normal':
            continue

        days_outstanding = row.get('days_outstanding', 0) or 0

        if days_outstanding > 90:
            result_df.at[idx, 'root_cause_type'] = 'slow_moving'
            result_df.at[idx, 'evidence_detail'] = f'Slow-moving inventory ({days_outstanding} days old)'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['slow_moving']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['slow_moving']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['slow_moving']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['slow_moving']['recovery_confidence']

    # RULE 7: Excess inventory
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'normal':
            continue

        days_outstanding = row.get('days_outstanding', 0) or 0

        if days_outstanding > 60:
            result_df.at[idx, 'root_cause_type'] = 'excess_inventory'
            result_df.at[idx, 'evidence_detail'] = f'Excess inventory ({days_outstanding} days old)'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['excess_inventory']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['excess_inventory']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['excess_inventory']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['excess_inventory']['recovery_confidence']

    # RULE 8: Normal (default)
    for idx, row in result_df.iterrows():
        if result_df.at[idx, 'root_cause_type'] == 'normal':
            days_outstanding = row.get('days_outstanding', 0) or 0
            result_df.at[idx, 'evidence_detail'] = f'Normal inventory movement ({days_outstanding} days in stock)'

    return result_df


def get_root_cause_summary(classified_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate classified inventory by root cause type for dashboard display.

    Returns summary DataFrame with:
    - root_cause_type
    - count
    - total_amount
    - avg_days_outstanding
    - fix_type
    - fix_owner
    - fix_days_estimate
    - recovery_confidence
    """

    summary = classified_df.groupby('root_cause_type').agg({
        'transaction_id': 'count',
        'amount': 'sum',
        'days_outstanding': 'mean',
        'fix_type': 'first',
        'fix_owner': 'first',
        'fix_days_estimate': 'first',
        'recovery_confidence': 'first'
    }).reset_index()

    summary.columns = [
        'root_cause_type',
        'count',
        'total_amount',
        'avg_days_outstanding',
        'fix_type',
        'fix_owner',
        'fix_days_estimate',
        'recovery_confidence'
    ]

    # Sort by total amount (descending)
    summary = summary.sort_values('total_amount', ascending=False)

    return summary
