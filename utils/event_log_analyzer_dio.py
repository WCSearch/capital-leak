"""
Event Log Analysis Module - DIO Forensics

This module provides event-level forensics for Days Inventory Outstanding (DIO),
identifying root causes of inventory cash delays through ERP event log analysis.

Key capabilities:
1. Sequence inversions (goods issue before receipt, etc.)
2. Valuation failures (received but not valued)
3. Quality bottlenecks (stuck in QA inspection)
4. Ghost allocations (unreleased reservations from cancelled orders)
5. Obsolescence detection (aged inventory with no write-off action)
6. Root cause synthesis (definitive attribution with evidence)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


# Valid event sequences for inventory workflows
VALID_SEQUENCES = {
    'goods_receipt': [
        'GOODS_RECEIPT',
        'VALUATION_POSTED',
        'QUALITY_DECISION',
        'UNRESTRICTED',
        'GOODS_ISSUE'
    ],
    'stock_transfer': [
        'STOCK_RESERVED',
        'TRANSFER_POSTED',
        'VALUATION_UPDATED'
    ]
}

# Inversion patterns for inventory
INVERSION_PATTERNS = {
    'issue_before_receipt': {
        'prerequisite': 'GOODS_RECEIPT',
        'dependent': 'GOODS_ISSUE',
        'severity': 'HIGH',
        'description': 'Stock issued before goods receipt (negative stock)'
    },
    'valuation_before_receipt': {
        'prerequisite': 'GOODS_RECEIPT',
        'dependent': 'VALUATION_POSTED',
        'severity': 'MEDIUM',
        'description': 'Valuation posted before physical receipt'
    },
    'transfer_without_receipt': {
        'prerequisite': 'GOODS_RECEIPT',
        'dependent': 'TRANSFER_POSTED',
        'severity': 'HIGH',
        'description': 'Stock transfer without originating receipt'
    }
}


def detect_dio_sequence_inversions(
    inventory_df: pd.DataFrame,
    movements_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Detect DIO events that occurred in wrong order (temporal paradoxes).

    Valid sequences:
    - GOODS_RECEIPT → VALUATION_POSTED → QUALITY_DECISION → UNRESTRICTED → GOODS_ISSUE
    - STOCK_RESERVED → TRANSFER_POSTED → VALUATION_UPDATED

    Invalid patterns:
    - GOODS_ISSUE before GOODS_RECEIPT (negative stock)
    - VALUATION_POSTED before GOODS_RECEIPT
    - TRANSFER_POSTED without GOODS_RECEIPT

    Returns DataFrame with columns:
    - material_id
    - inversion_pattern
    - prerequisite_event (should have happened first)
    - dependent_event (happened too early)
    - time_gap_seconds (negative = inversion)
    - first_occurrence_date
    - user_id, module
    - stock_value
    """

    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()

    inversions = []

    # For inventory, we'll check by material_id or transaction_id
    # Assuming inventory_df has a material_id field
    material_ids = inventory_df.get('material_id', inventory_df.get('transaction_id', pd.Series(dtype=str)))

    # Group events by material
    for mat_id in material_ids.unique():
        mat_events = event_logs_df[
            (event_logs_df['transaction_id'] == mat_id) |
            (event_logs_df.get('event_data', pd.Series([{}]*len(event_logs_df))).apply(
                lambda x: x.get('material_id') == mat_id if isinstance(x, dict) else False
            ))
        ].copy()

        if len(mat_events) == 0:
            continue

        # Get stock value
        stock_value = inventory_df[material_ids == mat_id]['amount'].iloc[0] if len(inventory_df[material_ids == mat_id]) > 0 else 0

        # Ensure event_timestamp is datetime
        mat_events['event_timestamp'] = pd.to_datetime(mat_events['event_timestamp'])

        # Create event lookup by type
        event_lookup = {}
        for _, event in mat_events.iterrows():
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
                        'material_id': mat_id,
                        'inversion_pattern': pattern_name,
                        'prerequisite_event': prereq,
                        'dependent_event': dependent,
                        'time_gap_seconds': -time_gap_seconds,
                        'first_occurrence_date': dependent_time,
                        'user_id': dependent_event['user_id'],
                        'module': dependent_event['module'],
                        'stock_value': stock_value,
                        'severity': pattern_def['severity'],
                        'description': pattern_def['description']
                    })

    if len(inversions) > 0:
        return pd.DataFrame(inversions)
    else:
        return pd.DataFrame()


def analyze_dio_valuation_failures(
    inventory_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Find received-not-valued cases with evidence.

    Detects:
    - GOODS_RECEIPT exists but no VALUATION_POSTED event
    - Stock value = 0 despite having quantity
    - Valuation pending >7 days since receipt

    Returns DataFrame with columns:
    - material_id
    - goods_receipt_date
    - days_since_receipt
    - stock_quantity
    - expected_value
    - actual_value
    - root_cause_detail
    - stock_value
    """

    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()

    valuation_failures = []
    now = datetime.now()

    # Identify materials with goods receipts
    material_ids = inventory_df.get('material_id', inventory_df.get('transaction_id', pd.Series(dtype=str)))

    for mat_id in material_ids.unique():
        mat_events = event_logs_df[
            (event_logs_df['transaction_id'] == mat_id) |
            (event_logs_df.get('event_data', pd.Series([{}]*len(event_logs_df))).apply(
                lambda x: x.get('material_id') == mat_id if isinstance(x, dict) else False
            ))
        ].copy()

        if len(mat_events) == 0:
            continue

        # Get material data
        mat_data = inventory_df[material_ids == mat_id]
        if len(mat_data) == 0:
            continue

        mat_data = mat_data.iloc[0]
        stock_value = mat_data.get('amount', 0) or 0
        stock_quantity = mat_data.get('outstanding_amount', 0) or 0  # Using outstanding_amount as quantity proxy

        # Ensure event_timestamp is datetime
        mat_events['event_timestamp'] = pd.to_datetime(mat_events['event_timestamp'])

        # Check for GOODS_RECEIPT events
        gr_events = mat_events[mat_events['event_type'] == 'GOODS_RECEIPT']
        valuation_events = mat_events[mat_events['event_type'] == 'VALUATION_POSTED']

        if len(gr_events) > 0 and len(valuation_events) == 0:
            # Goods received but never valued
            gr_date = gr_events.sort_values('event_timestamp').iloc[-1]['event_timestamp']
            days_since_receipt = (now - gr_date).days

            if days_since_receipt > 7:
                valuation_failures.append({
                    'material_id': mat_id,
                    'goods_receipt_date': gr_date,
                    'days_since_receipt': days_since_receipt,
                    'stock_quantity': stock_quantity,
                    'expected_value': stock_quantity * 100,  # Rough estimate
                    'actual_value': stock_value,
                    'root_cause_detail': f'Goods received {days_since_receipt} days ago but valuation not posted',
                    'stock_value': stock_value
                })
        elif stock_value == 0 and stock_quantity > 0:
            # Stock exists but has zero value
            valuation_failures.append({
                'material_id': mat_id,
                'goods_receipt_date': mat_data.get('transaction_date'),
                'days_since_receipt': (now - pd.to_datetime(mat_data.get('transaction_date'))).days if mat_data.get('transaction_date') else 0,
                'stock_quantity': stock_quantity,
                'expected_value': stock_quantity * 100,
                'actual_value': 0,
                'root_cause_detail': 'Stock has quantity but zero valuation',
                'stock_value': stock_value
            })

    if len(valuation_failures) > 0:
        return pd.DataFrame(valuation_failures)
    else:
        return pd.DataFrame()


def analyze_dio_quality_bottlenecks(
    inventory_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Find quality-hold-stall cases with QA workflow details.

    Detects:
    - Stock in quality inspection status with no QUALITY_DECISION event
    - QA inspection pending >48 hours (2 days)
    - Inspector assigned but not responding

    Returns DataFrame with columns:
    - material_id
    - inspection_start_date
    - days_in_qa
    - assigned_inspector
    - inspector_last_seen
    - root_cause_detail
    - stock_value
    """

    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()

    qa_bottlenecks = []
    now = datetime.now()

    # Identify inspector activity globally
    inspector_activity = {}
    for _, event in event_logs_df.iterrows():
        user_id = event['user_id']
        event_time = pd.to_datetime(event['event_timestamp'])

        if user_id not in inspector_activity or event_time > inspector_activity[user_id]:
            inspector_activity[user_id] = event_time

    # Check each material
    material_ids = inventory_df.get('material_id', inventory_df.get('transaction_id', pd.Series(dtype=str)))

    for mat_id in material_ids.unique():
        mat_events = event_logs_df[
            (event_logs_df['transaction_id'] == mat_id) |
            (event_logs_df.get('event_data', pd.Series([{}]*len(event_logs_df))).apply(
                lambda x: x.get('material_id') == mat_id if isinstance(x, dict) else False
            ))
        ].copy()

        if len(mat_events) == 0:
            continue

        # Get material data
        mat_data = inventory_df[material_ids == mat_id]
        if len(mat_data) == 0:
            continue

        mat_data = mat_data.iloc[0]
        stock_value = mat_data.get('amount', 0) or 0
        status = mat_data.get('status', '')

        # Check if in quality inspection
        metadata = mat_data.get('erp_metadata') or {}
        stock_type = metadata.get('stock_type', '') if isinstance(metadata, dict) else ''

        # Ensure event_timestamp is datetime
        mat_events['event_timestamp'] = pd.to_datetime(mat_events['event_timestamp'])

        # Check for quality events
        qa_start_events = mat_events[mat_events['event_type'].str.contains('QUALITY', case=False, na=False)]
        qa_decision_events = mat_events[mat_events['event_type'] == 'QUALITY_DECISION']

        if (stock_type == 'quality_inspection' or status == 'QUALITY_HOLD') and len(qa_decision_events) == 0:
            if len(qa_start_events) > 0:
                qa_start_date = qa_start_events.sort_values('event_timestamp').iloc[-1]['event_timestamp']
                days_in_qa = (now - qa_start_date).days
                assigned_inspector = qa_start_events.iloc[-1]['user_id']
                inspector_last_seen = inspector_activity.get(assigned_inspector, qa_start_date)

                if days_in_qa > 2:  # More than 2 days
                    qa_bottlenecks.append({
                        'material_id': mat_id,
                        'inspection_start_date': qa_start_date,
                        'days_in_qa': days_in_qa,
                        'assigned_inspector': assigned_inspector,
                        'inspector_last_seen': inspector_last_seen,
                        'root_cause_detail': f'QA inspection pending {days_in_qa} days, inspector {assigned_inspector}',
                        'stock_value': stock_value
                    })

    if len(qa_bottlenecks) > 0:
        return pd.DataFrame(qa_bottlenecks)
    else:
        return pd.DataFrame()


def detect_dio_ghost_allocations(
    inventory_df: pd.DataFrame,
    movements_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Find unreleased reservations linked to cancelled orders.

    Detects:
    - STOCK_RESERVED event exists
    - Linked order has ORDER_CANCELLED event
    - No RESERVATION_RELEASED event
    - Stock remains unavailable to system

    Returns DataFrame with columns:
    - material_id
    - reservation_date
    - order_id
    - order_cancelled_date
    - days_stuck
    - stock_quantity_reserved
    - root_cause_detail
    - stock_value
    """

    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()

    ghost_allocations = []
    now = datetime.now()

    # Find all cancelled orders
    cancelled_orders = event_logs_df[event_logs_df['event_type'] == 'ORDER_CANCELLED']
    cancelled_order_ids = set()

    for _, event in cancelled_orders.iterrows():
        event_data = event.get('event_data') or {}
        if isinstance(event_data, dict):
            order_id = event_data.get('order_id')
            if order_id:
                cancelled_order_ids.add(order_id)

    # Find stock reservations linked to cancelled orders
    reservation_events = event_logs_df[event_logs_df['event_type'] == 'STOCK_RESERVED']
    release_events = event_logs_df[event_logs_df['event_type'] == 'RESERVATION_RELEASED']

    for _, res_event in reservation_events.iterrows():
        event_data = res_event.get('event_data') or {}
        if not isinstance(event_data, dict):
            continue

        order_id = event_data.get('order_id')
        material_id = event_data.get('material_id', res_event.get('transaction_id'))

        if order_id in cancelled_order_ids:
            # Check if reservation was released
            material_releases = release_events[
                (release_events['transaction_id'] == material_id) |
                (release_events.get('event_data', pd.Series([{}]*len(release_events))).apply(
                    lambda x: x.get('material_id') == material_id if isinstance(x, dict) else False
                ))
            ]

            if len(material_releases) == 0:
                # Ghost allocation detected!
                res_date = pd.to_datetime(res_event['event_timestamp'])

                # Find order cancellation date
                order_cancel_event = cancelled_orders[
                    cancelled_orders.get('event_data', pd.Series([{}]*len(cancelled_orders))).apply(
                        lambda x: x.get('order_id') == order_id if isinstance(x, dict) else False
                    )
                ]

                cancel_date = pd.to_datetime(order_cancel_event.iloc[0]['event_timestamp']) if len(order_cancel_event) > 0 else res_date
                days_stuck = (now - cancel_date).days

                # Get stock value
                material_ids = inventory_df.get('material_id', inventory_df.get('transaction_id', pd.Series(dtype=str)))
                mat_data = inventory_df[material_ids == material_id]
                stock_value = mat_data.iloc[0].get('amount', 0) if len(mat_data) > 0 else 0
                stock_qty = event_data.get('quantity', 0)

                ghost_allocations.append({
                    'material_id': material_id,
                    'reservation_date': res_date,
                    'order_id': order_id,
                    'order_cancelled_date': cancel_date,
                    'days_stuck': days_stuck,
                    'stock_quantity_reserved': stock_qty,
                    'root_cause_detail': f'Reservation from cancelled order {order_id} not released ({days_stuck} days stuck)',
                    'stock_value': stock_value
                })

    if len(ghost_allocations) > 0:
        return pd.DataFrame(ghost_allocations)
    else:
        return pd.DataFrame()


def identify_dio_obsolescence(
    inventory_df: pd.DataFrame,
    movements_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Find obsolete inventory with no write-off action.

    Detects:
    - No movement events in >180 days
    - Stock value > $10K
    - No WRITE_OFF event or OBSOLESCENCE_REVIEW event

    Returns DataFrame with columns:
    - material_id
    - last_movement_date
    - days_since_movement
    - stock_value
    - last_event_type
    - root_cause_detail
    """

    obsolescence_items = []
    now = datetime.now()

    # Check each material
    material_ids = inventory_df.get('material_id', inventory_df.get('transaction_id', pd.Series(dtype=str)))

    for mat_id in material_ids.unique():
        mat_data = inventory_df[material_ids == mat_id]
        if len(mat_data) == 0:
            continue

        mat_data = mat_data.iloc[0]
        stock_value = mat_data.get('amount', 0) or 0

        # Skip low-value items
        if stock_value < 10000:
            continue

        # Check for movement events
        if event_logs_df is not None and len(event_logs_df) > 0:
            mat_events = event_logs_df[
                (event_logs_df['transaction_id'] == mat_id) |
                (event_logs_df.get('event_data', pd.Series([{}]*len(event_logs_df))).apply(
                    lambda x: x.get('material_id') == mat_id if isinstance(x, dict) else False
                ))
            ].copy()

            if len(mat_events) > 0:
                # Ensure event_timestamp is datetime
                mat_events['event_timestamp'] = pd.to_datetime(mat_events['event_timestamp'])

                # Get last movement event
                movement_events = mat_events[
                    mat_events['event_type'].str.contains('GOODS_ISSUE|TRANSFER|CONSUMPTION', case=False, na=False)
                ]

                if len(movement_events) > 0:
                    last_movement_date = movement_events['event_timestamp'].max()
                else:
                    last_movement_date = mat_events['event_timestamp'].max()

                days_since_movement = (now - last_movement_date).days

                # Check for write-off or obsolescence review events
                writeoff_events = mat_events[
                    mat_events['event_type'].str.contains('WRITE_OFF|OBSOLESCENCE|SCRAP', case=False, na=False)
                ]

                if days_since_movement > 180 and len(writeoff_events) == 0:
                    last_event = mat_events.sort_values('event_timestamp').iloc[-1]

                    obsolescence_items.append({
                        'material_id': mat_id,
                        'last_movement_date': last_movement_date,
                        'days_since_movement': days_since_movement,
                        'stock_value': stock_value,
                        'last_event_type': last_event['event_type'],
                        'root_cause_detail': f'No movement for {days_since_movement} days, ${stock_value:,.0f} trapped in dead inventory'
                    })
            else:
                # No events at all - check transaction date
                txn_date = mat_data.get('transaction_date')
                if txn_date:
                    txn_date = pd.to_datetime(txn_date)
                    days_since_movement = (now - txn_date).days

                    if days_since_movement > 180:
                        obsolescence_items.append({
                            'material_id': mat_id,
                            'last_movement_date': txn_date,
                            'days_since_movement': days_since_movement,
                            'stock_value': stock_value,
                            'last_event_type': 'NONE',
                            'root_cause_detail': f'No events for {days_since_movement} days, ${stock_value:,.0f} potentially obsolete'
                        })
        else:
            # No event logs - use transaction date
            txn_date = mat_data.get('transaction_date')
            if txn_date:
                txn_date = pd.to_datetime(txn_date)
                days_since_movement = (now - txn_date).days

                if days_since_movement > 180:
                    obsolescence_items.append({
                        'material_id': mat_id,
                        'last_movement_date': txn_date,
                        'days_since_movement': days_since_movement,
                        'stock_value': stock_value,
                        'last_event_type': 'NONE',
                        'root_cause_detail': f'No activity for {days_since_movement} days, ${stock_value:,.0f} potentially obsolete'
                    })

    if len(obsolescence_items) > 0:
        return pd.DataFrame(obsolescence_items)
    else:
        return pd.DataFrame()


def synthesize_dio_root_causes(
    inventory_df: pd.DataFrame,
    movements_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Run all DIO analyses and assign definitive root cause to each material.

    Priority order (first match wins):
    1. Sequence inversion → HIGH confidence
    2. Valuation failure → HIGH confidence
    3. Quality bottleneck → HIGH confidence
    4. Ghost allocation → HIGH confidence
    5. Obsolescence → MEDIUM confidence
    6. Rule-based classification → LOW confidence (fallback)

    Returns DataFrame with all transaction fields PLUS:
    - root_cause_type
    - root_cause_confidence (HIGH/MEDIUM/LOW)
    - evidence_source
    - evidence_detail (specific finding with dates/users)
    - fix_type (system/policy/process)
    - fix_owner (IT/Finance/Quality/Procurement)
    - fix_days_estimate
    - recovery_confidence (CERTAIN/PROBABLE/CONTESTED)
    """

    # Import the rule-based classifier for fallback
    from utils.root_cause_classifier_dio import classify_dio_root_causes

    # Initialize result with all inventory items
    result_df = inventory_df.copy()

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
        return classify_dio_root_causes(inventory_df, movements_df if movements_df is not None else pd.DataFrame())

    # Get material ID column
    material_id_col = 'material_id' if 'material_id' in result_df.columns else 'transaction_id'

    # Run all forensic analyses
    inversions_df = detect_dio_sequence_inversions(inventory_df, movements_df if movements_df is not None else pd.DataFrame(), event_logs_df)
    valuation_failures_df = analyze_dio_valuation_failures(inventory_df, event_logs_df)
    qa_bottlenecks_df = analyze_dio_quality_bottlenecks(inventory_df, event_logs_df)
    ghost_allocations_df = detect_dio_ghost_allocations(inventory_df, movements_df if movements_df is not None else pd.DataFrame(), event_logs_df)
    obsolescence_df = identify_dio_obsolescence(inventory_df, movements_df if movements_df is not None else pd.DataFrame(), event_logs_df)

    # PRIORITY 1: Sequence inversions
    if len(inversions_df) > 0:
        for _, inversion in inversions_df.iterrows():
            mat_id = inversion['material_id']
            mask = result_df[material_id_col] == mat_id

            result_df.loc[mask, 'root_cause_type'] = 'sequence_inversion'
            result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
            result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
            result_df.loc[mask, 'evidence_detail'] = f"{inversion['description']} ({inversion['inversion_pattern']})"
            result_df.loc[mask, 'fix_type'] = 'system'
            result_df.loc[mask, 'fix_owner'] = 'IT'
            result_df.loc[mask, 'fix_days_estimate'] = 5
            result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'

    # PRIORITY 2: Valuation failures
    if len(valuation_failures_df) > 0:
        for _, failure in valuation_failures_df.iterrows():
            mat_id = failure['material_id']
            mask = result_df[material_id_col] == mat_id

            if len(result_df[mask]) > 0 and result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                result_df.loc[mask, 'root_cause_type'] = 'received_not_valued'
                result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = failure['root_cause_detail']
                result_df.loc[mask, 'fix_type'] = 'system'
                result_df.loc[mask, 'fix_owner'] = 'Finance'
                result_df.loc[mask, 'fix_days_estimate'] = 7
                result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'

    # PRIORITY 3: Quality bottlenecks
    if len(qa_bottlenecks_df) > 0:
        for _, bottleneck in qa_bottlenecks_df.iterrows():
            mat_id = bottleneck['material_id']
            mask = result_df[material_id_col] == mat_id

            if len(result_df[mask]) > 0 and result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                result_df.loc[mask, 'root_cause_type'] = 'quality_hold_stall'
                result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = bottleneck['root_cause_detail']
                result_df.loc[mask, 'fix_type'] = 'process'
                result_df.loc[mask, 'fix_owner'] = 'Quality'
                result_df.loc[mask, 'fix_days_estimate'] = 2
                result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'

    # PRIORITY 4: Ghost allocations
    if len(ghost_allocations_df) > 0:
        for _, ghost in ghost_allocations_df.iterrows():
            mat_id = ghost['material_id']
            mask = result_df[material_id_col] == mat_id

            if len(result_df[mask]) > 0 and result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                result_df.loc[mask, 'root_cause_type'] = 'ghost_allocation'
                result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = ghost['root_cause_detail']
                result_df.loc[mask, 'fix_type'] = 'system'
                result_df.loc[mask, 'fix_owner'] = 'IT'
                result_df.loc[mask, 'fix_days_estimate'] = 3
                result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'

    # PRIORITY 5: Obsolescence
    if len(obsolescence_df) > 0:
        for _, obs in obsolescence_df.iterrows():
            mat_id = obs['material_id']
            mask = result_df[material_id_col] == mat_id

            if len(result_df[mask]) > 0 and result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                result_df.loc[mask, 'root_cause_type'] = 'obsolete_unwritten'
                result_df.loc[mask, 'root_cause_confidence'] = 'MEDIUM'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = obs['root_cause_detail']
                result_df.loc[mask, 'fix_type'] = 'policy'
                result_df.loc[mask, 'fix_owner'] = 'Finance'
                result_df.loc[mask, 'fix_days_estimate'] = 15
                result_df.loc[mask, 'recovery_confidence'] = 'PROBABLE'

    # PRIORITY 6: Rule-based fallback for remaining items
    unclassified_mask = result_df['root_cause_confidence'] == 'LOW'
    if unclassified_mask.sum() > 0:
        unclassified_items = result_df[unclassified_mask]
        rule_based_results = classify_dio_root_causes(unclassified_items, movements_df if movements_df is not None else pd.DataFrame())

        # Merge rule-based results back
        for col in ['root_cause_type', 'root_cause_confidence', 'evidence_source',
                    'evidence_detail', 'fix_type', 'fix_owner', 'fix_days_estimate', 'recovery_confidence']:
            if col in rule_based_results.columns:
                result_df.loc[unclassified_mask, col] = rule_based_results[col].values

    return result_df
