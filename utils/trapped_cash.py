"""
Trapped Cash Calculation Module

Calculates trapped cash across CCC components (DSO, DIO, DPO) and prioritizes
targets for surgical working capital analysis.
"""

from datetime import datetime
from typing import Dict, List, Optional


# Default benchmarks (industry standard)
DEFAULT_BENCHMARKS = {
    'dso': 45.0,  # Days Sales Outstanding
    'dio': 40.0,  # Days Inventory Outstanding
    'dpo': 50.0   # Days Payable Outstanding
}

# Recovery rate assumptions
RECOVERY_RATES = {
    'dso': 0.70,  # 70% recovery rate for receivables improvements
    'dio': 0.50,  # 50% recovery rate for inventory improvements
    'dpo': 0.60   # 60% recovery rate for payables improvements
}

# Difficulty factors (higher = more difficult)
DIFFICULTY_FACTORS = {
    'dso': 0.3,  # Moderate difficulty
    'dio': 0.6,  # Higher difficulty
    'dpo': 0.4   # Moderate difficulty
}


def calculate_trapped_cash(
    revenue_annual: float,
    actual_dso: float,
    actual_dio: float,
    actual_dpo: float,
    cogs_percentage: float = 0.73,
    benchmarks: Optional[Dict[str, float]] = None
) -> Dict:
    """
    Calculate trapped cash across all CCC components.

    Args:
        revenue_annual: Annual revenue in dollars
        actual_dso: Current Days Sales Outstanding
        actual_dio: Current Days Inventory Outstanding
        actual_dpo: Current Days Payable Outstanding
        cogs_percentage: COGS as percentage of revenue (default 0.73 = 73%)
        benchmarks: Custom benchmark values (optional)

    Returns:
        Dictionary containing:
        - total_trapped_cash: Total trapped cash across all components
        - total_expected_recovery: Total expected recoverable amount
        - targets: List of targets sorted by priority score
        - benchmarks: Benchmarks used in calculation
    """

    # Use default benchmarks if not provided
    if benchmarks is None:
        benchmarks = DEFAULT_BENCHMARKS.copy()

    # Calculate financial metrics
    cogs = revenue_annual * cogs_percentage
    daily_revenue = revenue_annual / 365
    daily_cogs = cogs / 365

    # Calculate excess/deficit days
    excess_dso = max(0, actual_dso - benchmarks['dso'])
    excess_dio = max(0, actual_dio - benchmarks['dio'])
    deficit_dpo = max(0, benchmarks['dpo'] - actual_dpo)  # Paying too fast

    # Calculate trapped cash by component
    trapped_dso = excess_dso * daily_revenue
    trapped_dio = excess_dio * daily_cogs
    trapped_dpo = deficit_dpo * daily_cogs

    # Calculate expected recovery
    expected_recovery_dso = trapped_dso * RECOVERY_RATES['dso']
    expected_recovery_dio = trapped_dio * RECOVERY_RATES['dio']
    expected_recovery_dpo = trapped_dpo * RECOVERY_RATES['dpo']

    # Calculate priority scores
    # Score = (trapped amount × recovery rate) / (1 + difficulty factor)
    dso_score = expected_recovery_dso / (1 + DIFFICULTY_FACTORS['dso'])
    dio_score = expected_recovery_dio / (1 + DIFFICULTY_FACTORS['dio'])
    dpo_score = expected_recovery_dpo / (1 + DIFFICULTY_FACTORS['dpo'])

    # Create target objects
    targets = [
        {
            'component': 'DSO',
            'trapped': trapped_dso,
            'excess_days': excess_dso,
            'recovery_rate': RECOVERY_RATES['dso'],
            'expected_recovery': expected_recovery_dso,
            'priority_score': dso_score,
            'priority': None  # Will be assigned after sorting
        },
        {
            'component': 'DIO',
            'trapped': trapped_dio,
            'excess_days': excess_dio,
            'recovery_rate': RECOVERY_RATES['dio'],
            'expected_recovery': expected_recovery_dio,
            'priority_score': dio_score,
            'priority': None
        },
        {
            'component': 'DPO',
            'trapped': trapped_dpo,
            'excess_days': deficit_dpo,
            'recovery_rate': RECOVERY_RATES['dpo'],
            'expected_recovery': expected_recovery_dpo,
            'priority_score': dpo_score,
            'priority': None
        }
    ]

    # Sort by priority score (highest first)
    targets.sort(key=lambda x: x['priority_score'], reverse=True)

    # Assign priority labels based on sorted order
    if len(targets) >= 1:
        targets[0]['priority'] = 'HIGH'
    if len(targets) >= 2:
        targets[1]['priority'] = 'MEDIUM'
    if len(targets) >= 3:
        targets[2]['priority'] = 'LOW'

    # Calculate totals
    total_trapped = trapped_dso + trapped_dio + trapped_dpo
    total_expected_recovery = expected_recovery_dso + expected_recovery_dio + expected_recovery_dpo

    return {
        'total_trapped_cash': total_trapped,
        'total_expected_recovery': total_expected_recovery,
        'targets': targets,
        'benchmarks': benchmarks
    }


def save_trapped_cash_analysis(
    supabase_client,
    company_id: str,
    analysis_result: Dict,
    analysis_date: Optional[datetime] = None
) -> Dict:
    """
    Save trapped cash analysis results to the database.

    Args:
        supabase_client: Supabase client instance
        company_id: UUID of the company
        analysis_result: Output from calculate_trapped_cash()
        analysis_date: Date of analysis (defaults to today)

    Returns:
        Inserted record data
    """

    if analysis_date is None:
        analysis_date = datetime.now().date()

    # Find each component in targets
    dso_target = next((t for t in analysis_result['targets'] if t['component'] == 'DSO'), None)
    dio_target = next((t for t in analysis_result['targets'] if t['component'] == 'DIO'), None)
    dpo_target = next((t for t in analysis_result['targets'] if t['component'] == 'DPO'), None)

    # Prepare record
    record = {
        'company_id': company_id,
        'analysis_date': analysis_date.isoformat(),
        'total_trapped_cash': float(analysis_result['total_trapped_cash']),
        'total_expected_recovery': float(analysis_result['total_expected_recovery']),

        # DSO
        'dso_trapped_cash': float(dso_target['trapped']) if dso_target else 0.0,
        'dso_excess_days': float(dso_target['excess_days']) if dso_target else 0.0,
        'dso_expected_recovery': float(dso_target['expected_recovery']) if dso_target else 0.0,
        'dso_priority': dso_target['priority'] if dso_target else 'LOW',
        'dso_priority_score': float(dso_target['priority_score']) if dso_target else 0.0,

        # DIO
        'dio_trapped_cash': float(dio_target['trapped']) if dio_target else 0.0,
        'dio_excess_days': float(dio_target['excess_days']) if dio_target else 0.0,
        'dio_expected_recovery': float(dio_target['expected_recovery']) if dio_target else 0.0,
        'dio_priority': dio_target['priority'] if dio_target else 'LOW',
        'dio_priority_score': float(dio_target['priority_score']) if dio_target else 0.0,

        # DPO
        'dpo_trapped_cash': float(dpo_target['trapped']) if dpo_target else 0.0,
        'dpo_deficit_days': float(dpo_target['excess_days']) if dpo_target else 0.0,
        'dpo_expected_recovery': float(dpo_target['expected_recovery']) if dpo_target else 0.0,
        'dpo_priority': dpo_target['priority'] if dpo_target else 'LOW',
        'dpo_priority_score': float(dpo_target['priority_score']) if dpo_target else 0.0,

        # Benchmarks
        'benchmark_dso': float(analysis_result['benchmarks']['dso']),
        'benchmark_dio': float(analysis_result['benchmarks']['dio']),
        'benchmark_dpo': float(analysis_result['benchmarks']['dpo'])
    }

    # Insert into database
    response = supabase_client.table('trapped_cash_analysis').insert(record).execute()

    return response.data[0] if response.data else None


def get_latest_trapped_cash_analysis(supabase_client, company_id: str) -> Optional[Dict]:
    """
    Retrieve the most recent trapped cash analysis for a company.

    Args:
        supabase_client: Supabase client instance
        company_id: UUID of the company

    Returns:
        Latest analysis record or None if not found
    """

    response = supabase_client.table('trapped_cash_analysis') \
        .select('*') \
        .eq('company_id', company_id) \
        .order('analysis_date', desc=True) \
        .limit(1) \
        .execute()

    if response.data and len(response.data) > 0:
        return response.data[0]

    return None


def calculate_surgical_target(
    supabase_client,
    company_id: str,
    component_type: str
) -> Optional[Dict]:
    """
    Identify the surgical target (highest impact functional area) for a component.

    Args:
        supabase_client: Supabase client instance
        company_id: UUID of the company
        component_type: 'DSO', 'DIO', or 'DPO'

    Returns:
        Dictionary with surgical target details or None
    """

    # Get component details for this component type
    response = supabase_client.table('component_details') \
        .select('*') \
        .eq('company_id', company_id) \
        .eq('component_type', component_type) \
        .order('amount', desc=True) \
        .execute()

    if not response.data or len(response.data) == 0:
        return None

    # The surgical target is the functional area with the highest amount
    surgical_target = response.data[0]

    # Get transaction count and average days for this functional area
    trans_response = supabase_client.table('transactions') \
        .select('transaction_id, days_outstanding, amount') \
        .eq('company_id', company_id) \
        .eq('gl_account', surgical_target['gl_account']) \
        .execute()

    transaction_count = len(trans_response.data) if trans_response.data else 0
    avg_days = 0
    if trans_response.data and len(trans_response.data) > 0:
        total_days = sum(t.get('days_outstanding', 0) or 0 for t in trans_response.data)
        avg_days = total_days / transaction_count if transaction_count > 0 else 0

    return {
        'functional_area': surgical_target['functional_area'],
        'gl_account': surgical_target['gl_account'],
        'gl_account_name': surgical_target['gl_account_name'],
        'amount': surgical_target['amount'],
        'days_contribution': surgical_target['days_contribution'],
        'transaction_count': transaction_count,
        'avg_days_outstanding': avg_days
    }


def format_currency(amount: float) -> str:
    """Format amount as USD currency."""
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.1f}K"
    else:
        return f"${amount:.0f}"


def format_percentage(rate: float) -> str:
    """Format rate as percentage."""
    return f"{rate*100:.0f}%"
