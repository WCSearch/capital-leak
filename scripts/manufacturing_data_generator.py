"""
Manufacturing-Specific Data Generation

Helper module to generate BOM structures, work orders, component snapshots,
and component shortages for manufacturing companies (SAP and Oracle datasets).

Author: Capital Leak Analysis Team
Date: 2025-01-10
"""

import uuid
import random
from datetime import datetime, timedelta
import pandas as pd


class ManufacturingDataGenerator:
    """Generates manufacturing-specific data (BOMs, work orders, component tracking)"""

    def __init__(self, dataset_name, config, analysis_date):
        """
        Initialize manufacturing data generator

        Args:
            dataset_name: 'sap' or 'oracle'
            config: Dataset configuration dict
            analysis_date: Analysis date for the dataset
        """
        self.dataset_name = dataset_name
        self.config = config
        self.analysis_date = analysis_date

    def generate_bom_and_work_orders(self, company_id):
        """
        Generate complete BOM structures and work orders with component availability tracking

        Returns:
            tuple: (bom_structures, bom_components, work_orders, component_snapshots,
                   component_shortages, inventory_snapshots)
        """
        print("\n[MANUFACTURING] Generating BOM structures and work orders...")

        # Product definitions based on industry
        products = self._get_product_definitions()

        bom_structures = []
        bom_components = []
        work_orders = []
        component_snapshots = []
        component_shortages = []
        inventory_snapshots = []

        # Track component shortages we'll create
        shortage_scenarios = self._get_component_shortage_scenarios()

        # Generate BOMs for each product
        print(f"   → Creating {len(products)} product BOMs...")
        for product in products:
            bom_id = str(uuid.uuid4())

            # Create BOM header
            expected_cycle_time = max(c['lead_time_days'] for c in product['components']) + product['assembly_time_days'] + 3

            bom_structures.append({
                'bom_id': bom_id,
                'company_id': company_id,
                'parent_item': product['product_code'],
                'parent_item_description': product['product_description'],
                'assembly_time_days': product['assembly_time_days'],
                'expected_cycle_time': expected_cycle_time
            })

            # Create BOM components
            for comp in product['components']:
                component_id = str(uuid.uuid4())
                is_critical = (comp['lead_time_days'] == max(c['lead_time_days'] for c in product['components']))

                bom_components.append({
                    'component_id': component_id,
                    'bom_id': bom_id,
                    'company_id': company_id,
                    'component_item': comp['component_code'],
                    'component_description': comp['component_description'],
                    'quantity_required': comp['quantity'],
                    'unit_cost': comp['unit_cost'],
                    'lead_time_days': comp['lead_time_days'],
                    'is_critical_path': is_critical
                })

        print(f"   ✓ Created {len(bom_structures)} BOMs with {len(bom_components)} total components")

        # Generate work orders
        print(f"   → Creating work orders...")
        num_work_orders = 156 if self.dataset_name == 'oracle' else 140

        # Create work orders with mix of normal and delayed
        for i in range(num_work_orders):
            wo_id = str(uuid.uuid4())
            wo_number = f"WO-{random.randint(100000, 999999)}"

            # Select random product
            product = random.choice(products)
            bom_id = next(b['bom_id'] for b in bom_structures if b['parent_item'] == product['product_code'])
            expected_cycle = next(b['expected_cycle_time'] for b in bom_structures if b['parent_item'] == product['product_code'])

            # Release date - spread across the year
            release_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 364))
            days_outstanding = (self.analysis_date - release_date).days

            quantity_ordered = random.randint(1, 20)
            total_cost = quantity_ordered * product['product_unit_cost']

            # Determine status based on cycle time and component availability
            # 34% will be normal WIP (within cycle), 66% will be delayed (beyond cycle)
            is_delayed = i < int(num_work_orders * 0.66)

            if is_delayed:
                # This work order is delayed - check why
                # 84% due to component shortage, 16% due to scheduling issues
                has_component_shortage = random.random() < 0.84

                if has_component_shortage:
                    # Select a component shortage scenario
                    shortage = random.choice(shortage_scenarios)

                    # Check if release date falls within shortage period
                    shortage_start = shortage['shortage_start']
                    shortage_end = shortage.get('shortage_end', self.analysis_date)

                    if release_date >= shortage_start - timedelta(days=30):
                        # This WO is affected by this shortage
                        status = 'RELEASED'  # Released but can't start due to shortage

                        # Create component availability snapshot showing shortage
                        for comp in product['components']:
                            snapshot_id = str(uuid.uuid4())

                            if comp['component_code'] == shortage['component']:
                                # This component is short
                                required_qty = comp['quantity'] * quantity_ordered
                                available_qty = 0  # None available
                                shortage_qty = required_qty
                                is_bottleneck = True
                            else:
                                # Other components are available
                                required_qty = comp['quantity'] * quantity_ordered
                                available_qty = required_qty + random.randint(10, 50)
                                shortage_qty = 0
                                is_bottleneck = False

                            component_snapshots.append({
                                'snapshot_id': snapshot_id,
                                'company_id': company_id,
                                'work_order_id': wo_id,
                                'component_item': comp['component_code'],
                                'snapshot_date': release_date.strftime('%Y-%m-%d'),
                                'required_quantity': required_qty,
                                'available_quantity': available_qty,
                                'shortage_quantity': shortage_qty,
                                'lead_time_days': comp['lead_time_days'],
                                'is_bottleneck': is_bottleneck
                            })
                    else:
                        # Not affected by shortage - scheduling issue
                        status = 'RELEASED'
                        self._create_normal_snapshots(component_snapshots, company_id, wo_id, product, quantity_ordered, release_date)
                else:
                    # Scheduling issue - all components available
                    status = 'RELEASED'
                    self._create_normal_snapshots(component_snapshots, company_id, wo_id, product, quantity_ordered, release_date)
            else:
                # Normal WIP - components available, within cycle time
                status = 'IN_PROGRESS'
                self._create_normal_snapshots(component_snapshots, company_id, wo_id, product, quantity_ordered, release_date)

            work_orders.append({
                'work_order_id': wo_id,
                'company_id': company_id,
                'work_order_number': wo_number,
                'product_item': product['product_code'],
                'bom_id': bom_id,
                'release_date': release_date.strftime('%Y-%m-%d'),
                'planned_completion_date': (release_date + timedelta(days=expected_cycle)).strftime('%Y-%m-%d'),
                'actual_completion_date': None,
                'quantity_ordered': quantity_ordered,
                'quantity_completed': 0 if status == 'RELEASED' else random.randint(0, int(quantity_ordered * 0.7)),
                'status': status,
                'total_cost': total_cost,
                'days_outstanding': days_outstanding
            })

        print(f"   ✓ Created {len(work_orders)} work orders")
        print(f"   ✓ Created {len(component_snapshots)} component availability snapshots")

        # Generate component shortage records
        print(f"   → Creating component shortage records...")
        for shortage in shortage_scenarios:
            shortage_id = str(uuid.uuid4())

            # Count affected work orders
            affected_wos = [wo for wo in work_orders
                          if any(snap['component_item'] == shortage['component'] and snap['is_bottleneck']
                                for snap in component_snapshots if snap['work_order_id'] == wo['work_order_id'])]

            total_value_trapped = sum(wo['total_cost'] for wo in affected_wos)

            component_shortages.append({
                'shortage_id': shortage_id,
                'company_id': company_id,
                'component_item': shortage['component'],
                'shortage_start_date': shortage['shortage_start'].strftime('%Y-%m-%d'),
                'shortage_end_date': shortage['shortage_end'].strftime('%Y-%m-%d') if shortage['shortage_end'] else None,
                'normal_lead_time_days': shortage['normal_lead_time'],
                'extended_lead_time_days': shortage['extended_lead_time'],
                'work_orders_affected': len(affected_wos),
                'total_value_trapped': total_value_trapped,
                'reason': shortage['reason'],
                'status': 'RESOLVED' if shortage['shortage_end'] else 'ACTIVE'
            })

        print(f"   ✓ Created {len(component_shortages)} component shortage records")

        # Generate inventory snapshots for component availability checking
        print(f"   → Creating inventory snapshots...")
        # Create snapshots for all work order release dates
        for wo in work_orders[:50]:  # Limit to first 50 for performance
            release_date = datetime.strptime(wo['release_date'], '%Y-%m-%d')

            # Get product and components
            product = next(p for p in products if p['product_code'] == wo['product_item'])

            for comp in product['components']:
                snapshot_id = str(uuid.uuid4())

                # Check if this component was in shortage at release date
                comp_shortages = [s for s in shortage_scenarios if s['component'] == comp['component_code']]
                in_shortage = False

                for shortage in comp_shortages:
                    if shortage['shortage_start'] <= release_date <= (shortage['shortage_end'] or self.analysis_date):
                        in_shortage = True
                        break

                if in_shortage:
                    on_hand_qty = 0
                    reserved_qty = 0
                    available_qty = 0
                else:
                    on_hand_qty = random.randint(100, 500)
                    reserved_qty = random.randint(0, int(on_hand_qty * 0.3))
                    available_qty = on_hand_qty - reserved_qty

                inventory_snapshots.append({
                    'snapshot_id': snapshot_id,
                    'company_id': company_id,
                    'item_number': comp['component_code'],
                    'snapshot_date': release_date.strftime('%Y-%m-%d'),
                    'on_hand_quantity': on_hand_qty,
                    'reserved_quantity': reserved_qty,
                    'available_quantity': available_qty,
                    'unit_cost': comp['unit_cost'],
                    'total_value': available_qty * comp['unit_cost']
                })

        print(f"   ✓ Created {len(inventory_snapshots)} inventory snapshots")

        return (bom_structures, bom_components, work_orders, component_snapshots,
                component_shortages, inventory_snapshots)

    def generate_subcontract_items(self, company_id):
        """Generate subcontract items (items at outside processors)"""
        print("\n[MANUFACTURING] Generating subcontract items...")

        subcontract_items = []
        num_items = 89 if self.dataset_name == 'oracle' else 75

        suppliers = ['Ace Machining', 'Precision Coating Co', 'Metro Heat Treat',
                    'Quality Plating Inc', 'Advanced Welding Services']

        for i in range(num_items):
            subcontract_id = str(uuid.uuid4())
            po_number = f"SUB-{random.randint(100000, 999999)}"
            item_number = f"COMP-{random.randint(1000, 9999)}"

            sent_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 300))
            days_at_supplier = (self.analysis_date - sent_date).days

            # 60% beyond threshold (45 days), 40% normal
            standard_days = 30
            threshold_days = 45

            if i < int(num_items * 0.60):
                # Beyond threshold - ensure sent date is old enough
                sent_date = self.analysis_date - timedelta(days=random.randint(45, 180))
                days_at_supplier = (self.analysis_date - sent_date).days
                status = 'AT_SUPPLIER'
                actual_return_date = None
            else:
                # Normal cycle
                days_at_supplier = random.randint(1, 44)
                sent_date = self.analysis_date - timedelta(days=days_at_supplier)
                status = 'AT_SUPPLIER'
                actual_return_date = None

            expected_return_date = sent_date + timedelta(days=standard_days)
            quantity = random.randint(10, 200)
            unit_value = random.uniform(50, 500)
            total_value = round(quantity * unit_value, 2)

            subcontract_items.append({
                'subcontract_id': subcontract_id,
                'company_id': company_id,
                'po_number': po_number,
                'item_number': item_number,
                'supplier_name': random.choice(suppliers),
                'sent_date': sent_date.strftime('%Y-%m-%d'),
                'expected_return_date': expected_return_date.strftime('%Y-%m-%d'),
                'actual_return_date': actual_return_date,
                'quantity': quantity,
                'total_value': total_value,
                'days_at_supplier': days_at_supplier,
                'status': status
            })

        print(f"   ✓ Created {len(subcontract_items)} subcontract items")
        return subcontract_items

    def generate_quarantine_items(self, company_id):
        """Generate quarantine/quality hold items"""
        print("\n[MANUFACTURING] Generating quarantine items...")

        quarantine_items = []

        # Oracle: 70 releasable + 42 failed = 112 total
        # SAP: similar mix
        if self.dataset_name == 'oracle':
            num_pending = 112
        else:
            num_pending = 95

        for i in range(num_pending):
            quarantine_id = str(uuid.uuid4())
            item_number = f"ITEM-{random.randint(1000, 9999)}"
            lot_number = f"LOT-{random.randint(100000, 999999)}"

            quarantine_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 300))
            days_in_quarantine = (self.analysis_date - quarantine_date).days

            # Mix of routine and complex inspections
            if random.random() < 0.6:
                inspection_type = 'ROUTINE'
                expected_pass_rate = 0.85
            else:
                inspection_type = 'MRB_REQUIRED'
                expected_pass_rate = 0.70

            quantity = random.randint(10, 500)
            unit_value = random.uniform(20, 300)
            total_value = round(quantity * unit_value, 2)

            quarantine_items.append({
                'quarantine_id': quarantine_id,
                'company_id': company_id,
                'item_number': item_number,
                'lot_number': lot_number,
                'quarantine_date': quarantine_date.strftime('%Y-%m-%d'),
                'inspection_type': inspection_type,
                'quantity': quantity,
                'total_value': total_value,
                'days_in_quarantine': days_in_quarantine,
                'expected_pass_rate': expected_pass_rate,
                'disposition': 'PENDING'
            })

        print(f"   ✓ Created {len(quarantine_items)} quarantine items")
        return quarantine_items

    def _get_product_definitions(self):
        """Get product definitions based on industry"""
        if self.dataset_name == 'oracle':
            # Industrial equipment manufacturing
            return [
                {
                    'product_code': 'PUMP-5000',
                    'product_description': 'Industrial Centrifugal Pump 5000 Series',
                    'assembly_time_days': 5,
                    'product_unit_cost': 4500,
                    'components': [
                        {'component_code': 'MOTOR-A', 'component_description': 'Electric Motor 5HP', 'quantity': 1, 'unit_cost': 450, 'lead_time_days': 15},
                        {'component_code': 'HOUSING-B', 'component_description': 'Cast Iron Housing', 'quantity': 1, 'unit_cost': 320, 'lead_time_days': 8},
                        {'component_code': 'IMPELLER-C', 'component_description': 'Stainless Steel Impeller', 'quantity': 1, 'unit_cost': 1200, 'lead_time_days': 22},
                        {'component_code': 'GASKET-D', 'component_description': 'Rubber Gasket Set', 'quantity': 2, 'unit_cost': 25, 'lead_time_days': 3},
                        {'component_code': 'FASTENER-E', 'component_description': 'Fastener Kit', 'quantity': 50, 'unit_cost': 2, 'lead_time_days': 1}
                    ]
                },
                {
                    'product_code': 'VALVE-3000',
                    'product_description': 'High Pressure Control Valve',
                    'assembly_time_days': 3,
                    'product_unit_cost': 3200,
                    'components': [
                        {'component_code': 'BODY-F', 'component_description': 'Valve Body', 'quantity': 1, 'unit_cost': 680, 'lead_time_days': 12},
                        {'component_code': 'ACTUATOR-G', 'component_description': 'Pneumatic Actuator', 'quantity': 1, 'unit_cost': 890, 'lead_time_days': 18},
                        {'component_code': 'CONTROL-BOARD-F', 'component_description': 'Electronic Control Board', 'quantity': 1, 'unit_cost': 450, 'lead_time_days': 30},
                        {'component_code': 'SEAL-H', 'component_description': 'High Pressure Seal', 'quantity': 3, 'unit_cost': 45, 'lead_time_days': 5}
                    ]
                },
                {
                    'product_code': 'COMPRESSOR-2000',
                    'product_description': 'Rotary Screw Air Compressor',
                    'assembly_time_days': 7,
                    'product_unit_cost': 8900,
                    'components': [
                        {'component_code': 'MOTOR-A', 'component_description': 'Electric Motor 25HP', 'quantity': 1, 'unit_cost': 950, 'lead_time_days': 15},
                        {'component_code': 'SCREW-I', 'component_description': 'Compression Screw Assembly', 'quantity': 1, 'unit_cost': 2400, 'lead_time_days': 25},
                        {'component_code': 'TANK-J', 'component_description': 'Pressure Tank', 'quantity': 1, 'unit_cost': 1200, 'lead_time_days': 10},
                        {'component_code': 'CONTROL-PANEL-K', 'component_description': 'Control Panel Assembly', 'quantity': 1, 'unit_cost': 780, 'lead_time_days': 20}
                    ]
                }
            ]
        else:  # SAP - electronics manufacturing
            return [
                {
                    'product_code': 'PCB-1000',
                    'product_description': 'Control Board Assembly',
                    'assembly_time_days': 2,
                    'product_unit_cost': 850,
                    'components': [
                        {'component_code': 'PCB-BLANK', 'component_description': 'Blank PCB', 'quantity': 1, 'unit_cost': 45, 'lead_time_days': 8},
                        {'component_code': 'IC-CHIP-A', 'component_description': 'Microcontroller', 'quantity': 1, 'unit_cost': 180, 'lead_time_days': 45},
                        {'component_code': 'RESISTOR-B', 'component_description': 'Resistor Pack', 'quantity': 50, 'unit_cost': 0.50, 'lead_time_days': 3},
                        {'component_code': 'CAPACITOR-C', 'component_description': 'Capacitor Pack', 'quantity': 30, 'unit_cost': 1.20, 'lead_time_days': 3}
                    ]
                },
                {
                    'product_code': 'DISPLAY-500',
                    'product_description': 'LCD Display Module',
                    'assembly_time_days': 1,
                    'product_unit_cost': 320,
                    'components': [
                        {'component_code': 'LCD-PANEL', 'component_description': 'LCD Panel', 'quantity': 1, 'unit_cost': 120, 'lead_time_days': 30},
                        {'component_code': 'DRIVER-IC', 'component_description': 'Display Driver IC', 'quantity': 1, 'unit_cost': 45, 'lead_time_days': 20},
                        {'component_code': 'CONNECTOR-D', 'component_description': 'Ribbon Connector', 'quantity': 1, 'unit_cost': 8, 'lead_time_days': 5}
                    ]
                }
            ]

    def _get_component_shortage_scenarios(self):
        """Get component shortage scenarios"""
        if self.dataset_name == 'oracle':
            return [
                {
                    'component': 'IMPELLER-C',
                    'shortage_start': datetime(2024, 3, 8),
                    'shortage_end': datetime(2024, 6, 15),
                    'normal_lead_time': 22,
                    'extended_lead_time': 90,
                    'reason': 'Supplier quality issue - extended lead time'
                },
                {
                    'component': 'CONTROL-BOARD-F',
                    'shortage_start': datetime(2024, 7, 1),
                    'shortage_end': None,  # Ongoing
                    'normal_lead_time': 30,
                    'extended_lead_time': 120,
                    'reason': 'Supplier bankruptcy - alternative source qualification'
                },
                {
                    'component': 'MOTOR-A',
                    'shortage_start': datetime(2024, 5, 20),
                    'shortage_end': datetime(2024, 8, 10),
                    'normal_lead_time': 15,
                    'extended_lead_time': 60,
                    'reason': 'Supplier capacity constraints'
                }
            ]
        else:  # SAP
            return [
                {
                    'component': 'IC-CHIP-A',
                    'shortage_start': datetime(2024, 2, 1),
                    'shortage_end': datetime(2024, 9, 30),
                    'normal_lead_time': 45,
                    'extended_lead_time': 180,
                    'reason': 'Global semiconductor shortage'
                },
                {
                    'component': 'LCD-PANEL',
                    'shortage_start': datetime(2024, 6, 15),
                    'shortage_end': datetime(2024, 10, 20),
                    'normal_lead_time': 30,
                    'extended_lead_time': 90,
                    'reason': 'Factory fire at supplier'
                }
            ]

    def _create_normal_snapshots(self, component_snapshots, company_id, wo_id, product, quantity_ordered, release_date):
        """Create component snapshots showing all components available"""
        for comp in product['components']:
            snapshot_id = str(uuid.uuid4())
            required_qty = comp['quantity'] * quantity_ordered
            available_qty = required_qty + random.randint(10, 100)

            component_snapshots.append({
                'snapshot_id': snapshot_id,
                'company_id': company_id,
                'work_order_id': wo_id,
                'component_item': comp['component_code'],
                'snapshot_date': release_date.strftime('%Y-%m-%d'),
                'required_quantity': required_qty,
                'available_quantity': available_qty,
                'shortage_quantity': 0,
                'lead_time_days': comp['lead_time_days'],
                'is_bottleneck': False
            })
