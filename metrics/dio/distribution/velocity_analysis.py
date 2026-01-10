"""
Distribution velocity and inventory turns analysis.

Identifies items that should turn fast (high demand) but are turning slowly,
calculates lost turn opportunity and cash impact.

For distributors, velocity is everything. Items with high demand should
turn quickly. When they don't, it indicates process issues causing
cash to be trapped in slow-moving inventory.

Cash impact calculation:
- Lost turns × Inventory value × Gross margin %

Example:
- Item should turn 12x/year (every 30 days)
- Actually turning 8x/year (every 45 days)
- Lost turns: 4 per year
- Inventory value: $100K
- Gross margin: 12%
- Cash impact: 4 × $100K × 12% = $48K/year
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class VelocityIssue:
    """Represents a single velocity/turns issue"""
    item_id: str
    item_description: str
    avg_monthly_demand: float
    avg_inventory_on_hand: float
    inventory_value: float
    expected_turn_days: int
    actual_turn_days: int
    excess_days: int
    normal_annual_turns: float
    actual_annual_turns: float
    lost_turns: float
    gross_margin_pct: float
    cash_impact_annual: float
    root_cause: str


class VelocityAnalyzer:
    """
    Analyzes inventory velocity and identifies turn opportunities.

    Adapted to work with existing WCSearch database structure:
    - Uses transactions table with DIO component_type
    - Extracts item-level data from erp_metadata JSONB field
    - Calculates turns from days_outstanding
    """

    def __init__(self, db_client):
        """
        Initialize analyzer with database client.

        Args:
            db_client: Supabase client
        """
        self.db = db_client

    def analyze(
        self,
        company_id: str,
        gross_margin_pct: float = 0.12,
        min_inventory_value: float = 1000
    ) -> Dict:
        """
        Main analysis method.

        Args:
            company_id: UUID of company
            gross_margin_pct: Default gross margin % (0.12 = 12%)
            min_inventory_value: Minimum inventory value to include

        Returns:
            dict with:
            - issues: List of VelocityIssue objects
            - summary_metrics: Aggregated totals
        """
        logger.info(f"Starting velocity analysis for company {company_id}")

        # Query DIO transactions with item-level metadata
        response = self.db.table('transactions').select(
            'transaction_id, transaction_number, days_outstanding, '
            'outstanding_amount, erp_metadata, status'
        ).eq('company_id', company_id).eq(
            'component_type', 'DIO'
        ).gte(
            'outstanding_amount', min_inventory_value
        ).execute()

        if not response.data:
            logger.warning(f"No DIO transactions found for company {company_id}")
            return {
                'issues': [],
                'summary': self._empty_summary()
            }

        # Analyze each transaction for velocity issues
        issues = []
        for record in response.data:
            issue = self._analyze_transaction(record, gross_margin_pct)
            if issue:
                issues.append(issue)

        # Sort by cash impact (descending)
        issues.sort(key=lambda x: x.cash_impact_annual, reverse=True)

        # Calculate summary metrics
        summary = self._calculate_summary(issues)

        logger.info(
            f"Velocity analysis complete: {len(issues)} issues found, "
            f"${summary['total_cash_impact_annual']:,.0f} total impact"
        )

        return {
            'issues': issues,
            'summary': summary
        }

    def _analyze_transaction(
        self,
        record: Dict,
        default_margin: float
    ) -> Optional[VelocityIssue]:
        """
        Analyze a single transaction for velocity issues.

        Args:
            record: Transaction record from database
            default_margin: Default gross margin %

        Returns:
            VelocityIssue object if issue found, None otherwise
        """
        metadata = record.get('erp_metadata', {})
        days_outstanding = record.get('days_outstanding', 0)
        inventory_value = record.get('outstanding_amount', 0)

        # Skip if no meaningful data
        if days_outstanding <= 0 or inventory_value <= 0:
            return None

        # Extract item information from metadata
        item_id = metadata.get('item_id', metadata.get('material_number', 'UNKNOWN'))
        item_description = metadata.get('item_description', metadata.get('material_desc', ''))

        # Determine expected turn days based on item classification
        # If metadata includes ABC classification or movement class, use it
        movement_class = metadata.get('movement_class', '').upper()
        abc_class = metadata.get('abc_classification', '').upper()

        if movement_class == 'FAST' or abc_class == 'A':
            expected_turn_days = 30  # Monthly turns for fast movers
        elif movement_class == 'MEDIUM' or abc_class == 'B':
            expected_turn_days = 45  # 45-day turns for medium movers
        else:
            expected_turn_days = 60  # 60-day turns for slow movers

        # If transaction has been outstanding longer than expected, it's a velocity issue
        actual_turn_days = days_outstanding

        # Only flag if actually slow
        if actual_turn_days <= expected_turn_days:
            return None

        # Calculate turns
        normal_annual_turns = 365.0 / expected_turn_days
        actual_annual_turns = 365.0 / actual_turn_days if actual_turn_days > 0 else 0
        lost_turns = normal_annual_turns - actual_annual_turns

        # Get gross margin from metadata or use default
        gross_margin = metadata.get('gross_margin_pct', default_margin)
        if isinstance(gross_margin, (int, float)) and gross_margin > 1:
            gross_margin = gross_margin / 100.0  # Convert percentage to decimal

        # Calculate cash impact
        cash_impact_annual = inventory_value * lost_turns * gross_margin

        # Diagnose root cause from metadata
        root_cause = self._diagnose_root_cause(metadata, actual_turn_days - expected_turn_days)

        # Estimate monthly demand (simplified)
        avg_monthly_demand = metadata.get('avg_monthly_demand', 0)
        avg_inventory = metadata.get('quantity_on_hand', 0)

        return VelocityIssue(
            item_id=item_id,
            item_description=item_description,
            avg_monthly_demand=avg_monthly_demand,
            avg_inventory_on_hand=avg_inventory,
            inventory_value=inventory_value,
            expected_turn_days=expected_turn_days,
            actual_turn_days=actual_turn_days,
            excess_days=actual_turn_days - expected_turn_days,
            normal_annual_turns=normal_annual_turns,
            actual_annual_turns=actual_annual_turns,
            lost_turns=lost_turns,
            gross_margin_pct=gross_margin,
            cash_impact_annual=cash_impact_annual,
            root_cause=root_cause
        )

    def _diagnose_root_cause(self, metadata: Dict, excess_days: int) -> str:
        """
        Attempt to diagnose root cause of slow turns from metadata.

        Possible causes:
        - Cross-dock staging delays
        - Warehouse transfer delays
        - Putaway delays
        - Over-purchasing
        - Multi-warehouse imbalance
        """
        # Check for location indicators
        location = metadata.get('location_code', '').upper()
        if 'XDOCK' in location or 'CROSS' in location:
            return f"Cross-dock staging delay ({excess_days} days excess)"

        # Check for transfer indicators
        if metadata.get('transfer_order') or metadata.get('warehouse_transfer'):
            return f"Warehouse transfer delay ({excess_days} days excess)"

        # Check for receiving/putaway status
        receipt_status = metadata.get('receipt_status', '').upper()
        if receipt_status in ['RECEIVED', 'IN_RECEIVING']:
            return f"Putaway delay - received but not put away ({excess_days} days)"

        # Check for over-purchasing indicators
        purchase_qty = metadata.get('purchase_order_quantity', 0)
        monthly_demand = metadata.get('avg_monthly_demand', 0)
        if monthly_demand > 0 and purchase_qty > monthly_demand * 2:
            return f"Over-purchasing - PO quantity is {purchase_qty / monthly_demand:.1f}x monthly demand"

        # Check for multi-location issues
        if metadata.get('multiple_warehouses') or metadata.get('transfer_pending'):
            return f"Multi-warehouse imbalance ({excess_days} days excess)"

        # Default
        return f"Process delays causing {excess_days}-day excess cycle time"

    def _calculate_summary(self, issues: List[VelocityIssue]) -> Dict:
        """Calculate summary metrics from issues list"""
        if not issues:
            return self._empty_summary()

        return {
            'total_issues': len(issues),
            'total_inventory_value': sum(i.inventory_value for i in issues),
            'total_lost_turns': sum(i.lost_turns for i in issues),
            'total_cash_impact_annual': sum(i.cash_impact_annual for i in issues),
            'avg_excess_days': sum(i.excess_days for i in issues) / len(issues),
            'avg_lost_turns': sum(i.lost_turns for i in issues) / len(issues)
        }

    def _empty_summary(self) -> Dict:
        """Return empty summary dict"""
        return {
            'total_issues': 0,
            'total_inventory_value': 0,
            'total_lost_turns': 0,
            'total_cash_impact_annual': 0,
            'avg_excess_days': 0,
            'avg_lost_turns': 0
        }

    def save_to_database(
        self,
        company_id: str,
        issues: List[VelocityIssue],
        summary: Dict
    ) -> Optional[str]:
        """
        Save velocity analysis results to database.

        Args:
            company_id: UUID of company
            issues: List of VelocityIssue objects
            summary: Summary metrics dict

        Returns:
            analysis_id (UUID) if successful, None otherwise
        """
        try:
            # First check if an analysis record exists for today
            response = self.db.table('dio_distribution_analysis').select(
                'analysis_id'
            ).eq('company_id', company_id).execute()

            # Prepare summary data for main table
            analysis_data = {
                'company_id': company_id,
                'velocity_issues_count': summary['total_issues'],
                'velocity_inventory_value': summary['total_inventory_value'],
                'velocity_normal_turns': summary.get('avg_normal_turns', 0),
                'velocity_actual_turns': summary.get('avg_actual_turns', 0),
                'velocity_lost_turns': summary['total_lost_turns'],
                'velocity_cash_impact': summary['total_cash_impact_annual']
            }

            # Upsert main analysis record
            if response.data and len(response.data) > 0:
                # Update existing
                analysis_id = response.data[0]['analysis_id']
                self.db.table('dio_distribution_analysis').update(
                    analysis_data
                ).eq('analysis_id', analysis_id).execute()
            else:
                # Insert new
                result = self.db.table('dio_distribution_analysis').insert(
                    analysis_data
                ).execute()
                analysis_id = result.data[0]['analysis_id']

            # Save detail records
            if issues:
                detail_records = []
                for issue in issues:
                    detail_records.append({
                        'analysis_id': analysis_id,
                        'item_id': issue.item_id,
                        'item_description': issue.item_description,
                        'avg_monthly_demand': issue.avg_monthly_demand,
                        'avg_inventory_on_hand': issue.avg_inventory_on_hand,
                        'inventory_value': issue.inventory_value,
                        'expected_turn_days': issue.expected_turn_days,
                        'actual_turn_days': issue.actual_turn_days,
                        'excess_days': issue.excess_days,
                        'normal_annual_turns': issue.normal_annual_turns,
                        'actual_annual_turns': issue.actual_annual_turns,
                        'lost_turns': issue.lost_turns,
                        'gross_margin_pct': issue.gross_margin_pct,
                        'cash_impact_annual': issue.cash_impact_annual,
                        'root_cause': issue.root_cause
                    })

                # Batch insert detail records
                self.db.table('dio_distribution_velocity_detail').insert(
                    detail_records
                ).execute()

            logger.info(f"Velocity analysis saved with ID {analysis_id}")
            return analysis_id

        except Exception as e:
            logger.error(f"Error saving velocity analysis: {e}")
            return None
