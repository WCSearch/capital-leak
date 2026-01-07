"""
Rule-Based Root Cause Classifier - DPO Fallback

Provides rule-based DPO classification when event logs are unavailable.
"""

from datetime import datetime
import pandas as pd

ROOT_CAUSE_DEFINITIONS = {
    'vouchered_not_approved': {
        'fix_type': 'policy',
        'fix_owner': 'Finance',
        'fix_days_estimate': 2,
        'recovery_confidence': 'CERTAIN',
        'description': 'Invoice stuck in approval workflow'
    },
    'variance_hold': {
        'fix_type': 'process',
        'fix_owner': 'Procurement',
        'fix_days_estimate': 7,
        'recovery_confidence': 'CERTAIN',
        'description': 'Price or quantity variance blocking payment'
    },
    'discount_opportunity': {
        'fix_type': 'process',
        'fix_owner': 'AP Team',
        'fix_days_estimate': 1,
        'recovery_confidence': 'CERTAIN',
        'description': 'Early payment discount available'
    },
    'payment_term_excess': {
        'fix_type': 'policy',
        'fix_owner': 'Procurement',
        'fix_days_estimate': 15,
        'recovery_confidence': 'PROBABLE',
        'description': 'Extended payment terms beyond policy'
    },
    'within_terms': {
        'fix_type': 'none',
        'fix_owner': 'None',
        'fix_days_estimate': 0,
        'recovery_confidence': 'CERTAIN',
        'description': 'Normal payment terms'
    }
}

def classify_dpo_root_causes(ap_invoices_df: pd.DataFrame, po_df: pd.DataFrame, gr_df: pd.DataFrame) -> pd.DataFrame:
    """Rule-based DPO classification."""
    
    result_df = ap_invoices_df.copy()
    
    result_df['root_cause_type'] = 'within_terms'
    result_df['root_cause_confidence'] = 'LOW'
    result_df['evidence_source'] = 'rule_based'
    result_df['evidence_detail'] = ''
    result_df['fix_type'] = 'none'
    result_df['fix_owner'] = 'None'
    result_df['fix_days_estimate'] = 0
    result_df['recovery_confidence'] = 'CERTAIN'
    
    for idx, row in result_df.iterrows():
        status = row.get('status', '')
        days_outstanding = row.get('days_outstanding', 0) or 0
        
        # RULE 1: Vouchered not approved
        if status in ['PENDING_APPROVAL', 'PENDING'] and days_outstanding > 30:
            result_df.at[idx, 'root_cause_type'] = 'vouchered_not_approved'
            result_df.at[idx, 'evidence_detail'] = f'Pending approval for {days_outstanding} days'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['vouchered_not_approved']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['vouchered_not_approved']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['vouchered_not_approved']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['vouchered_not_approved']['recovery_confidence']
        
        # RULE 2: Variance hold
        elif 'VARIANCE' in status or 'HOLD' in status:
            result_df.at[idx, 'root_cause_type'] = 'variance_hold'
            result_df.at[idx, 'evidence_detail'] = f'Variance hold for {days_outstanding} days'
            result_df.at[idx, 'fix_type'] = ROOT_CAUSE_DEFINITIONS['variance_hold']['fix_type']
            result_df.at[idx, 'fix_owner'] = ROOT_CAUSE_DEFINITIONS['variance_hold']['fix_owner']
            result_df.at[idx, 'fix_days_estimate'] = ROOT_CAUSE_DEFINITIONS['variance_hold']['fix_days_estimate']
            result_df.at[idx, 'recovery_confidence'] = ROOT_CAUSE_DEFINITIONS['variance_hold']['recovery_confidence']
        
        # RULE 3: Within terms
        else:
            result_df.at[idx, 'evidence_detail'] = f'Within payment terms ({days_outstanding} days)'
    
    return result_df
