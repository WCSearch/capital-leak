"""
Manufacturing QA delay analysis.

Tracks work orders and operations placed on QA hold, quantifies the
cash impact of WIP sitting idle during inspection/rework decisions.

QA holds cause cash to be trapped in WIP while inspection/rework
decisions are made. Unlike other bottlenecks where work is actively
progressing, QA holds are completely idle time.

Cash impact:
1. Carrying cost: WIP value × Days on hold × (WACC/365)
2. Throughput impact: Delayed completion → delayed revenue

Preventability analysis:
- Recurring holds on same operation → Process issue (preventable)
- Random holds across different operations → Normal QA (not preventable)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class QADelay:
    """Represents a QA hold event"""
    work_order_id: str
    operation_seq: int
    qa_hold_start_date: Optional[datetime]
    qa_hold_release_date: Optional[datetime]
    days_on_hold: int
    quantity_on_hold: float
    unit_wip_cost: float
    wip_value: float
    hold_reason: str
    carrying_cost: float
    throughput_impact: float
    total_cash_impact: float
    preventable: bool


class QADelayAnalyzer:
    """
    Analyzes QA hold delays in manufacturing.

    QA holds cause cash to be trapped in WIP while inspection/
    rework decisions are made. Unlike other bottlenecks where
    work is actively progressing, QA holds are completely idle time.

    Adapted to work with existing WCSearch database:
    - Uses transactions table with DIO component_type
    - Identifies QA holds from status or erp_metadata
    - Extracts hold duration from days_outstanding
    """

    def __init__(self, db_client, wacc: float = 0.12):
        """
        Initialize analyzer with database client.

        Args:
            db_client: Supabase client
            wacc: Weighted average cost of capital (default 12%)
        """
        self.db = db_client
        self.wacc = wacc

    def analyze(self, company_id: str) -> Dict:
        """
        Main QA delay analysis.

        Identifies work orders on QA hold, calculates hold duration
        and cash impact.

        Args:
            company_id: UUID of company

        Returns:
            dict with:
            - qa_delays: List of QADelay objects
            - summary: Aggregated totals
        """
        logger.info(f"Starting QA delay analysis for company {company_id}")

        qa_delays = []

        try:
            # Query DIO transactions with QA hold indicators
            response = self.db.table('transactions').select(
                'transaction_id, transaction_number, days_outstanding, '
                'outstanding_amount, erp_metadata, status'
            ).eq('company_id', company_id).eq('component_type', 'DIO').execute()

            if not response.data:
                logger.warning(f"No DIO transactions found for company {company_id}")
                return {
                    'qa_delays': [],
                    'summary': self._empty_summary()
                }

            # Analyze each transaction for QA hold
            for record in response.data:
                metadata = record.get('erp_metadata', {})
                status = record.get('status', '').upper()

                # Check if this is a QA hold
                if not self._is_qa_hold(status, metadata):
                    continue

                # Analyze QA delay
                qa_delay = self._analyze_qa_hold(record, metadata)
                if qa_delay:
                    qa_delays.append(qa_delay)

        except Exception as e:
            logger.error(f"Error analyzing QA delays: {e}")

        # Sort by cash impact
        qa_delays.sort(key=lambda x: x.total_cash_impact, reverse=True)

        # Calculate summary
        summary = self._calculate_summary(qa_delays)

        logger.info(
            f"QA delay analysis complete: {len(qa_delays)} holds found, "
            f"${summary['total_cash_impact']:,.0f} total impact"
        )

        return {
            'qa_delays': qa_delays,
            'summary': summary
        }

    def _is_qa_hold(self, status: str, metadata: Dict) -> bool:
        """Check if transaction represents QA hold"""
        # Check status field
        if status in ['QA_HOLD', 'QUALITY_HOLD', 'INSPECTION']:
            return True

        # Check metadata fields
        qa_status = metadata.get('qa_status', metadata.get('quality_status', '')).upper()
        if qa_status in ['HOLD', 'ON_HOLD', 'INSPECTION', 'PENDING_QA']:
            return True

        # Check for QA-related flags
        if metadata.get('qa_hold') or metadata.get('quality_hold'):
            return True

        return False

    def _analyze_qa_hold(
        self,
        record: Dict,
        metadata: Dict
    ) -> Optional[QADelay]:
        """
        Analyze a single QA hold transaction.

        Args:
            record: Transaction record from database
            metadata: ERP metadata from transaction

        Returns:
            QADelay object if valid hold found, None otherwise
        """
        days_on_hold = record.get('days_outstanding', 0)
        wip_value = record.get('outstanding_amount', 0)

        # Skip if no meaningful hold time
        if days_on_hold < 1:
            return None

        # Extract work order information
        work_order_id = metadata.get('work_order', metadata.get('job_number', 'UNKNOWN'))
        operation_seq = metadata.get('operation_seq', metadata.get('routing_seq', 0))

        # Extract quantity information
        quantity_on_hold = metadata.get('quantity_on_hold', metadata.get('quantity', 0))
        unit_wip_cost = wip_value / quantity_on_hold if quantity_on_hold > 0 else 0

        # Extract hold reason
        hold_reason = metadata.get(
            'qa_hold_reason',
            metadata.get('hold_reason', metadata.get('quality_issue', 'Unknown'))
        )

        # Calculate cash impact components
        # 1. Carrying cost: WIP value × Days on hold × (WACC/365)
        carrying_cost = wip_value * days_on_hold * (self.wacc / 365.0)

        # 2. Throughput impact (estimated revenue delay)
        # Assume each day of QA hold delays revenue by 15% of WIP value
        throughput_impact = wip_value * 0.15

        total_cash_impact = carrying_cost + throughput_impact

        # Determine if preventable
        preventable = self._is_preventable_hold(metadata, hold_reason)

        return QADelay(
            work_order_id=work_order_id,
            operation_seq=int(operation_seq),
            qa_hold_start_date=None,  # Not available in current schema
            qa_hold_release_date=None,  # Not available in current schema
            days_on_hold=days_on_hold,
            quantity_on_hold=quantity_on_hold,
            unit_wip_cost=unit_wip_cost,
            wip_value=wip_value,
            hold_reason=hold_reason,
            carrying_cost=carrying_cost,
            throughput_impact=throughput_impact,
            total_cash_impact=total_cash_impact,
            preventable=preventable
        )

    def _is_preventable_hold(self, metadata: Dict, hold_reason: str) -> bool:
        """
        Determine if QA hold is preventable through process improvement.

        Criteria for preventable:
        - Hold reason indicates process issue (e.g., "out of spec", "dimensional variance")
        - Recurring issue flag

        Not preventable:
        - Random QA sampling
        - First-time issues
        - Customer-required inspection
        """
        # Check for recurring issue flag
        if metadata.get('recurring_issue') or metadata.get('repeat_failure'):
            return True

        # Check hold reason for process issues
        preventable_keywords = [
            'out of spec',
            'dimensional variance',
            'tolerance',
            'material defect',
            'process deviation',
            'setup error',
            'contamination',
            'measurement error'
        ]

        hold_reason_lower = hold_reason.lower()
        if any(keyword in hold_reason_lower for keyword in preventable_keywords):
            return True

        # Random sampling or customer-required inspection
        non_preventable_keywords = [
            'random sample',
            'customer inspection',
            'required inspection',
            'audit sample',
            'first article'
        ]

        if any(keyword in hold_reason_lower for keyword in non_preventable_keywords):
            return False

        # Default to non-preventable for unknown reasons
        return False

    def _calculate_summary(self, qa_delays: List[QADelay]) -> Dict:
        """Calculate summary metrics from QA delays list"""
        if not qa_delays:
            return self._empty_summary()

        preventable_delays = [d for d in qa_delays if d.preventable]

        return {
            'total_qa_holds': len(qa_delays),
            'total_wip_value': sum(d.wip_value for d in qa_delays),
            'avg_hold_days': sum(d.days_on_hold for d in qa_delays) / len(qa_delays),
            'total_carrying_cost': sum(d.carrying_cost for d in qa_delays),
            'total_throughput_impact': sum(d.throughput_impact for d in qa_delays),
            'total_cash_impact': sum(d.total_cash_impact for d in qa_delays),
            'preventable_holds': len(preventable_delays),
            'preventable_cash_impact': sum(d.total_cash_impact for d in preventable_delays)
        }

    def _empty_summary(self) -> Dict:
        """Return empty summary dict"""
        return {
            'total_qa_holds': 0,
            'total_wip_value': 0,
            'avg_hold_days': 0,
            'total_carrying_cost': 0,
            'total_throughput_impact': 0,
            'total_cash_impact': 0,
            'preventable_holds': 0,
            'preventable_cash_impact': 0
        }
