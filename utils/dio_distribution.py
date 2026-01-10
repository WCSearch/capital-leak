"""
Distribution-Specific DIO Calculator

For distribution companies (no manufacturing/BOMs), uses velocity-based
time benchmarks to identify trapped capital vs recognized losses.

Key differences from manufacturing:
- Fast cycle times (hours to days, not days to months)
- No BOM critical path analysis
- Focus on staging, cross-dock, cycle counts, and velocity metrics

Author: Capital Leak Analysis Team
Date: 2025-01-10
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from decimal import Decimal
import pandas as pd


# Distribution-specific velocity benchmarks (hours/days)
DISTRIBUTION_BENCHMARKS = {
    'receiving_to_putaway': {
        'standard_hours': 24,
        'threshold_hours': 48,  # 2× standard
        'description': 'Time from goods receipt to storage location assignment',
        'recovery_type': 'TRAPPED_CAPITAL'
    },
    'cross_dock_staging': {
        'standard_hours': 4,
        'threshold_hours': 8,
        'description': 'Time items sit in cross-dock staging before ship',
        'recovery_type': 'TRAPPED_CAPITAL'
    },
    'cycle_count_adjustment': {
        'standard_hours': 48,
        'threshold_hours': 96,
        'description': 'Time from count entered to adjustment posted',
        'recovery_type': 'SPLIT'  # Positive = trapped, Negative = loss
    },
    'rtv_approval': {
        'standard_days': 5,
        'threshold_days': 10,
        'description': 'Time from RTV created to vendor approval/rejection',
        'recovery_type': 'PARTIAL_RECOVERY'
    },
    'pick_to_ship': {
        'standard_hours': 8,
        'threshold_hours': 24,
        'description': 'Time from pick released to shipment confirmed',
        'recovery_type': 'TRAPPED_CAPITAL'
    },
    'receiving_to_valuation': {
        'standard_hours': 24,
        'threshold_hours': 72,
        'description': 'Time from receipt to financial valuation posting',
        'recovery_type': 'TRAPPED_CAPITAL'
    },
    'excess_slow_moving': {
        'standard_days': 90,
        'threshold_days': 180,
        'description': 'No movement in extended period',
        'recovery_type': 'PARTIAL_RECOVERY'  # Liquidation value
    }
}

# Distribution DIO issue types mapped to benchmarks
DISTRIBUTION_DIO_ISSUES = {
    'CYCLE_COUNT_VARIANCE_POSITIVE': {
        'benchmark': 'cycle_count_adjustment',
        'recovery_type': 'TRAPPED_CAPITAL',
        'description': 'Physical inventory exceeds system - hidden stock',
        'status_patterns': ['CYCLE_COUNT_VARIANCE', 'COUNT_OVERAGE']
    },
    'CYCLE_COUNT_VARIANCE_NEGATIVE': {
        'benchmark': 'cycle_count_adjustment',
        'recovery_type': 'RECOGNIZED_LOSS',
        'description': 'Physical inventory less than system - shrinkage',
        'status_patterns': ['CYCLE_COUNT_VARIANCE', 'COUNT_SHORTAGE']
    },
    'STAGED_NOT_SHIPPED': {
        'benchmark': 'cross_dock_staging',
        'recovery_type': 'TRAPPED_CAPITAL',
        'description': 'Items staged for cross-dock but not shipped',
        'status_patterns': ['STAGED_CROSSDOCK', 'STAGING_TIMEOUT']
    },
    'RTV_PENDING': {
        'benchmark': 'rtv_approval',
        'recovery_type': 'PARTIAL_RECOVERY',
        'description': 'Return-to-vendor pending approval - may or may not be accepted',
        'status_patterns': ['RTV_PENDING', 'RETURN_AUTHORIZATION']
    },
    'RECEIVED_NOT_VALUED': {
        'benchmark': 'receiving_to_valuation',
        'recovery_type': 'TRAPPED_CAPITAL',
        'description': 'Goods received but valuation not posted',
        'status_patterns': ['RECEIVED_NOT_VALUED', 'VALUATION_PENDING']
    },
    'RECEIVED_NOT_PUTAWAY': {
        'benchmark': 'receiving_to_putaway',
        'recovery_type': 'TRAPPED_CAPITAL',
        'description': 'Goods received but not moved to storage location',
        'status_patterns': ['RECEIVED_NOT_PUTAWAY', 'PUTAWAY_PENDING']
    },
    'PICK_NOT_SHIPPED': {
        'benchmark': 'pick_to_ship',
        'recovery_type': 'TRAPPED_CAPITAL',
        'description': 'Items picked but shipment not confirmed',
        'status_patterns': ['PICKED_NOT_SHIPPED', 'SHIP_PENDING']
    },
    'EXCESS_SLOW_MOVING': {
        'benchmark': 'excess_slow_moving',
        'recovery_type': 'PARTIAL_RECOVERY',
        'description': 'No movement in 180+ days - liquidation required',
        'status_patterns': ['SLOW_MOVING', 'EXCESS', 'OBSOLETE']
    }
}


class DistributionDIOCalculator:
    """Calculate trapped capital for distribution companies using velocity benchmarks"""

    def __init__(self, company_id: str, analysis_date: datetime):
        """
        Initialize calculator

        Args:
            company_id: UUID of the distribution company
            analysis_date: Date of analysis (typically today)
        """
        self.company_id = company_id
        self.analysis_date = analysis_date
        self.transactions = []
        self.results = {}

    def load_transactions(self, transactions: List[Dict]) -> None:
        """Load DIO transactions for analysis"""
        self.transactions = transactions

    def calculate_trapped_capital(self) -> Dict:
        """
        Main calculation entry point
        Returns comprehensive trapped capital analysis
        """
        # Group transactions by issue type
        grouped = self._group_by_issue_type()

        # Calculate for each issue type
        issue_results = {}
        for issue_type, txs in grouped.items():
            if issue_type in DISTRIBUTION_DIO_ISSUES:
                result = self._calculate_issue_type(issue_type, txs)
                issue_results[issue_type] = result

        # Aggregate totals
        summary = self._aggregate_results(issue_results)

        return {
            'company_id': self.company_id,
            'company_type': 'DISTRIBUTION',
            'analysis_date': self.analysis_date.isoformat(),
            'methodology': 'Velocity-based time benchmarks (hours/days)',
            'total_dio_value': summary['total_dio_value'],
            'trapped_capital': summary['trapped_capital'],
            'recognized_losses': summary['recognized_losses'],
            'partial_recovery': summary['partial_recovery'],
            'partial_recovery_amount': summary['partial_recovery_amount'],
            'net_recovery': summary['net_recovery'],
            'recovery_rate': summary['recovery_rate'],
            'issues_breakdown': issue_results,
            'summary': summary
        }

    def _group_by_issue_type(self) -> Dict[str, List[Dict]]:
        """Group transactions by distribution issue type"""
        grouped = {}

        for tx in self.transactions:
            status = tx.get('status', '').upper()
            metadata = tx.get('erp_metadata', {})

            # Determine issue type from status patterns
            issue_type = self._classify_transaction(status, metadata)

            if issue_type:
                if issue_type not in grouped:
                    grouped[issue_type] = []
                grouped[issue_type].append(tx)

        return grouped

    def _classify_transaction(self, status: str, metadata: Dict) -> str:
        """Classify transaction into issue type based on status"""
        # Check metadata first for explicit variance type
        variance_type = metadata.get('variance_type', '').upper()
        if variance_type == 'OVERAGE':
            return 'CYCLE_COUNT_VARIANCE_POSITIVE'
        elif variance_type == 'SHORTAGE':
            return 'CYCLE_COUNT_VARIANCE_NEGATIVE'

        # Check status patterns
        for issue_type, config in DISTRIBUTION_DIO_ISSUES.items():
            patterns = config['status_patterns']
            for pattern in patterns:
                if pattern in status:
                    return issue_type

        # Default classification based on partial status matches
        if 'CYCLE_COUNT' in status or 'COUNT_VARIANCE' in status:
            # Need to check amount sign for positive/negative
            return 'CYCLE_COUNT_VARIANCE_POSITIVE'  # Default to positive
        elif 'STAGED' in status or 'CROSS_DOCK' in status or 'CROSSDOCK' in status:
            return 'STAGED_NOT_SHIPPED'
        elif 'RTV' in status or 'RETURN' in status:
            return 'RTV_PENDING'
        elif 'RECEIVED_NOT_VALUED' in status or 'VALUATION' in status:
            return 'RECEIVED_NOT_VALUED'
        elif 'SLOW' in status or 'EXCESS' in status:
            return 'EXCESS_SLOW_MOVING'

        return None

    def _calculate_issue_type(self, issue_type: str, transactions: List[Dict]) -> Dict:
        """Calculate trapped capital for a specific issue type"""
        issue_config = DISTRIBUTION_DIO_ISSUES[issue_type]
        benchmark_key = issue_config['benchmark']
        benchmark = DISTRIBUTION_BENCHMARKS[benchmark_key]

        trapped = []
        normal = []
        losses = []

        for tx in transactions:
            # Calculate time outstanding
            tx_date = self._parse_date(tx.get('transaction_date'))
            time_outstanding = (self.analysis_date - tx_date) if tx_date else timedelta(0)

            # Determine if excess based on benchmark
            is_excess, excess_time = self._check_excess(
                time_outstanding,
                benchmark
            )

            amount = float(tx.get('amount', 0) or 0)
            outstanding_amount = float(tx.get('outstanding_amount', 0) or amount)

            # Handle cycle count variance split
            if issue_type == 'CYCLE_COUNT_VARIANCE_POSITIVE' and amount > 0:
                category_list = trapped if is_excess else normal
            elif issue_type == 'CYCLE_COUNT_VARIANCE_NEGATIVE' or amount < 0:
                category_list = losses if is_excess else normal
                amount = abs(amount)  # Losses are positive amounts
                outstanding_amount = abs(outstanding_amount)
            else:
                category_list = trapped if is_excess else normal

            item = {
                'transaction': tx,
                'time_outstanding': time_outstanding.total_seconds() / 3600,  # hours
                'excess_time': excess_time,
                'amount': outstanding_amount,
                'category': 'EXCESS' if is_excess else 'NORMAL'
            }

            category_list.append(item)

        # Calculate recovery amounts
        recovery_type = issue_config['recovery_type']
        trapped_amount = sum(t['amount'] for t in trapped)
        loss_amount = sum(l['amount'] for l in losses)
        normal_amount = sum(n['amount'] for n in normal)

        # For partial recovery, estimate recoverable amount
        partial_recovery_amount = 0
        if recovery_type == 'PARTIAL_RECOVERY':
            # Estimate 65% recovery for liquidation scenarios
            recovery_rate = 0.65
            if issue_type == 'RTV_PENDING':
                recovery_rate = 0.50  # 50% vendor acceptance rate
            partial_recovery_amount = trapped_amount * recovery_rate

        return {
            'issue_type': issue_type,
            'description': issue_config['description'],
            'benchmark': benchmark['description'],
            'recovery_type': recovery_type,
            'trapped_capital': trapped_amount if recovery_type == 'TRAPPED_CAPITAL' else 0,
            'recognized_losses': loss_amount,
            'partial_recovery_gross': trapped_amount if recovery_type == 'PARTIAL_RECOVERY' else 0,
            'partial_recovery_net': partial_recovery_amount,
            'normal_operations': normal_amount,
            'trapped_count': len(trapped),
            'loss_count': len(losses),
            'normal_count': len(normal),
            'avg_excess_time_hours': sum(t['excess_time'] for t in trapped) / len(trapped) if trapped else 0,
            'trapped_details': trapped[:100],  # Limit for performance
            'benchmark_standard': self._get_benchmark_standard(benchmark),
            'benchmark_threshold': self._get_benchmark_threshold(benchmark)
        }

    def _check_excess(self, time_outstanding: timedelta, benchmark: Dict) -> Tuple[bool, float]:
        """
        Check if time outstanding exceeds benchmark threshold

        Returns:
            (is_excess, excess_time_in_appropriate_units)
        """
        if 'threshold_hours' in benchmark:
            hours_outstanding = time_outstanding.total_seconds() / 3600
            threshold = benchmark['threshold_hours']
            standard = benchmark['standard_hours']

            is_excess = hours_outstanding > threshold
            excess_time = max(0, hours_outstanding - standard)

            return is_excess, excess_time

        else:  # threshold_days
            days_outstanding = time_outstanding.days
            threshold = benchmark['threshold_days']
            standard = benchmark['standard_days']

            is_excess = days_outstanding > threshold
            excess_time = max(0, days_outstanding - standard)

            return is_excess, excess_time

    def _get_benchmark_standard(self, benchmark: Dict) -> str:
        """Get human-readable benchmark standard"""
        if 'standard_hours' in benchmark:
            return f"{benchmark['standard_hours']} hours"
        else:
            return f"{benchmark['standard_days']} days"

    def _get_benchmark_threshold(self, benchmark: Dict) -> str:
        """Get human-readable benchmark threshold"""
        if 'threshold_hours' in benchmark:
            return f"{benchmark['threshold_hours']} hours"
        else:
            return f"{benchmark['threshold_days']} days"

    def _aggregate_results(self, issue_results: Dict) -> Dict:
        """Aggregate all issue results into summary"""
        total_trapped = sum(r.get('trapped_capital', 0) for r in issue_results.values())
        total_losses = sum(r.get('recognized_losses', 0) for r in issue_results.values())
        total_partial_gross = sum(r.get('partial_recovery_gross', 0) for r in issue_results.values())
        total_partial_net = sum(r.get('partial_recovery_net', 0) for r in issue_results.values())
        total_normal = sum(r.get('normal_operations', 0) for r in issue_results.values())

        total_dio_value = total_trapped + total_losses + total_partial_gross + total_normal
        net_recovery = total_trapped + total_partial_net
        recovery_rate = net_recovery / total_dio_value if total_dio_value > 0 else 0

        return {
            'total_dio_value': total_dio_value,
            'trapped_capital': total_trapped,
            'recognized_losses': total_losses,
            'partial_recovery': total_partial_gross,
            'partial_recovery_amount': total_partial_net,
            'normal_operations': total_normal,
            'net_recovery': net_recovery,
            'recovery_rate': recovery_rate,
            'total_count': sum(
                r.get('trapped_count', 0) + r.get('loss_count', 0) + r.get('normal_count', 0)
                for r in issue_results.values()
            ),
            'trapped_count': sum(r.get('trapped_count', 0) for r in issue_results.values()),
            'loss_count': sum(r.get('loss_count', 0) for r in issue_results.values())
        }

    def _parse_date(self, date_value) -> datetime:
        """Parse date from various formats"""
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                try:
                    return datetime.strptime(date_value, '%Y-%m-%d')
                except:
                    return None
        return None
