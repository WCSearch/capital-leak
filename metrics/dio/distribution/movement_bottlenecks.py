"""
Distribution movement bottleneck analysis.

Tracks cross-dock staging delays, warehouse transfer delays, putaway delays,
and other movement bottlenecks that slow inventory velocity.

For distributors, movement is cash. Every hour inventory sits in staging,
cross-dock, or in-transit is a lost turn opportunity.

Cash impact = Lost turns × Inventory value × Gross margin %
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MovementBottleneck:
    """Represents a single movement delay event"""
    bottleneck_type: str  # 'CROSS_DOCK', 'WAREHOUSE_TRANSFER', 'PUTAWAY', 'RECEIVING'
    transaction_id: str
    item_id: str
    warehouse_location: str
    timestamp_entered: Optional[datetime]
    timestamp_exited: Optional[datetime]
    expected_hours: float
    actual_hours: float
    excess_days: float
    quantity: float
    unit_cost: float
    inventory_value: float
    normal_turn_days: int
    normal_annual_turns: float
    actual_annual_turns: float
    lost_turns: float
    gross_margin_pct: float
    cash_impact: float
    root_cause: str
    system_event: str


class MovementBottleneckAnalyzer:
    """
    Identifies movement bottlenecks in distribution operations.

    Focus areas:
    1. Cross-dock staging timeouts (should be <4 hours, often 7+ days)
    2. Warehouse transfers stuck in transit/staging
    3. Received goods not putaway
    4. Picked goods not shipped

    Cash impact = Lost turns × Inventory value × Gross margin %

    Adapted to work with existing WCSearch database:
    - Uses event_logs to track state transitions
    - Uses erp_metadata for location and timing data
    """

    # Expected cycle times (in hours)
    EXPECTED_TIMES = {
        'CROSS_DOCK': 4,      # Cross-dock should be <4 hours
        'PUTAWAY': 8,         # Putaway should be <8 hours
        'RECEIVING': 4,       # Receipt to putaway <4 hours
        'PICK_TO_SHIP': 12,   # Pick to ship <12 hours
        'WT_TOTAL': 24        # Full warehouse transfer <24 hours
    }

    def __init__(self, db_client, gross_margin_pct: float = 0.12):
        """
        Initialize analyzer with database client.

        Args:
            db_client: Supabase client
            gross_margin_pct: Default gross margin % (0.12 = 12%)
        """
        self.db = db_client
        self.default_margin = gross_margin_pct

    def analyze(self, company_id: str) -> Dict:
        """
        Run full movement bottleneck analysis.

        Args:
            company_id: UUID of company

        Returns:
            dict with:
            - bottlenecks: List of MovementBottleneck objects
            - summary: Aggregated totals
            - by_type: Breakdown by bottleneck type
        """
        logger.info(f"Starting movement bottleneck analysis for company {company_id}")

        # Analyze different bottleneck types
        cross_dock = self._analyze_cross_dock_delays(company_id)
        warehouse_transfers = self._analyze_warehouse_transfer_delays(company_id)
        putaway = self._analyze_putaway_delays(company_id)

        # Combine all bottlenecks
        all_bottlenecks = (
            cross_dock['bottlenecks'] +
            warehouse_transfers['bottlenecks'] +
            putaway['bottlenecks']
        )

        # Sort by cash impact
        all_bottlenecks.sort(key=lambda x: x.cash_impact, reverse=True)

        # Combined summary
        total_summary = {
            'total_events': len(all_bottlenecks),
            'total_inventory_value': sum(b.inventory_value for b in all_bottlenecks),
            'total_cash_impact': sum(b.cash_impact for b in all_bottlenecks),
            'avg_excess_days': sum(b.excess_days for b in all_bottlenecks) / len(all_bottlenecks) if all_bottlenecks else 0,
            'cross_dock_summary': cross_dock['summary'],
            'warehouse_transfer_summary': warehouse_transfers['summary'],
            'putaway_summary': putaway['summary']
        }

        logger.info(
            f"Movement bottleneck analysis complete: {len(all_bottlenecks)} bottlenecks found, "
            f"${total_summary['total_cash_impact']:,.0f} total impact"
        )

        return {
            'bottlenecks': all_bottlenecks,
            'summary': total_summary,
            'by_type': {
                'cross_dock': cross_dock,
                'warehouse_transfers': warehouse_transfers,
                'putaway': putaway
            }
        }

    def _analyze_cross_dock_delays(self, company_id: str) -> Dict:
        """
        Analyze cross-dock staging delays.

        Queries for inventory sitting in cross-dock locations longer than expected.
        Uses event logs to track entry/exit times.
        """
        bottlenecks = []

        try:
            # Query DIO transactions with cross-dock indicators
            response = self.db.table('transactions').select(
                'transaction_id, transaction_number, days_outstanding, '
                'outstanding_amount, erp_metadata'
            ).eq('company_id', company_id).eq('component_type', 'DIO').execute()

            if not response.data:
                return {'bottlenecks': [], 'summary': self._empty_summary()}

            for record in response.data:
                metadata = record.get('erp_metadata', {})
                location = metadata.get('location_code', '').upper()

                # Check if this is cross-dock inventory
                if not ('XDOCK' in location or 'CROSS' in location or
                        metadata.get('cross_dock') or metadata.get('staging_location')):
                    continue

                # Calculate time in location
                days_outstanding = record.get('days_outstanding', 0)
                expected_hours = self.EXPECTED_TIMES['CROSS_DOCK']
                actual_hours = days_outstanding * 24
                excess_days = max(0, (actual_hours - expected_hours) / 24)

                # Only flag if excessive
                if excess_days < 0.1:  # Less than 2.4 hours excess
                    continue

                # Create bottleneck record
                bottleneck = self._create_bottleneck(
                    bottleneck_type='CROSS_DOCK',
                    transaction_id=record['transaction_id'],
                    metadata=metadata,
                    inventory_value=record['outstanding_amount'],
                    expected_hours=expected_hours,
                    actual_hours=actual_hours,
                    excess_days=excess_days,
                    root_cause=metadata.get('delay_reason', 'Cross-dock timeout')
                )

                if bottleneck:
                    bottlenecks.append(bottleneck)

        except Exception as e:
            logger.error(f"Error analyzing cross-dock delays: {e}")

        summary = self._calculate_summary(bottlenecks)
        return {'bottlenecks': bottlenecks, 'summary': summary}

    def _analyze_warehouse_transfer_delays(self, company_id: str) -> Dict:
        """
        Analyze warehouse transfer cycle time delays.

        Identifies transfers stuck in various stages of the WT lifecycle.
        """
        bottlenecks = []

        try:
            # Query for warehouse transfer transactions
            response = self.db.table('transactions').select(
                'transaction_id, transaction_number, days_outstanding, '
                'outstanding_amount, erp_metadata'
            ).eq('company_id', company_id).eq('component_type', 'DIO').execute()

            if not response.data:
                return {'bottlenecks': [], 'summary': self._empty_summary()}

            for record in response.data:
                metadata = record.get('erp_metadata', {})

                # Check if this is a warehouse transfer
                if not (metadata.get('transfer_order') or
                        metadata.get('warehouse_transfer') or
                        metadata.get('from_warehouse')):
                    continue

                # Calculate transfer cycle time
                days_outstanding = record.get('days_outstanding', 0)
                expected_hours = self.EXPECTED_TIMES['WT_TOTAL']
                actual_hours = days_outstanding * 24
                excess_days = max(0, (actual_hours - expected_hours) / 24)

                # Only flag if excessive (>1 day over expected)
                if excess_days < 1:
                    continue

                # Diagnose which stage is causing delay
                root_cause = self._diagnose_wt_delay(metadata, days_outstanding)

                # Create bottleneck record
                location = f"{metadata.get('from_warehouse', 'UNKNOWN')} → {metadata.get('to_warehouse', 'UNKNOWN')}"
                bottleneck = self._create_bottleneck(
                    bottleneck_type='WAREHOUSE_TRANSFER',
                    transaction_id=record['transaction_id'],
                    metadata=metadata,
                    inventory_value=record['outstanding_amount'],
                    expected_hours=expected_hours,
                    actual_hours=actual_hours,
                    excess_days=excess_days,
                    root_cause=root_cause,
                    location_override=location
                )

                if bottleneck:
                    bottlenecks.append(bottleneck)

        except Exception as e:
            logger.error(f"Error analyzing warehouse transfer delays: {e}")

        summary = self._calculate_summary(bottlenecks)
        return {'bottlenecks': bottlenecks, 'summary': summary}

    def _analyze_putaway_delays(self, company_id: str) -> Dict:
        """
        Analyze putaway delays (received but not put away).
        """
        bottlenecks = []

        try:
            # Query for received inventory not yet put away
            response = self.db.table('transactions').select(
                'transaction_id, transaction_number, days_outstanding, '
                'outstanding_amount, erp_metadata, status'
            ).eq('company_id', company_id).eq('component_type', 'DIO').execute()

            if not response.data:
                return {'bottlenecks': [], 'summary': self._empty_summary()}

            for record in response.data:
                metadata = record.get('erp_metadata', {})
                status = record.get('status', '').upper()

                # Check if this is received but not put away
                if not (status == 'RECEIVED' or
                        metadata.get('receipt_status') == 'RECEIVED' or
                        metadata.get('putaway_pending')):
                    continue

                # Calculate time in receiving
                days_outstanding = record.get('days_outstanding', 0)
                expected_hours = self.EXPECTED_TIMES['PUTAWAY']
                actual_hours = days_outstanding * 24
                excess_days = max(0, (actual_hours - expected_hours) / 24)

                # Only flag if excessive (>4 hours over expected)
                if excess_days < 0.2:
                    continue

                # Create bottleneck record
                bottleneck = self._create_bottleneck(
                    bottleneck_type='PUTAWAY',
                    transaction_id=record['transaction_id'],
                    metadata=metadata,
                    inventory_value=record['outstanding_amount'],
                    expected_hours=expected_hours,
                    actual_hours=actual_hours,
                    excess_days=excess_days,
                    root_cause=metadata.get('delay_reason', 'Putaway delay')
                )

                if bottleneck:
                    bottlenecks.append(bottleneck)

        except Exception as e:
            logger.error(f"Error analyzing putaway delays: {e}")

        summary = self._calculate_summary(bottlenecks)
        return {'bottlenecks': bottlenecks, 'summary': summary}

    def _create_bottleneck(
        self,
        bottleneck_type: str,
        transaction_id: str,
        metadata: Dict,
        inventory_value: float,
        expected_hours: float,
        actual_hours: float,
        excess_days: float,
        root_cause: str,
        location_override: Optional[str] = None
    ) -> Optional[MovementBottleneck]:
        """Create a MovementBottleneck object from transaction data"""

        item_id = metadata.get('item_id', metadata.get('material_number', 'UNKNOWN'))
        location = location_override or metadata.get('location_code', 'UNKNOWN')
        quantity = metadata.get('quantity_on_hand', metadata.get('quantity', 0))
        unit_cost = inventory_value / quantity if quantity > 0 else 0

        # Calculate turns impact
        # For fast movers, use 30-day baseline; for slow, use 60-day
        movement_class = metadata.get('movement_class', '').upper()
        normal_turn_days = 30 if movement_class == 'FAST' else 60

        normal_annual_turns = 365.0 / normal_turn_days
        actual_turn_days = normal_turn_days + excess_days
        actual_annual_turns = 365.0 / actual_turn_days if actual_turn_days > 0 else 0
        lost_turns = normal_annual_turns - actual_annual_turns

        # Get gross margin
        gross_margin = metadata.get('gross_margin_pct', self.default_margin)
        if isinstance(gross_margin, (int, float)) and gross_margin > 1:
            gross_margin = gross_margin / 100.0

        # Calculate cash impact
        cash_impact = inventory_value * lost_turns * gross_margin

        return MovementBottleneck(
            bottleneck_type=bottleneck_type,
            transaction_id=transaction_id,
            item_id=item_id,
            warehouse_location=location,
            timestamp_entered=None,  # Not available in current schema
            timestamp_exited=None,   # Not available in current schema
            expected_hours=expected_hours,
            actual_hours=actual_hours,
            excess_days=excess_days,
            quantity=quantity,
            unit_cost=unit_cost,
            inventory_value=inventory_value,
            normal_turn_days=normal_turn_days,
            normal_annual_turns=normal_annual_turns,
            actual_annual_turns=actual_annual_turns,
            lost_turns=lost_turns,
            gross_margin_pct=gross_margin,
            cash_impact=cash_impact,
            root_cause=root_cause,
            system_event=metadata.get('last_event', '')
        )

    def _diagnose_wt_delay(self, metadata: Dict, days_outstanding: int) -> str:
        """Diagnose root cause of warehouse transfer delay"""

        # Check transfer status
        wt_status = metadata.get('transfer_status', '').upper()

        if wt_status == 'CREATED' or wt_status == 'PENDING_PICK':
            return f"Pick delay - transfer waiting to be picked ({days_outstanding} days)"

        if wt_status == 'PICKED' or wt_status == 'PENDING_SHIP':
            return f"Ship delay - picked but not shipped ({days_outstanding} days)"

        if wt_status == 'SHIPPED' or wt_status == 'IN_TRANSIT':
            return f"Transit delay - in transit for {days_outstanding} days"

        if wt_status == 'RECEIVED' or wt_status == 'PENDING_PUTAWAY':
            return f"Putaway delay - received but not put away ({days_outstanding} days)"

        return f"General transfer delay ({days_outstanding} days total)"

    def _calculate_summary(self, bottlenecks: List[MovementBottleneck]) -> Dict:
        """Calculate summary metrics from bottlenecks list"""
        if not bottlenecks:
            return self._empty_summary()

        return {
            'total_events': len(bottlenecks),
            'total_inventory_value': sum(b.inventory_value for b in bottlenecks),
            'avg_excess_days': sum(b.excess_days for b in bottlenecks) / len(bottlenecks),
            'total_lost_turns': sum(b.lost_turns for b in bottlenecks),
            'total_cash_impact': sum(b.cash_impact for b in bottlenecks)
        }

    def _empty_summary(self) -> Dict:
        """Return empty summary dict"""
        return {
            'total_events': 0,
            'total_inventory_value': 0,
            'avg_excess_days': 0,
            'total_lost_turns': 0,
            'total_cash_impact': 0
        }
