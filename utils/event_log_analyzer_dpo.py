"""
Event Log Analysis Module - DPO Forensics

This module provides event-level forensics for Days Payable Outstanding (DPO),
identifying root causes of payable delays through ERP event log analysis.

Key capabilities:
1. Sequence inversions (payment before invoice, etc.)
2. Approval bottlenecks (stuck approvals, departed approvers)
3. Variance holds (price/quantity mismatches)
4. Discount risks (expiring discount opportunities)
5. Duplicate detection (potential duplicate payments)
6. Root cause synthesis (definitive attribution with evidence)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


# Valid event sequences for AP workflows
VALID_SEQUENCES = {
    'purchase_to_pay': [
        'PURCHASE_ORDER',
        'GOODS_RECEIPT',
        'INVOICE_RECEIVED',
        'INVOICE_APPROVED',
        'PAYMENT_MADE'
    ]
}

# Inversion patterns for AP
INVERSION_PATTERNS = {
    'payment_before_approval': {
        'prerequisite': 'INVOICE_APPROVED',
        'dependent': 'PAYMENT_MADE',
        'severity': 'HIGH',
        'description': 'Payment made before invoice approval'
    },
    'invoice_before_receipt': {
        'prerequisite': 'GOODS_RECEIPT',
        'dependent': 'INVOICE_RECEIVED',
        'severity': 'MEDIUM',
        'description': 'Invoice received before goods receipt'
    }
}


def detect_dpo_sequence_inversions(
    ap_invoices_df: pd.DataFrame,
    po_df: pd.DataFrame,
    gr_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """Detect DPO event inversions."""
    
    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()
    
    inversions = []
    
    for inv_id in ap_invoices_df['transaction_id'].unique():
        inv_events = event_logs_df[event_logs_df['transaction_id'] == inv_id].copy()
        
        if len(inv_events) == 0:
            continue
            
        inv_amount = ap_invoices_df[ap_invoices_df['transaction_id'] == inv_id]['amount'].iloc[0]
        inv_events['event_timestamp'] = pd.to_datetime(inv_events['event_timestamp'])
        
        event_lookup = {}
        for _, event in inv_events.iterrows():
            event_type = event['event_type']
            if event_type not in event_lookup:
                event_lookup[event_type] = event
        
        for pattern_name, pattern_def in INVERSION_PATTERNS.items():
            prereq = pattern_def['prerequisite']
            dependent = pattern_def['dependent']
            
            if prereq in event_lookup and dependent in event_lookup:
                prereq_event = event_lookup[prereq]
                dependent_event = event_lookup[dependent]
                
                prereq_time = prereq_event['event_timestamp']
                dependent_time = dependent_event['event_timestamp']
                
                if dependent_time < prereq_time:
                    time_gap_seconds = (prereq_time - dependent_time).total_seconds()
                    
                    inversions.append({
                        'transaction_id': inv_id,
                        'inversion_pattern': pattern_name,
                        'prerequisite_event': prereq,
                        'dependent_event': dependent,
                        'time_gap_seconds': -time_gap_seconds,
                        'first_occurrence_date': dependent_time,
                        'user_id': dependent_event['user_id'],
                        'module': dependent_event['module'],
                        'transaction_amount': inv_amount,
                        'severity': pattern_def['severity'],
                        'description': pattern_def['description']
                    })
    
    return pd.DataFrame(inversions) if len(inversions) > 0 else pd.DataFrame()


def analyze_dpo_approval_bottlenecks(
    ap_invoices_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """Find vouchered-not-approved cases with workflow details."""
    
    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()
    
    bottlenecks = []
    now = datetime.now()
    
    approver_activity = {}
    for _, event in event_logs_df.iterrows():
        user_id = event['user_id']
        event_time = pd.to_datetime(event['event_timestamp'])
        
        if user_id not in approver_activity or event_time > approver_activity[user_id]:
            approver_activity[user_id] = event_time
    
    for inv_id in ap_invoices_df['transaction_id'].unique():
        inv_events = event_logs_df[event_logs_df['transaction_id'] == inv_id].copy()
        
        if len(inv_events) == 0:
            continue
        
        inv_data = ap_invoices_df[ap_invoices_df['transaction_id'] == inv_id].iloc[0]
        inv_amount = inv_data['amount']
        
        inv_events['event_timestamp'] = pd.to_datetime(inv_events['event_timestamp'])
        
        approval_events = inv_events[
            inv_events['event_type'].str.contains('APPROVAL|WORKFLOW', case=False, na=False)
        ]
        
        if len(approval_events) == 0:
            continue
        
        last_approval = approval_events.sort_values('event_timestamp').iloc[-1]
        last_activity_date = last_approval['event_timestamp']
        days_stuck = (now - last_activity_date).days
        
        if days_stuck > 30:
            assigned_approver = last_approval['user_id']
            approver_last_seen = approver_activity.get(assigned_approver, last_activity_date)
            days_since_approver_active = (now - approver_last_seen).days
            
            if days_since_approver_active > 90:
                bottlenecks.append({
                    'transaction_id': inv_id,
                    'workflow_status': 'reassignment_needed',
                    'assigned_approver_id': assigned_approver,
                    'days_stuck': days_stuck,
                    'last_activity_date': last_activity_date,
                    'approver_last_seen_date': approver_last_seen,
                    'root_cause': f'Approver {assigned_approver} left company, workflow not reassigned',
                    'transaction_amount': inv_amount
                })
            else:
                bottlenecks.append({
                    'transaction_id': inv_id,
                    'workflow_status': 'stuck',
                    'assigned_approver_id': assigned_approver,
                    'days_stuck': days_stuck,
                    'last_activity_date': last_activity_date,
                    'approver_last_seen_date': approver_last_seen,
                    'root_cause': f'Approval pending >{days_stuck} days',
                    'transaction_amount': inv_amount
                })
    
    return pd.DataFrame(bottlenecks) if len(bottlenecks) > 0 else pd.DataFrame()


def analyze_dpo_variance_holds(
    ap_invoices_df: pd.DataFrame,
    po_df: pd.DataFrame,
    gr_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """Find variance-hold cases with mismatch details."""
    
    if event_logs_df is None or len(event_logs_df) == 0:
        return pd.DataFrame()
    
    variances = []
    now = datetime.now()
    
    for inv_id in ap_invoices_df['transaction_id'].unique():
        inv_events = event_logs_df[event_logs_df['transaction_id'] == inv_id].copy()
        
        if len(inv_events) == 0:
            continue
        
        inv_data = ap_invoices_df[ap_invoices_df['transaction_id'] == inv_id].iloc[0]
        inv_amount = inv_data['amount']
        
        inv_events['event_timestamp'] = pd.to_datetime(inv_events['event_timestamp'])
        
        variance_events = inv_events[inv_events['event_type'] == 'VARIANCE_DETECTED']
        variance_resolved_events = inv_events[inv_events['event_type'] == 'VARIANCE_RESOLVED']
        
        if len(variance_events) > 0 and len(variance_resolved_events) == 0:
            variance_date = variance_events.iloc[-1]['event_timestamp']
            days_stuck = (now - variance_date).days
            
            if days_stuck > 15:
                variances.append({
                    'transaction_id': inv_id,
                    'variance_detected_date': variance_date,
                    'days_stuck': days_stuck,
                    'root_cause_detail': f'Price/quantity variance unresolved for {days_stuck} days',
                    'transaction_amount': inv_amount
                })
    
    return pd.DataFrame(variances) if len(variances) > 0 else pd.DataFrame()


def detect_dpo_discount_risks(
    ap_invoices_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """Find invoices approaching discount deadline."""
    
    discount_risks = []
    now = datetime.now()
    
    for _, inv in ap_invoices_df.iterrows():
        metadata = inv.get('erp_metadata') or {}
        if isinstance(metadata, dict):
            discount_days = metadata.get('discount_days', 0)
            discount_percent = metadata.get('discount_percent', 0)
            
            if discount_days > 0 and discount_percent > 0:
                inv_date = pd.to_datetime(inv.get('transaction_date'))
                discount_deadline = inv_date + timedelta(days=discount_days)
                days_remaining = (discount_deadline - now).days
                
                if 0 < days_remaining <= 5:
                    discount_risks.append({
                        'transaction_id': inv['transaction_id'],
                        'discount_deadline': discount_deadline,
                        'days_remaining': days_remaining,
                        'discount_percent': discount_percent,
                        'potential_savings': inv['amount'] * (discount_percent / 100),
                        'root_cause_detail': f'Discount opportunity expires in {days_remaining} days ({discount_percent}% on ${inv["amount"]:,.0f})',
                        'transaction_amount': inv['amount']
                    })
    
    return pd.DataFrame(discount_risks) if len(discount_risks) > 0 else pd.DataFrame()


def identify_dpo_duplicates(
    ap_invoices_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """Find potential duplicate invoices."""
    
    duplicates = []
    
    # Group by vendor and look for similar amounts
    for vendor in ap_invoices_df['customer_vendor'].unique():
        vendor_invoices = ap_invoices_df[ap_invoices_df['customer_vendor'] == vendor]
        
        # Look for invoices with same amount posted within 30 days
        for _, inv1 in vendor_invoices.iterrows():
            similar = vendor_invoices[
                (vendor_invoices['amount'] == inv1['amount']) &
                (vendor_invoices['transaction_id'] != inv1['transaction_id'])
            ]
            
            for _, inv2 in similar.iterrows():
                date1 = pd.to_datetime(inv1['transaction_date'])
                date2 = pd.to_datetime(inv2['transaction_date'])
                days_apart = abs((date2 - date1).days)
                
                if days_apart <= 30:
                    duplicates.append({
                        'transaction_id': inv1['transaction_id'],
                        'duplicate_transaction_id': inv2['transaction_id'],
                        'vendor': vendor,
                        'amount': inv1['amount'],
                        'days_apart': days_apart,
                        'root_cause_detail': f'Possible duplicate of invoice {inv2["transaction_number"]} (same amount, {days_apart} days apart)',
                        'transaction_amount': inv1['amount']
                    })
                    break  # Only flag once per invoice
    
    return pd.DataFrame(duplicates) if len(duplicates) > 0 else pd.DataFrame()


def synthesize_dpo_root_causes(
    ap_invoices_df: pd.DataFrame,
    po_df: pd.DataFrame,
    gr_df: pd.DataFrame,
    event_logs_df: pd.DataFrame
) -> pd.DataFrame:
    """Master DPO function - assign root cause to each AP invoice with evidence."""
    
    from utils.root_cause_classifier_dpo import classify_dpo_root_causes
    
    result_df = ap_invoices_df.copy()
    
    result_df['root_cause_type'] = 'unknown'
    result_df['root_cause_confidence'] = 'LOW'
    result_df['evidence_source'] = 'rule_based'
    result_df['evidence_detail'] = ''
    result_df['fix_type'] = 'manual_review'
    result_df['fix_owner'] = 'Finance'
    result_df['fix_days_estimate'] = None
    result_df['recovery_confidence'] = 'CONTESTED'
    
    if event_logs_df is None or len(event_logs_df) == 0:
        return classify_dpo_root_causes(ap_invoices_df, po_df, gr_df)
    
    # Run all forensic analyses
    inversions_df = detect_dpo_sequence_inversions(ap_invoices_df, po_df, gr_df, event_logs_df)
    bottlenecks_df = analyze_dpo_approval_bottlenecks(ap_invoices_df, event_logs_df)
    variances_df = analyze_dpo_variance_holds(ap_invoices_df, po_df, gr_df, event_logs_df)
    discount_risks_df = detect_dpo_discount_risks(ap_invoices_df, event_logs_df)
    duplicates_df = identify_dpo_duplicates(ap_invoices_df, event_logs_df)
    
    # PRIORITY 1: Sequence inversions
    if len(inversions_df) > 0:
        for _, inversion in inversions_df.iterrows():
            txn_id = inversion['transaction_id']
            mask = result_df['transaction_id'] == txn_id
            
            result_df.loc[mask, 'root_cause_type'] = 'sequence_inversion'
            result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
            result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
            result_df.loc[mask, 'evidence_detail'] = f"{inversion['description']}"
            result_df.loc[mask, 'fix_type'] = 'system'
            result_df.loc[mask, 'fix_owner'] = 'IT'
            result_df.loc[mask, 'fix_days_estimate'] = 5
            result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'
    
    # PRIORITY 2: Approval bottlenecks
    if len(bottlenecks_df) > 0:
        for _, bottleneck in bottlenecks_df.iterrows():
            txn_id = bottleneck['transaction_id']
            mask = result_df['transaction_id'] == txn_id
            
            if len(result_df[mask]) > 0 and result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                result_df.loc[mask, 'root_cause_type'] = 'approval_bottleneck'
                result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = bottleneck['root_cause']
                result_df.loc[mask, 'fix_type'] = 'policy'
                result_df.loc[mask, 'fix_owner'] = 'Finance'
                result_df.loc[mask, 'fix_days_estimate'] = 2
                result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'
    
    # PRIORITY 3: Variance holds
    if len(variances_df) > 0:
        for _, variance in variances_df.iterrows():
            txn_id = variance['transaction_id']
            mask = result_df['transaction_id'] == txn_id
            
            if len(result_df[mask]) > 0 and result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                result_df.loc[mask, 'root_cause_type'] = 'variance_hold'
                result_df.loc[mask, 'root_cause_confidence'] = 'HIGH'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = variance['root_cause_detail']
                result_df.loc[mask, 'fix_type'] = 'process'
                result_df.loc[mask, 'fix_owner'] = 'Procurement'
                result_df.loc[mask, 'fix_days_estimate'] = 7
                result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'
    
    # PRIORITY 4: Discount risks
    if len(discount_risks_df) > 0:
        for _, discount in discount_risks_df.iterrows():
            txn_id = discount['transaction_id']
            mask = result_df['transaction_id'] == txn_id
            
            if len(result_df[mask]) > 0 and result_df.loc[mask, 'root_cause_confidence'].iloc[0] == 'LOW':
                result_df.loc[mask, 'root_cause_type'] = 'discount_risk'
                result_df.loc[mask, 'root_cause_confidence'] = 'MEDIUM'
                result_df.loc[mask, 'evidence_source'] = 'event_log_pattern'
                result_df.loc[mask, 'evidence_detail'] = discount['root_cause_detail']
                result_df.loc[mask, 'fix_type'] = 'process'
                result_df.loc[mask, 'fix_owner'] = 'AP Team'
                result_df.loc[mask, 'fix_days_estimate'] = 1
                result_df.loc[mask, 'recovery_confidence'] = 'CERTAIN'
    
    # Rule-based fallback
    unclassified_mask = result_df['root_cause_confidence'] == 'LOW'
    if unclassified_mask.sum() > 0:
        unclassified_items = result_df[unclassified_mask]
        rule_based_results = classify_dpo_root_causes(unclassified_items, po_df, gr_df)
        
        for col in ['root_cause_type', 'root_cause_confidence', 'evidence_source',
                    'evidence_detail', 'fix_type', 'fix_owner', 'fix_days_estimate', 'recovery_confidence']:
            if col in rule_based_results.columns:
                result_df.loc[unclassified_mask, col] = rule_based_results[col].values
    
    return result_df
