"""
Manufacturing-Specific DIO Calculator

For manufacturing companies with BOMs, uses critical path analysis to determine
expected cycle times and identify trapped capital based on component availability.

Key differences from distribution:
- Long cycle times (days to months, not hours)
- BOM critical path determines expected completion time
- Component shortage analysis identifies root causes
- Work order aging analysis with bottleneck identification

Author: Capital Leak Analysis Team
Date: 2025-01-10
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import pandas as pd
from config.database import get_supabase_client


# Manufacturing-specific benchmarks (for non-BOM issues)
MANUFACTURING_BENCHMARKS = {
    'subcontract_standard': {
        'standard_days': 30,
        'threshold_days': 45,
        'description': 'Items at outside processor',
        'recovery_type': 'TRAPPED_CAPITAL'
    },
    'inspection_routine': {
        'standard_days': 2,
        'threshold_days': 5,
        'description': 'Routine quality inspection',
        'recovery_type': 'SPLIT'  # Some pass, some fail
    },
    'inspection_complex': {
        'standard_days': 5,
        'threshold_days': 10,
        'description': 'Complex quality inspection (MRB required)',
        'recovery_type': 'SPLIT'
    },
    'wip_aging': {
        'standard_days': None,  # Use BOM critical path
        'threshold_days': None,  # BOM + buffer
        'description': 'Work in process aging beyond BOM cycle',
        'recovery_type': 'PARTIAL_RECOVERY'
    }
}

# Manufacturing DIO issue types
MANUFACTURING_DIO_ISSUES = {
    'RELEASED_NOT_STARTED': {
        'benchmark': 'BOM_CRITICAL_PATH',
        'recovery_type': 'TRAPPED_CAPITAL',
        'description': 'Work orders released but production never started',
        'analysis_method': 'Component availability check at release date'
    },
    'AT_SUBCONTRACTOR': {
        'benchmark': 'subcontract_standard',
        'recovery_type': 'TRAPPED_CAPITAL',
        'description': 'Items at outside processor beyond normal cycle'
    },
    'QUARANTINE_PENDING_MRB': {
        'benchmark': 'inspection_complex',
        'recovery_type': 'SPLIT',
        'description': 'Quality inspection hold - disposition pending',
        'pass_rate_assumption': 0.70  # 70% typically pass, 30% scrapped
    },
    'QUARANTINE_ROUTINE': {
        'benchmark': 'inspection_routine',
        'recovery_type': 'SPLIT',
        'description': 'Routine quality inspection',
        'pass_rate_assumption': 0.85  # 85% pass for routine
    },
    'WIP_AGING': {
        'benchmark': 'wip_aging',
        'recovery_type': 'PARTIAL_RECOVERY',
        'description': 'Partially completed work orders beyond expected cycle',
        'recovery_rate': 0.50  # 50% recovery for abandoned WIP
    }
}


class BOMAnalyzer:
    """Analyzes BOM structure to calculate critical path and expected cycle time"""

    def __init__(self, bom_id: str, supabase_client=None):
        """
        Initialize BOM analyzer

        Args:
            bom_id: UUID of the BOM structure
            supabase_client: Optional Supabase client (will create if not provided)
        """
        self.bom_id = bom_id
        self.supabase = supabase_client or get_supabase_client()
        self.bom_data = None
        self.components = []
        self.critical_path = None
        self.expected_cycle_time = None

    def load_bom(self) -> bool:
        """Load BOM structure and components"""
        try:
            # Load BOM header
            bom_response = self.supabase.table('bom_structure').select('*').eq(
                'bom_id', self.bom_id
            ).execute()

            if not bom_response.data:
                return False

            self.bom_data = bom_response.data[0]

            # Load components
            components_response = self.supabase.table('bom_components').select('*').eq(
                'bom_id', self.bom_id
            ).order('lead_time_days', desc=True).execute()

            self.components = components_response.data if components_response.data else []

            return True

        except Exception as e:
            print(f"Error loading BOM: {e}")
            return False

    def calculate_critical_path(self) -> int:
        """
        Calculate expected cycle time from BOM critical path

        Critical path = longest component lead time + assembly time + buffer

        Returns:
            Expected cycle time in days
        """
        if not self.components:
            return 0

        # Find longest lead time (bottleneck component)
        max_lead_time = max(c['lead_time_days'] for c in self.components)

        # Add assembly time
        assembly_time = self.bom_data.get('assembly_time_days', 0) or 0

        # Add buffer (3 days standard)
        buffer_days = 3

        self.critical_path = max_lead_time
        self.expected_cycle_time = max_lead_time + assembly_time + buffer_days

        return self.expected_cycle_time

    def get_bottleneck_component(self) -> Optional[Dict]:
        """Identify component with longest lead time (bottleneck)"""
        if not self.components:
            return None

        return max(self.components, key=lambda x: x['lead_time_days'])

    def get_component_details(self) -> List[Dict]:
        """Get list of all components with lead times"""
        return self.components


class ComponentAvailabilityChecker:
    """Checks component availability at work order release date"""

    def __init__(self, company_id: str, supabase_client=None):
        """Initialize checker"""
        self.company_id = company_id
        self.supabase = supabase_client or get_supabase_client()

    def check_availability_at_release(
        self,
        work_order_id: str,
        bom_id: str,
        release_date: datetime
    ) -> Dict:
        """
        Check if all BOM components were available when work order was released

        This is forensic evidence for why work order is stuck

        Args:
            work_order_id: UUID of the work order
            bom_id: UUID of the BOM
            release_date: Date when work order was released

        Returns:
            Dictionary with availability status and bottleneck analysis
        """
        # Try to get from snapshot table first (if pre-calculated)
        snapshot_response = self.supabase.table(
            'component_availability_snapshots'
        ).select('*').eq('work_order_id', work_order_id).execute()

        if snapshot_response.data:
            return self._parse_snapshot_data(snapshot_response.data)

        # Otherwise, calculate from BOM and inventory snapshots
        return self._calculate_availability(bom_id, release_date)

    def _parse_snapshot_data(self, snapshots: List[Dict]) -> Dict:
        """Parse pre-calculated component availability snapshots"""
        availability_status = []

        for snap in snapshots:
            availability_status.append({
                'component': snap['component_item'],
                'required': float(snap.get('required_quantity', 0)),
                'available': float(snap.get('available_quantity', 0)),
                'shortage': float(snap.get('shortage_quantity', 0)),
                'lead_time_days': snap.get('lead_time_days', 0),
                'status': 'AVAILABLE' if snap.get('shortage_quantity', 0) <= 0 else 'SHORTAGE'
            })

        # Find bottleneck (shortage with longest lead time)
        shortages = [a for a in availability_status if a['status'] == 'SHORTAGE']
        bottleneck = max(shortages, key=lambda x: x['lead_time_days']) if shortages else None

        return {
            'components': availability_status,
            'all_available': len(shortages) == 0,
            'bottleneck_component': bottleneck,
            'can_start_production': len(shortages) == 0,
            'shortage_count': len(shortages)
        }

    def _calculate_availability(self, bom_id: str, release_date: datetime) -> Dict:
        """Calculate availability from BOM and inventory snapshots"""
        # Load BOM components
        bom_response = self.supabase.table('bom_components').select('*').eq(
            'bom_id', bom_id
        ).execute()

        if not bom_response.data:
            return {'components': [], 'all_available': True, 'bottleneck_component': None}

        components = bom_response.data
        availability_status = []

        for component in components:
            # Get inventory snapshot at release date
            inventory = self._get_inventory_at_date(
                component['component_item'],
                release_date
            )

            required_qty = float(component['quantity_required'])
            available_qty = float(inventory.get('available_quantity', 0)) if inventory else 0
            shortage_qty = max(0, required_qty - available_qty)

            availability_status.append({
                'component': component['component_item'],
                'required': required_qty,
                'available': available_qty,
                'shortage': shortage_qty,
                'lead_time_days': component['lead_time_days'],
                'status': 'AVAILABLE' if shortage_qty == 0 else 'SHORTAGE'
            })

        # Find bottleneck
        shortages = [a for a in availability_status if a['status'] == 'SHORTAGE']
        bottleneck = max(shortages, key=lambda x: x['lead_time_days']) if shortages else None

        return {
            'components': availability_status,
            'all_available': len(shortages) == 0,
            'bottleneck_component': bottleneck,
            'can_start_production': len(shortages) == 0,
            'shortage_count': len(shortages)
        }

    def _get_inventory_at_date(self, item_number: str, snapshot_date: datetime) -> Optional[Dict]:
        """Get inventory snapshot for item at specific date"""
        try:
            response = self.supabase.table('inventory_snapshots').select('*').eq(
                'company_id', self.company_id
            ).eq('item_number', item_number).eq(
                'snapshot_date', snapshot_date.date()
            ).execute()

            return response.data[0] if response.data else None

        except:
            return None


class ManufacturingDIOCalculator:
    """Calculate trapped capital for manufacturing companies using BOM analysis"""

    def __init__(self, company_id: str, analysis_date: datetime):
        """
        Initialize calculator

        Args:
            company_id: UUID of the manufacturing company
            analysis_date: Date of analysis (typically today)
        """
        self.company_id = company_id
        self.analysis_date = analysis_date
        self.supabase = get_supabase_client()
        self.work_orders = []
        self.subcontract_items = []
        self.quarantine_items = []
        self.results = {}

    def load_data(self) -> None:
        """Load all manufacturing-specific data"""
        self._load_work_orders()
        self._load_subcontract_items()
        self._load_quarantine_items()

    def _load_work_orders(self) -> None:
        """Load work orders for this company"""
        try:
            response = self.supabase.table('work_orders').select('*').eq(
                'company_id', self.company_id
            ).is_('actual_completion_date', 'null').execute()

            self.work_orders = response.data if response.data else []

        except Exception as e:
            print(f"Error loading work orders: {e}")
            self.work_orders = []

    def _load_subcontract_items(self) -> None:
        """Load subcontract items"""
        try:
            response = self.supabase.table('subcontract_items').select('*').eq(
                'company_id', self.company_id
            ).eq('status', 'AT_SUPPLIER').execute()

            self.subcontract_items = response.data if response.data else []

        except Exception as e:
            print(f"Error loading subcontract items: {e}")
            self.subcontract_items = []

    def _load_quarantine_items(self) -> None:
        """Load quarantine items"""
        try:
            response = self.supabase.table('quarantine_items').select('*').eq(
                'company_id', self.company_id
            ).eq('disposition', 'PENDING').execute()

            self.quarantine_items = response.data if response.data else []

        except Exception as e:
            print(f"Error loading quarantine items: {e}")
            self.quarantine_items = []

    def calculate_trapped_capital(self) -> Dict:
        """
        Main calculation entry point using BOM-based analysis

        Returns:
            Comprehensive trapped capital analysis with component cascade
        """
        results = {}

        # Work order analysis
        if self.work_orders:
            wo_result = self._calculate_work_order_delays()
            results['WORK_ORDER_DELAYS'] = wo_result

        # Subcontract analysis
        if self.subcontract_items:
            sub_result = self._calculate_subcontract_delays()
            results['SUBCONTRACT_DELAYS'] = sub_result

        # Quarantine analysis
        if self.quarantine_items:
            qc_result = self._calculate_quarantine_delays()
            results['QUARANTINE_DELAYS'] = qc_result

        # Aggregate
        summary = self._aggregate_results(results)

        return {
            'company_id': self.company_id,
            'company_type': 'MANUFACTURING',
            'analysis_date': self.analysis_date.isoformat(),
            'methodology': 'BOM critical path analysis with component availability verification',
            'total_dio_value': summary['total_dio_value'],
            'trapped_capital': summary['trapped_capital'],
            'recognized_losses': summary['recognized_losses'],
            'partial_recovery_gross': summary['partial_recovery_gross'],
            'partial_recovery_net': summary['partial_recovery_net'],
            'net_recovery': summary['net_recovery'],
            'recovery_rate': summary['recovery_rate'],
            'issues_breakdown': results,
            'component_cascade_analysis': summary.get('component_cascade', {}),
            'summary': summary
        }

    def _calculate_work_order_delays(self) -> Dict:
        """Calculate trapped capital in work orders using BOM critical path"""
        trapped = []
        normal = []
        component_cascade = {}

        checker = ComponentAvailabilityChecker(self.company_id, self.supabase)

        for wo in self.work_orders:
            bom_id = wo.get('bom_id')
            if not bom_id:
                continue  # Skip if no BOM

            # Get BOM and calculate expected cycle
            bom_analyzer = BOMAnalyzer(bom_id, self.supabase)
            if not bom_analyzer.load_bom():
                continue

            expected_cycle = bom_analyzer.calculate_critical_path()

            # Calculate actual days outstanding
            release_date = self._parse_date(wo['release_date'])
            days_outstanding = (self.analysis_date - release_date).days if release_date else 0

            amount = float(wo.get('total_cost', 0) or 0)

            # Check if within normal cycle or excess
            if days_outstanding <= expected_cycle:
                normal.append({
                    'work_order': wo,
                    'days_outstanding': days_outstanding,
                    'expected_cycle': expected_cycle,
                    'amount': amount,
                    'category': 'NORMAL_WIP'
                })
                continue

            # This is excess - check WHY
            excess_days = days_outstanding - expected_cycle

            # Check component availability at release
            availability = checker.check_availability_at_release(
                wo['work_order_id'],
                bom_id,
                release_date
            )

            if not availability['all_available']:
                bottleneck = availability['bottleneck_component']
                root_cause = (
                    f"Component shortage: {bottleneck['component']} was out of stock "
                    f"at release (LT: {bottleneck['lead_time_days']} days). "
                    f"Work order released prematurely without material availability check."
                )
                root_cause_category = 'COMPONENT_SHORTAGE'

                # Track component cascade
                comp_name = bottleneck['component']
                if comp_name not in component_cascade:
                    component_cascade[comp_name] = {
                        'component': comp_name,
                        'lead_time': bottleneck['lead_time_days'],
                        'work_orders_affected': [],
                        'total_trapped': 0
                    }
                component_cascade[comp_name]['work_orders_affected'].append(wo['work_order_number'])
                component_cascade[comp_name]['total_trapped'] += amount

            else:
                root_cause = (
                    f"All components were available at release but production never started. "
                    f"Investigate production scheduling, capacity constraints, or labor availability."
                )
                root_cause_category = 'SCHEDULING_ISSUE'

            trapped.append({
                'work_order': wo,
                'days_outstanding': days_outstanding,
                'expected_cycle': expected_cycle,
                'excess_days': excess_days,
                'amount': amount,
                'category': 'EXCESS_CYCLE',
                'root_cause': root_cause,
                'root_cause_category': root_cause_category,
                'bottleneck_component': availability.get('bottleneck_component'),
                'bom_critical_path': bom_analyzer.get_bottleneck_component()
            })

        trapped_amount = sum(t['amount'] for t in trapped)
        normal_amount = sum(n['amount'] for n in normal)

        return {
            'issue_type': 'WORK_ORDER_DELAYS',
            'description': 'Work orders beyond BOM expected cycle time',
            'methodology': 'BOM critical path analysis',
            'trapped_capital': trapped_amount,
            'normal_wip': normal_amount,
            'trapped_count': len(trapped),
            'normal_count': len(normal),
            'avg_excess_days': sum(t['excess_days'] for t in trapped) / len(trapped) if trapped else 0,
            'component_cascade_analysis': component_cascade,
            'trapped_details': trapped[:100],
            'recovery_type': 'TRAPPED_CAPITAL'
        }

    def _calculate_subcontract_delays(self) -> Dict:
        """Calculate trapped capital in subcontract items"""
        benchmark = MANUFACTURING_BENCHMARKS['subcontract_standard']
        threshold = benchmark['threshold_days']

        trapped = []
        normal = []

        for item in self.subcontract_items:
            sent_date = self._parse_date(item.get('sent_date'))
            days_at_supplier = (self.analysis_date - sent_date).days if sent_date else 0

            amount = float(item.get('total_value', 0) or 0)

            if days_at_supplier > threshold:
                trapped.append({
                    'item': item,
                    'days_at_supplier': days_at_supplier,
                    'amount': amount,
                    'excess_days': days_at_supplier - benchmark['standard_days']
                })
            else:
                normal.append({
                    'item': item,
                    'days_at_supplier': days_at_supplier,
                    'amount': amount
                })

        return {
            'issue_type': 'SUBCONTRACT_DELAYS',
            'description': 'Items at outside processor beyond normal cycle',
            'benchmark': f"{benchmark['standard_days']} days standard, {threshold} days threshold",
            'trapped_capital': sum(t['amount'] for t in trapped),
            'normal_operations': sum(n['amount'] for n in normal),
            'trapped_count': len(trapped),
            'normal_count': len(normal),
            'avg_excess_days': sum(t['excess_days'] for t in trapped) / len(trapped) if trapped else 0,
            'recovery_type': 'TRAPPED_CAPITAL'
        }

    def _calculate_quarantine_delays(self) -> Dict:
        """Calculate trapped capital in quarantine with pass/fail split"""
        total_amount = sum(float(q.get('total_value', 0) or 0) for q in self.quarantine_items)

        # Estimate pass rate (70% for complex, 85% for routine)
        avg_pass_rate = 0.70  # Conservative estimate

        passed_amount = total_amount * avg_pass_rate
        failed_amount = total_amount * (1 - avg_pass_rate)

        return {
            'issue_type': 'QUARANTINE_DELAYS',
            'description': 'Quality inspection hold - disposition pending',
            'total_value': total_amount,
            'expected_pass_amount': passed_amount,
            'expected_fail_amount': failed_amount,
            'pass_rate_assumption': avg_pass_rate,
            'trapped_capital': passed_amount,  # Items that will pass
            'recognized_losses': failed_amount,  # Items that will fail
            'item_count': len(self.quarantine_items),
            'recovery_type': 'SPLIT'
        }

    def _aggregate_results(self, results: Dict) -> Dict:
        """Aggregate all manufacturing results"""
        total_trapped = sum(r.get('trapped_capital', 0) for r in results.values())
        total_losses = sum(r.get('recognized_losses', 0) for r in results.values())
        total_normal = sum(r.get('normal_wip', 0) + r.get('normal_operations', 0) for r in results.values())

        # Collect component cascade data
        component_cascade = {}
        for result in results.values():
            if 'component_cascade_analysis' in result:
                component_cascade.update(result['component_cascade_analysis'])

        total_dio_value = total_trapped + total_losses + total_normal
        net_recovery = total_trapped
        recovery_rate = net_recovery / total_dio_value if total_dio_value > 0 else 0

        return {
            'total_dio_value': total_dio_value,
            'trapped_capital': total_trapped,
            'recognized_losses': total_losses,
            'partial_recovery_gross': 0,  # No partial recovery in current implementation
            'partial_recovery_net': 0,
            'normal_operations': total_normal,
            'net_recovery': net_recovery,
            'recovery_rate': recovery_rate,
            'component_cascade': component_cascade,
            'total_count': sum(
                r.get('trapped_count', 0) + r.get('normal_count', 0) + r.get('item_count', 0)
                for r in results.values()
            )
        }

    def _parse_date(self, date_value) -> Optional[datetime]:
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
