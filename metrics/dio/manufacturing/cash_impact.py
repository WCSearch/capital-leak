"""
Manufacturing cash impact calculation.

For manufacturing businesses, cash impact is calculated as:
Carrying costs + Throughput impact

This is fundamentally different from distribution's "lost turns" model.

Components:
1. Carrying cost: WIP value × Days delayed × (WACC/365)
2. Throughput impact: Delayed completion → delayed revenue
3. Yield losses: Scrap and rework costs
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ManufacturingCashImpact:
    """
    Calculates total cash impact for manufacturing business.

    Aggregates impact from:
    - WIP bottlenecks (carrying costs + throughput delays)
    - QA delays (idle time costs)
    - Yield issues (scrap and rework)
    - Production variances
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
        wip_analysis: Dict,
        qa_analysis: Dict,
        scrap_value: float = 0,
        rework_cost: float = 0,
        variance_cost: float = 0
    ) -> Dict:
        """
        Calculate total manufacturing cash impact.

        Args:
            company_id: UUID of company
            wip_analysis: Results from WIPBottleneckAnalyzer
            qa_analysis: Results from QADelayAnalyzer
            scrap_value: Total value of scrapped materials
            rework_cost: Total cost of rework
            variance_cost: Total manufacturing variances

        Returns:
            dict with:
            - total_cash_impact: Total annual cash impact
            - breakdown: Impact by category
            - priority_actions: Recommended priorities
        """
        # Extract impacts from analyses
        wip_carrying = wip_analysis.get('summary', {}).get('total_carrying_cost', 0)
        wip_throughput = wip_analysis.get('summary', {}).get('total_throughput_impact', 0)
        qa_carrying = qa_analysis.get('summary', {}).get('total_carrying_cost', 0)
        qa_throughput = qa_analysis.get('summary', {}).get('total_throughput_impact', 0)

        # Total impact
        total_impact = (
            wip_carrying + wip_throughput +
            qa_carrying + qa_throughput +
            scrap_value + rework_cost + variance_cost
        )

        # Breakdown by category
        breakdown = {
            'wip_bottlenecks': {
                'carrying_cost': wip_carrying,
                'throughput_impact': wip_throughput,
                'total_impact': wip_carrying + wip_throughput,
                'pct_of_total': ((wip_carrying + wip_throughput) / total_impact * 100) if total_impact > 0 else 0,
                'description': 'Work center queue delays and capacity constraints',
                'calculation': 'Carrying cost (WIP value × Days × WACC/365) + Throughput impact'
            },
            'qa_delays': {
                'carrying_cost': qa_carrying,
                'throughput_impact': qa_throughput,
                'total_impact': qa_carrying + qa_throughput,
                'pct_of_total': ((qa_carrying + qa_throughput) / total_impact * 100) if total_impact > 0 else 0,
                'description': 'Quality hold delays - WIP sitting idle during inspection',
                'calculation': 'Carrying cost + Throughput impact',
                'preventable_pct': self._calculate_preventable_pct(qa_analysis)
            },
            'yield_losses': {
                'scrap_cost': scrap_value,
                'rework_cost': rework_cost,
                'total_impact': scrap_value + rework_cost,
                'pct_of_total': ((scrap_value + rework_cost) / total_impact * 100) if total_impact > 0 else 0,
                'description': 'Material and labor costs from scrap and rework',
                'calculation': 'Direct scrap costs + Rework labor and material'
            },
            'variances': {
                'total_impact': variance_cost,
                'pct_of_total': (variance_cost / total_impact * 100) if total_impact > 0 else 0,
                'description': 'Material, labor, and overhead variances from standard',
                'calculation': 'Sum of unfavorable manufacturing variances'
            }
        }

        # Determine priority actions
        priority_actions = self._determine_priorities(breakdown)

        # Format for presentation
        result = {
            'total_cash_impact': total_impact,
            'total_wip_at_risk': (
                wip_analysis.get('summary', {}).get('total_wip_value', 0) +
                qa_analysis.get('summary', {}).get('total_wip_value', 0)
            ),
            'breakdown': breakdown,
            'priority_actions': priority_actions,
            'methodology': 'MANUFACTURING',
            'calculation_note': (
                'Manufacturing cash impact focuses on carrying costs and throughput delays. '
                'WIP sitting in queues or on hold incurs carrying costs (WIP value × Days × WACC/365) '
                'and delays revenue recognition. This is fundamentally different from distribution\'s '
                '"lost turns" approach.'
            )
        }

        logger.info(
            f"Manufacturing cash impact calculated for {company_id}: "
            f"${total_impact:,.0f} total annual impact"
        )

        return result

    def _calculate_preventable_pct(self, qa_analysis: Dict) -> float:
        """Calculate percentage of QA delays that are preventable"""
        summary = qa_analysis.get('summary', {})
        total_qa_impact = summary.get('total_cash_impact', 0)
        preventable_impact = summary.get('preventable_cash_impact', 0)

        if total_qa_impact > 0:
            return (preventable_impact / total_qa_impact) * 100
        return 0

    def _determine_priorities(self, breakdown: Dict) -> list:
        """
        Determine priority actions based on impact breakdown.

        Returns list of priorities sorted by impact.
        """
        priorities = []

        for category, data in breakdown.items():
            total_impact = data.get('total_impact', 0)
            if total_impact > 0:
                priority_item = {
                    'category': category,
                    'impact': total_impact,
                    'pct_of_total': data['pct_of_total'],
                    'description': data['description'],
                    'priority': self._get_priority_level(data['pct_of_total'])
                }

                # Add special notes for specific categories
                if category == 'qa_delays':
                    preventable_pct = data.get('preventable_pct', 0)
                    if preventable_pct > 50:
                        priority_item['note'] = f"{preventable_pct:.0f}% of QA delays are preventable through process improvement"

                priorities.append(priority_item)

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

        Updates dio_manufacturing_analysis table with total impact.

        Args:
            company_id: UUID of company
            analysis_id: UUID of analysis record
            impact_data: Impact calculation results

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract breakdown components
            breakdown = impact_data.get('breakdown', {})

            # Update the analysis record with detailed breakdown
            update_data = {
                'bottleneck_carrying_cost': breakdown.get('wip_bottlenecks', {}).get('carrying_cost', 0),
                'bottleneck_throughput_impact': breakdown.get('wip_bottlenecks', {}).get('throughput_impact', 0),
                'qa_hold_carrying_cost': breakdown.get('qa_delays', {}).get('carrying_cost', 0),
                'qa_hold_throughput_impact': breakdown.get('qa_delays', {}).get('throughput_impact', 0),
                'scrap_total_impact': breakdown.get('yield_losses', {}).get('scrap_cost', 0),
                'rework_total_impact': breakdown.get('yield_losses', {}).get('rework_cost', 0),
                'total_variance_cost': breakdown.get('variances', {}).get('total_impact', 0),
                'total_cash_impact': impact_data['total_cash_impact'],
                'total_annual_impact': impact_data['total_cash_impact']
            }

            self.db.table('dio_manufacturing_analysis').update(
                update_data
            ).eq('analysis_id', analysis_id).execute()

            logger.info(f"Cash impact saved for analysis {analysis_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving cash impact: {e}")
            return False
