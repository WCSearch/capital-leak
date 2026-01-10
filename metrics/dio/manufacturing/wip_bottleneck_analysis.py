"""
Manufacturing WIP bottleneck analysis.

Identifies work center capacity constraints causing queue buildup,
analyzes actual vs standard operation times, and quantifies cash impact
from delayed throughput.

For manufacturers, WIP sitting in queues represents:
1. Carrying costs (WIP value × Days delayed × WACC/365)
2. Throughput impact (delayed completion → delayed revenue)

This is fundamentally different from distribution's "lost turns" model.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class WIPBottleneck:
    """Represents a work center bottleneck"""
    work_order_id: str
    operation_seq: int
    department_id: str
    resource_code: str
    scheduled_start_date: Optional[datetime]
    actual_start_date: Optional[datetime]
    days_delayed: int
    quantity_in_queue: float
    quantity_running: float
    unit_wip_cost: float
    wip_value_in_queue: float
    standard_hours_per_unit: float
    actual_hours_per_unit: float
    hours_variance_per_unit: float
    carrying_cost: float
    throughput_impact: float
    total_cash_impact: float
    bottleneck_severity: str
    root_cause: str


class WIPBottleneckAnalyzer:
    """
    Analyzes work center bottlenecks in manufacturing.

    Cash impact components:
    1. Carrying cost: WIP value × Days delayed × (WACC/365)
    2. Throughput impact: Delayed completion → delayed revenue

    Unlike distribution (where lost turns = cash impact), manufacturing
    cares about:
    - WIP carrying costs
    - Delayed completion → delayed revenue
    - Inefficient resource utilization

    Adapted to work with existing WCSearch database:
    - Uses transactions table with DIO component_type
    - Extracts work order data from erp_metadata
    - Identifies bottlenecks from event_logs
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
        Main bottleneck analysis.

        Identifies operations with:
        - High queue quantities (backlog)
        - Significant start delays (scheduled vs actual)
        - Hours variance (actual > standard)

        Args:
            company_id: UUID of company

        Returns:
            dict with:
            - bottlenecks: List of WIPBottleneck objects
            - summary: Aggregated totals
        """
        logger.info(f"Starting WIP bottleneck analysis for company {company_id}")

        bottlenecks = []

        try:
            # Query DIO transactions with work order indicators
            response = self.db.table('transactions').select(
                'transaction_id, transaction_number, days_outstanding, '
                'outstanding_amount, erp_metadata, status'
            ).eq('company_id', company_id).eq('component_type', 'DIO').execute()

            if not response.data:
                logger.warning(f"No DIO transactions found for company {company_id}")
                return {
                    'bottlenecks': [],
                    'summary': self._empty_summary()
                }

            # Analyze each transaction for WIP bottleneck indicators
            for record in response.data:
                metadata = record.get('erp_metadata', {})

                # Check if this is WIP (work order, job number, etc.)
                if not self._is_wip_transaction(metadata):
                    continue

                # Analyze for bottleneck
                bottleneck = self._analyze_wip_transaction(record, metadata)
                if bottleneck:
                    bottlenecks.append(bottleneck)

        except Exception as e:
            logger.error(f"Error analyzing WIP bottlenecks: {e}")

        # Sort by cash impact
        bottlenecks.sort(key=lambda x: x.total_cash_impact, reverse=True)

        # Calculate summary
        summary = self._calculate_summary(bottlenecks)

        logger.info(
            f"WIP bottleneck analysis complete: {len(bottlenecks)} bottlenecks found, "
            f"${summary['total_cash_impact']:,.0f} total impact"
        )

        return {
            'bottlenecks': bottlenecks,
            'summary': summary
        }

    def _is_wip_transaction(self, metadata: Dict) -> bool:
        """Check if transaction represents WIP"""
        wip_indicators = [
            'work_order', 'job_number', 'production_order',
            'manufacturing_order', 'shop_order', 'wip_entity',
            'operation_seq', 'work_center', 'routing_seq'
        ]

        return any(key in metadata for key in wip_indicators)

    def _analyze_wip_transaction(
        self,
        record: Dict,
        metadata: Dict
    ) -> Optional[WIPBottleneck]:
        """
        Analyze a single WIP transaction for bottleneck.

        Args:
            record: Transaction record from database
            metadata: ERP metadata from transaction

        Returns:
            WIPBottleneck object if bottleneck found, None otherwise
        """
        days_outstanding = record.get('days_outstanding', 0)
        wip_value = record.get('outstanding_amount', 0)

        # Skip if no meaningful delay
        if days_outstanding < 2:  # Less than 2 days delay
            return None

        # Extract work order information
        work_order_id = metadata.get('work_order', metadata.get('job_number', 'UNKNOWN'))
        operation_seq = metadata.get('operation_seq', metadata.get('routing_seq', 0))
        department_id = metadata.get('department', metadata.get('work_center', 'UNKNOWN'))
        resource_code = metadata.get('resource_code', metadata.get('work_center_code', 'UNKNOWN'))

        # Extract queue and running quantities
        quantity_in_queue = metadata.get('quantity_in_queue', metadata.get('quantity', 0))
        quantity_running = metadata.get('quantity_running', 0)

        # Calculate unit WIP cost
        total_quantity = quantity_in_queue + quantity_running
        unit_wip_cost = wip_value / total_quantity if total_quantity > 0 else 0
        wip_value_in_queue = quantity_in_queue * unit_wip_cost

        # Extract hours data
        standard_hours = metadata.get('standard_hours_per_unit', 0)
        actual_hours = metadata.get('actual_hours_per_unit', 0)
        hours_variance = actual_hours - standard_hours if actual_hours > 0 else 0

        # Calculate cash impact components
        # 1. Carrying cost: WIP value × Days delayed × (WACC/365)
        carrying_cost = wip_value_in_queue * days_outstanding * (self.wacc / 365.0)

        # 2. Throughput impact (simplified: estimate revenue delay impact)
        # Assume each day of delay costs 20% of WIP value in lost revenue opportunity
        throughput_impact = wip_value_in_queue * 0.20 if days_outstanding > 5 else 0

        total_cash_impact = carrying_cost + throughput_impact

        # Determine severity
        if days_outstanding > 10:
            severity = 'CRITICAL'
        elif days_outstanding > 5:
            severity = 'MODERATE'
        else:
            severity = 'MINOR'

        # Diagnose root cause
        root_cause = self._diagnose_bottleneck_cause(
            metadata,
            days_outstanding,
            hours_variance,
            quantity_in_queue
        )

        return WIPBottleneck(
            work_order_id=work_order_id,
            operation_seq=int(operation_seq),
            department_id=department_id,
            resource_code=resource_code,
            scheduled_start_date=None,  # Not available in current schema
            actual_start_date=None,     # Not available in current schema
            days_delayed=days_outstanding,
            quantity_in_queue=quantity_in_queue,
            quantity_running=quantity_running,
            unit_wip_cost=unit_wip_cost,
            wip_value_in_queue=wip_value_in_queue,
            standard_hours_per_unit=standard_hours,
            actual_hours_per_unit=actual_hours,
            hours_variance_per_unit=hours_variance,
            carrying_cost=carrying_cost,
            throughput_impact=throughput_impact,
            total_cash_impact=total_cash_impact,
            bottleneck_severity=severity,
            root_cause=root_cause
        )

    def _diagnose_bottleneck_cause(
        self,
        metadata: Dict,
        days_delayed: int,
        hours_variance: float,
        queue_quantity: float
    ) -> str:
        """
        Diagnose root cause of bottleneck.

        Possible causes:
        - Capacity constraint (work center overloaded)
        - Material shortage (waiting for components)
        - Quality hold (inspection delays)
        - Machine downtime
        - Inefficient setup times
        """
        # Check for capacity constraint indicators
        utilization = metadata.get('work_center_utilization', 0)
        if utilization > 90:
            return f"Capacity constraint - work center overloaded ({utilization:.0f}% utilization)"

        # Check for material shortage
        material_status = metadata.get('material_status', '').upper()
        if material_status in ['SHORTAGE', 'WAITING', 'BACKORDER']:
            return f"Material shortage - waiting for components ({days_delayed} days)"

        # Check for quality hold
        qa_status = metadata.get('qa_status', metadata.get('quality_status', '')).upper()
        if qa_status in ['HOLD', 'ON_HOLD', 'INSPECTION']:
            return f"Quality hold - {days_delayed} days on hold for inspection"

        # Check for machine downtime
        if metadata.get('machine_downtime') or metadata.get('equipment_failure'):
            return f"Machine downtime - equipment unavailable ({days_delayed} days)"

        # Check hours variance for inefficiency
        if hours_variance > 0.5:
            return f"Process inefficiency - actual time {hours_variance:.1f} hours over standard per unit"

        # Check queue size
        if queue_quantity > 100:
            return f"Queue buildup - {queue_quantity:.0f} units in queue ({days_delayed} day delay)"

        # Default
        return f"Production delay - {days_delayed} day backlog"

    def _calculate_summary(self, bottlenecks: List[WIPBottleneck]) -> Dict:
        """Calculate summary metrics from bottlenecks list"""
        if not bottlenecks:
            return self._empty_summary()

        return {
            'total_bottlenecks': len(bottlenecks),
            'total_wip_value': sum(b.wip_value_in_queue for b in bottlenecks),
            'avg_queue_days': sum(b.days_delayed for b in bottlenecks) / len(bottlenecks),
            'total_carrying_cost': sum(b.carrying_cost for b in bottlenecks),
            'total_throughput_impact': sum(b.throughput_impact for b in bottlenecks),
            'total_cash_impact': sum(b.total_cash_impact for b in bottlenecks),
            'critical_bottlenecks': len([b for b in bottlenecks if b.bottleneck_severity == 'CRITICAL']),
            'moderate_bottlenecks': len([b for b in bottlenecks if b.bottleneck_severity == 'MODERATE'])
        }

    def _empty_summary(self) -> Dict:
        """Return empty summary dict"""
        return {
            'total_bottlenecks': 0,
            'total_wip_value': 0,
            'avg_queue_days': 0,
            'total_carrying_cost': 0,
            'total_throughput_impact': 0,
            'total_cash_impact': 0,
            'critical_bottlenecks': 0,
            'moderate_bottlenecks': 0
        }
