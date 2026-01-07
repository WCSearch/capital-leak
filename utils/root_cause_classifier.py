"""
Rule-Based Root Cause Classifier - Phase 1 Fallback

This module provides rule-based classification using only transaction fields
when event logs are not available. It maintains the same output schema as
the event log analyzer but with lower confidence levels.

Classification rules (priority order):
1. fulfilled_not_invoiced: has delivery_date, billing_date > delivery_date + 7 days
2. credit_hold_lag: credit_hold=True, days_outstanding > 30
3. pricing_dispute: dispute_flag=True, days_outstanding > 15
4. payment_term_exception: payment_terms_days > 60, past due
5. late_payer_behavioral: days_outstanding > 90, no other flags
6. collections_needed: days_outstanding > 60, no other flags
7. within_terms: everything else
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np


# Root cause definitions with fix metadata
ROOT_CAUSE_DEFINITIONS = {
    'fulfilled_not_invoiced': {
        'fix_type': 'system',
        'fix_owner': 'IT',
        'fix_days_estimate': 5,
        'recovery_confidence': 'CERTAIN',
        'description': 'Delivery completed but invoice not generated'
    },
    'credit_hold_lag': {
        'fix_type': 'policy',
        'fix_owner': 'Finance',
        'fix_days_estimate': 2,
        'recovery_confidence': 'CERTAIN',
        'description': 'Credit hold applied but never reviewed'
    },
    'pricing_dispute': {
        'fix_type': 'master_data',
        'fix_owner': 'Finance',
        'fix_days_estimate': 10,
        'recovery_confidence': 'PROBABLE',
        'description': 'Customer disputes pricing or terms'
    },
    'payment_term_exception': {
        'fix_type': 'policy',
        'fix_owner': 'Sales',
        'fix_days_estimate': 15,
        'recovery_confidence': 'PROBABLE',
        'description': 'Non-standard payment terms granted'
    },
    'paid_unapplied': {
        'fix_type': 'process',
        'fix_owner': 'AR Team',
        'fix_days_estimate': 3,
        'recovery_confidence': 'CERTAIN',
        'description': 'Payment received but not applied to invoice'
    },
    'invoice_release_lag': {
        'fix_type': 'process',
        'fix_owner': 'AR Team',
        'fix_days_estimate': 1,
        'recovery_confidence': 'PROBABLE',
        'description': 'Invoice created but not released to customer'
    },
    'late_payer_behavioral': {
        'fix_type': 'behavioral',
        'fix_owner': 'Collections',
        'fix_days_estimate': 60,
        'recovery_confidence': 'CONTESTED',
        'description': 'Customer consistently pays late'
    },
    'collections_needed': {
        'fix_type': 'behavioral',
        'fix_owner': 'Collections',
        'fix_days_estimate': 30,
        'recovery_confidence': 'CONTESTED',
        'description': 'Past due, collections action required'
    },
    'within_terms': {
        'fix_type': 'none',
        'fix_owner': 'None',
        'fix_days_estimate': 0,
        'recovery_confidence': 'CERTAIN',
        'description': 'Transaction within payment terms'
    }
}


def classify_root_causes(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Rule-based classification using only transaction fields (no event logs).

    Classification rules (priority order):
    1. fulfilled_not_invoiced: has_delivery=True, billing_date > delivery_date + 7 days
    2. credit_hold_lag: credit_hold=True, days_outstanding > 30
    3. pricing_dispute: dispute_flag=True, days_outstanding > 15
    4. payment_term_exception: payment_terms_days > 60, past due
    5. late_payer_behavioral: days_outstanding > 90, no other flags
    6. collections_needed: days_outstanding > 60, no other flags
    7. within_terms: everything else

    Returns DataFrame with same structure as event log analyzer
    (but with root_cause_confidence='LOW' and evidence_source='rule_based')
    """

    result_df = transactions_df.copy()

    # Initialize result columns
    result_df['root_cause_type'] = 'within_terms'
    result_df['root_cause_confidence'] = 'LOW'
    result_df['evidence_source'] = 'rule_based'
    result_df['evidence_detail'] = ''
    result_df['fix_type'] = 'none'
    result_df['fix_owner'] = 'None'
    result_df['fix_days_estimate'] = 0
    result_df['recovery_confidence'] = 'CERTAIN'

    # Extract metadata fields (stored in erp_metadata JSONB)
    # Handle both dict and NaN values
    def safe_get_metadata(row, key, default=None):
        metadata = row.get('erp_metadata')
        if pd.isna(metadata) or metadata is None:
            return default
        if isinstance(metadata, dict):
            return metadata.get(key, default)
        return default

    # RULE 1: Fulfilled but not invoiced
    # Check for delivery_date in metadata and compare to transaction_date
    for idx, row in result_df.iterrows():
        metadata = row.get('erp_metadata') or {}
        delivery_date = metadata.get('delivery_date') if isinstance(metadata, dict) else None
        transaction_date = row.get('transaction_date')

        if delivery_date and transaction_date:
            # Convert to datetime if needed
            if isinstance(delivery_date, str):
                delivery_date = pd.to_datetime(delivery_date)
            if isinstance(transaction_date, str):
                transaction_date = pd.to_datetime(transaction_date)

            # Check if invoice came >7 days after delivery
            if pd.notna(delivery_date) and pd.notna(transaction_date):
                days_diff = (transaction_date - delivery_date).days
                if days_diff > 7:
                    result_df.at[idx, 'root_cause_type'] = 'fulfilled_not_invoiced'
                    result_df.at[idx, 'evidence_detail'] = f'Invoice created {days_diff} days after delivery'
                    result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['fulfilled_not_invoiced']['fix_type']
                    result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['fulfilled_not_invoiced']['fix_owner']
                    result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['fulfilled_not_invoiced']['fix_days_estimate']
                    result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['fulfilled_not_invoiced']['recovery_confidence']

    # RULE 2: Credit hold lag
    # Check for credit_hold flag and days outstanding
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'within_terms':
            continue

        metadata = row.get('erp_metadata') or {}
        credit_hold = metadata.get('credit_hold', False) if isinstance(metadata, dict) else False
        status = row.get('status', '')
        days_outstanding = row.get('days_outstanding', 0)

        if (credit_hold or status == 'CREDIT_HOLD') and days_outstanding > 30:
            result_df.at[idx, 'root_cause_type'] = 'credit_hold_lag'
            result_df.at[idx, 'evidence_detail'] = f'Credit hold for {days_outstanding} days with no review'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['credit_hold_lag']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['credit_hold_lag']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['credit_hold_lag']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['credit_hold_lag']['recovery_confidence']

    # RULE 3: Pricing disputes
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'within_terms':
            continue

        metadata = row.get('erp_metadata') or {}
        dispute_flag = metadata.get('dispute_flag', False) if isinstance(metadata, dict) else False
        status = row.get('status', '')
        days_outstanding = row.get('days_outstanding', 0)

        if (dispute_flag or status == 'DISPUTED') and days_outstanding > 15:
            dispute_reason = metadata.get('dispute_reason', 'Unknown') if isinstance(metadata, dict) else 'Unknown'
            result_df.at[idx, 'root_cause_type'] = 'pricing_dispute'
            result_df.at[idx, 'evidence_detail'] = f'Disputed for {days_outstanding} days (Reason: {dispute_reason})'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['pricing_dispute']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['pricing_dispute']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['pricing_dispute']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['pricing_dispute']['recovery_confidence']

    # RULE 4: Check for invoiced but not sent
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'within_terms':
            continue

        status = row.get('status', '')
        transaction_date = row.get('transaction_date')

        if status in ['CREATED', 'PENDING_SEND', 'PENDING'] and transaction_date:
            # Calculate days since creation
            if isinstance(transaction_date, str):
                transaction_date = pd.to_datetime(transaction_date)

            days_since_creation = (datetime.now() - transaction_date).days if pd.notna(transaction_date) else 0

            if days_since_creation > 3:
                result_df.at[idx, 'root_cause_type'] = 'invoice_release_lag'
                result_df.at[idx, 'evidence_detail'] = f'Invoice created {days_since_creation} days ago but not sent'
                result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['invoice_release_lag']['fix_type']
                result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['invoice_release_lag']['fix_owner']
                result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['invoice_release_lag']['fix_days_estimate']
                result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['invoice_release_lag']['recovery_confidence']

    # RULE 5: Payment term exceptions
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'within_terms':
            continue

        metadata = row.get('erp_metadata') or {}
        payment_terms_days = metadata.get('payment_terms_days', 30) if isinstance(metadata, dict) else 30
        days_outstanding = row.get('days_outstanding', 0)

        if payment_terms_days > 60 and days_outstanding > 0:
            result_df.at[idx, 'root_cause_type'] = 'payment_term_exception'
            result_df.at[idx, 'evidence_detail'] = f'Non-standard payment terms ({payment_terms_days} days) granted'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['payment_term_exception']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['payment_term_exception']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['payment_term_exception']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['payment_term_exception']['recovery_confidence']

    # RULE 6: Late payer (behavioral)
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'within_terms':
            continue

        days_outstanding = row.get('days_outstanding', 0)

        if days_outstanding > 90:
            result_df.at[idx, 'root_cause_type'] = 'late_payer_behavioral'
            result_df.at[idx, 'evidence_detail'] = f'Past due {days_outstanding} days, no systemic issues detected'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['late_payer_behavioral']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['late_payer_behavioral']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['late_payer_behavioral']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['late_payer_behavioral']['recovery_confidence']

    # RULE 7: Collections needed (moderately past due)
    for idx, row in result_df.iterrows():
        # Skip if already classified
        if result_df.at[idx, 'root_cause_type'] != 'within_terms':
            continue

        days_outstanding = row.get('days_outstanding', 0)

        if days_outstanding > 60:
            result_df.at[idx, 'root_cause_type'] = 'collections_needed'
            result_df.at[idx, 'evidence_detail'] = f'Past due {days_outstanding} days'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['collections_needed']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['collections_needed']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['collections_needed']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['collections_needed']['recovery_confidence']

    # RULE 8: Within terms (default)
    # Already set as default, so no additional logic needed
    for idx, row in result_df.iterrows():
        if result_df.at[idx, 'root_cause_type'] == 'within_terms':
            days_outstanding = row.get('days_outstanding', 0)
            result_df.at[idx, 'evidence_detail'] = f'Within payment terms ({days_outstanding} days outstanding)'

    return result_df


def get_root_cause_summary(classified_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate classified transactions by root cause type for dashboard display.

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
