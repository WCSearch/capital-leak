"""
Distribution cash impact calculation.

For distribution businesses, cash impact is calculated as:
Lost turns × Inventory value × Gross margin %

This is fundamentally different from manufacturing, where the focus is on
carrying costs and throughput delays.
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DistributionCashImpact:
    """
    Calculates total cash impact for distribution business.

    Aggregates impact from:
    - Velocity issues (lost turn opportunities)
    - Movement bottlenecks (cross-dock, WT, putaway delays)
    - Stockouts (lost sales)
    - Excess inventory (carrying costs)
    """

    def __init__(self, db_client):
        """
        Initialize calculator with database client.

        Args:
            db_client: Supabase client
        """
        self.db = db_client

    def calculate_total_impact(
        self,
        company_id: str,
        velocity_analysis: Dict,
        movement_analysis: Dict,
        excess_inventory_value: float = 0,
        carrying_cost_rate: float = 0.20
    ) -> Dict:
        """
        Calculate total distribution cash impact.

        Args:
            company_id: UUID of company
            velocity_analysis: Results from VelocityAnalyzer
            movement_analysis: Results from MovementBottleneckAnalyzer
            excess_inventory_value: Value of excess/obsolete inventory
            carrying_cost_rate: Annual carrying cost rate (default 20%)

        Returns:
            dict with:
            - total_cash_impact: Total annual cash impact
            - breakdown: Impact by category
            - priority_actions: Recommended priorities
        """
        # Extract impacts from analyses
        velocity_impact = velocity_analysis.get('summary', {}).get('total_cash_impact_annual', 0)
        movement_impact = movement_analysis.get('summary', {}).get('total_cash_impact', 0)
        excess_carrying_cost = excess_inventory_value * carrying_cost_rate

        # Total impact
        total_impact = velocity_impact + movement_impact + excess_carrying_cost

        # Breakdown by category
        breakdown = {
            'velocity_issues': {
                'cash_impact': velocity_impact,
                'pct_of_total': (velocity_impact / total_impact * 100) if total_impact > 0 else 0,
                'description': 'Lost turn opportunities from slow-moving inventory',
                'calculation': 'Lost turns × Inventory value × Gross margin %'
            },
            'movement_bottlenecks': {
                'cash_impact': movement_impact,
                'pct_of_total': (movement_impact / total_impact * 100) if total_impact > 0 else 0,
                'description': 'Cross-dock, warehouse transfer, and putaway delays',
                'calculation': 'Lost turns from delays × Inventory value × Gross margin %'
            },
            'excess_inventory': {
                'cash_impact': excess_carrying_cost,
                'pct_of_total': (excess_carrying_cost / total_impact * 100) if total_impact > 0 else 0,
                'description': 'Carrying costs for excess/obsolete inventory',
                'calculation': 'Excess inventory value × Carrying cost rate'
            }
        }

        # Determine priority actions
        priority_actions = self._determine_priorities(breakdown)

        # Format for presentation
        result = {
            'total_cash_impact': total_impact,
            'total_inventory_at_risk': (
                velocity_analysis.get('summary', {}).get('total_inventory_value', 0) +
                movement_analysis.get('summary', {}).get('total_inventory_value', 0) +
                excess_inventory_value
            ),
            'breakdown': breakdown,
            'priority_actions': priority_actions,
            'methodology': 'DISTRIBUTION',
            'calculation_note': (
                'Distribution cash impact focuses on lost turn opportunities. '
                'Every day inventory sits idle is a lost opportunity to turn that '
                'inventory into margin. Impact = Lost turns × Inventory value × Gross margin %.'
            )
        }

        logger.info(
            f"Distribution cash impact calculated for {company_id}: "
            f"${total_impact:,.0f} total annual impact"
        )

        return result

    def _determine_priorities(self, breakdown: Dict) -> list:
        """
        Determine priority actions based on impact breakdown.

        Returns list of priorities sorted by impact.
        """
        priorities = []

        for category, data in breakdown.items():
            if data['cash_impact'] > 0:
                priorities.append({
                    'category': category,
                    'impact': data['cash_impact'],
                    'pct_of_total': data['pct_of_total'],
                    'description': data['description'],
                    'priority': self._get_priority_level(data['pct_of_total'])
                })

        # Sort by impact (descending)
        priorities.sort(key=lambda x: x['impact'], reverse=True)

        return priorities

    def _get_priority_level(self, pct_of_total: float) -> str:
        """Determine priority level based on % of total impact"""
        if pct_of_total >= 40:
            return 'CRITICAL'
        elif pct_of_total >= 20:
            return 'HIGH'
        elif pct_of_total >= 10:
            return 'MEDIUM'
        else:
            return 'LOW'

    def save_to_database(
        self,
        company_id: str,
        analysis_id: str,
        impact_data: Dict
    ) -> bool:
        """
        Save cash impact calculation to database.

        Updates dio_distribution_analysis table with total impact.

        Args:
            company_id: UUID of company
            analysis_id: UUID of analysis record
            impact_data: Impact calculation results

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update the analysis record with total impact
            update_data = {
                'total_cash_impact': impact_data['total_cash_impact'],
                'total_annual_opportunity': impact_data['total_cash_impact']
            }

            self.db.table('dio_distribution_analysis').update(
                update_data
            ).eq('analysis_id', analysis_id).execute()

            logger.info(f"Cash impact saved for analysis {analysis_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving cash impact: {e}")
            return False
