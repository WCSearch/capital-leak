"""
Generate Synthetic ERP Data for Working Capital Analysis Dashboard

This script creates realistic ERP data for multiple companies across different
ERP systems (SAP, Infor, Oracle), including intentional issues for testing
the dashboard's forensic capabilities.

Supports:
- SAP ECC 6.0 (TechMfg Industries - Electronics Manufacturing)
- Infor CloudSuite Distribution (AmeriParts Distribution - Automotive Parts)
- Oracle E-Business Suite (PrecisionTech Manufacturing - Industrial Equipment)

Author: Capital Leak Analysis Team
Date: 2025-01-07
"""

import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import uuid
import json
import random
import os
import argparse
from pathlib import Path
from manufacturing_data_generator import ManufacturingDataGenerator

# Set random seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)

# Initialize Faker
fake = Faker()

# Dataset configurations
DATASET_CONFIGS = {
    'sap': {
        'company_name': 'TechMfg Industries',
        'industry': 'Electronics Manufacturing',
        'erp_system': 'SAP ECC 6.0',
        'annual_revenue': 85000000,
        'dso_transactions': 2500,
        'dio_items': 800,
        'dpo_invoices': 1800,
        'output_dir': 'data/synthetic/sap',

        # GL Accounts
        'gl_ar': '1300000',
        'gl_ar_name': 'Accounts Receivable',
        'gl_inventory_rm': '1400000',
        'gl_inventory_rm_name': 'Raw Materials Inventory',
        'gl_inventory_fg': '1410000',
        'gl_inventory_fg_name': 'Finished Goods Inventory',
        'gl_ap': '2100000',
        'gl_ap_name': 'Accounts Payable',

        # ERP-specific details
        'modules': {
            'sales': 'SD',
            'materials': 'MM',
            'finance': 'FI',
            'workflow': 'WF',
            'quality': 'QM'
        },
        'transaction_prefixes': {
            'invoice': 'INV',
            'material': 'MAT',
            'po': 'PO',
            'ap_invoice': 'APINV'
        },
        'event_types': {
            'order_created': 'ORDER_CREATED',
            'shipped': 'SHIPPED',
            'billed': 'BILLED',
            'payment_received': 'PAYMENT_RECEIVED',
            'credit_hold': 'CREDIT_HOLD_APPLIED',
            'approval_triggered': 'APPROVAL_TRIGGERED',
            'goods_receipt': 'GOODS_RECEIPT',
            'valuation_posted': 'VALUATION_POSTED',
            'quality_hold': 'QUALITY_HOLD_APPLIED',
            'goods_issue': 'GOODS_ISSUE',
            'invoice_received': 'INVOICE_RECEIVED',
            'matching_completed': 'MATCHING_COMPLETED',
            'variance_detected': 'VARIANCE_DETECTED',
            'payment_released': 'PAYMENT_RELEASED'
        },

        # Issue dates
        'issue_dates': {
            'billing_trigger_disabled': datetime(2024, 3, 17),
            'approver_left_ar': datetime(2024, 6, 15),
            'credit_policy_change': datetime(2024, 8, 1),
            'valuation_issue_start': datetime(2024, 5, 12),
            'approver_left_ap': datetime(2024, 7, 22)
        },
        'approver_names': {
            'ar': 'BWILSON',
            'ap': 'JSMITH'
        }
    },

    'infor': {
        'company_name': 'AmeriParts Distribution',
        'industry': 'Automotive Parts Wholesale Distribution',
        'erp_system': 'Infor CloudSuite Distribution',
        'annual_revenue': 120000000,
        'dso_transactions': 3200,
        'dio_items': 1200,
        'dpo_invoices': 2400,
        'output_dir': 'data/synthetic/infor',

        # GL Accounts (Infor-specific)
        'gl_ar': '11200',
        'gl_ar_name': 'Accounts Receivable - Trade',
        'gl_inventory_rm': '13000',
        'gl_inventory_rm_name': 'Finished Goods',
        'gl_inventory_fg': '13100',
        'gl_inventory_fg_name': 'Parts in Transit',
        'gl_ap': '21000',
        'gl_ap_name': 'Accounts Payable - Trade',

        # ERP-specific details
        'modules': {
            'sales': 'OE',
            'materials': 'IC',
            'finance': 'AR/AP',
            'workflow': 'WF',
            'quality': 'QC'
        },
        'transaction_prefixes': {
            'invoice': 'INV',
            'material': 'PART',
            'po': 'PO',
            'ap_invoice': 'APINV'
        },
        'event_types': {
            'order_created': 'ORDER_ENTERED',
            'shipped': 'SHIPMENT_CONFIRMED',
            'billed': 'INVOICE_POSTED',
            'payment_received': 'PAYMENT_RECEIVED',
            'credit_hold': 'CREDIT_HOLD_APPLIED',
            'approval_triggered': 'CREDIT_CHECK_INITIATED',
            'goods_receipt': 'RECEIPT_POSTED',
            'valuation_posted': 'INVENTORY_VALUED',
            'quality_hold': 'CYCLE_COUNT_VARIANCE',
            'goods_issue': 'PICK_CONFIRMED',
            'invoice_received': 'INVOICE_MATCHED',
            'matching_completed': 'THREE_WAY_MATCH_COMPLETE',
            'variance_detected': 'MATCHING_EXCEPTION',
            'payment_released': 'PAYMENT_PROCESSED'
        },

        # Issue dates
        'issue_dates': {
            'billing_trigger_disabled': datetime(2024, 3, 15),
            'approver_left_ar': datetime(2024, 6, 8),
            'credit_policy_change': datetime(2024, 3, 15),  # System upgrade date
            'valuation_issue_start': datetime(2024, 4, 22),
            'approver_left_ap': datetime(2024, 2, 12)
        },
        'approver_names': {
            'ar': 'CREDIT_MODULE',
            'ap': 'FREIGHT_MATCHING'
        }
    },

    'oracle': {
        'company_name': 'PrecisionTech Manufacturing',
        'industry': 'Industrial Equipment Manufacturing',
        'erp_system': 'Oracle E-Business Suite R12.2',
        'annual_revenue': 95000000,
        'dso_transactions': 1800,
        'dio_items': 900,
        'dpo_invoices': 1600,
        'output_dir': 'data/synthetic/oracle',

        # GL Accounts (Oracle-specific)
        'gl_ar': '1120',
        'gl_ar_name': 'Accounts Receivable',
        'gl_inventory_rm': '1510',
        'gl_inventory_rm_name': 'Raw Materials',
        'gl_inventory_fg': '1520',
        'gl_inventory_fg_name': 'Work in Process',
        'gl_ap': '2100',
        'gl_ap_name': 'Accounts Payable - Trade',

        # ERP-specific details
        'modules': {
            'sales': 'AR',
            'materials': 'INV',
            'finance': 'GL',
            'workflow': 'AME',
            'quality': 'QA'
        },
        'transaction_prefixes': {
            'invoice': 'INV',
            'material': 'ITEM',
            'po': 'PO',
            'ap_invoice': 'APINV'
        },
        'event_types': {
            'order_created': 'ORDER_BOOKED',
            'shipped': 'SHIP_CONFIRM',
            'billed': 'INVOICE_VALIDATED',
            'payment_received': 'RECEIPT_APPLIED',
            'credit_hold': 'CREDIT_HOLD',
            'approval_triggered': 'MILESTONE_ACHIEVED',
            'goods_receipt': 'RECEIPT_CREATED',
            'valuation_posted': 'COST_POSTED',
            'quality_hold': 'INSPECTION_FAILED',
            'goods_issue': 'WIP_ISSUE',
            'invoice_received': 'INVOICE_VALIDATED',
            'matching_completed': 'MATCHED_TO_PO',
            'variance_detected': 'PO_CHANGE_NOT_CLOSED',
            'payment_released': 'PAYMENT_CREATED'
        },

        # Issue dates
        'issue_dates': {
            'billing_trigger_disabled': datetime(2024, 4, 1),
            'approver_left_ar': datetime(2024, 5, 15),
            'credit_policy_change': datetime(2024, 4, 1),  # Progress billing issue
            'valuation_issue_start': datetime(2024, 3, 8),
            'approver_left_ap': datetime(2024, 3, 25)
        },
        'approver_names': {
            'ar': 'PROJECT_MANAGER',
            'ap': 'BUYER_APPROVAL'
        }
    }
}

# Analysis date (constant across all datasets)
ANALYSIS_DATE = datetime(2025, 1, 7)
PERIOD_START = datetime(2024, 1, 1)
PERIOD_END = datetime(2024, 12, 31)


class SyntheticDataGenerator:
    """Generator for synthetic ERP data"""

    def __init__(self, dataset_name):
        """Initialize generator with dataset configuration"""
        if dataset_name not in DATASET_CONFIGS:
            raise ValueError(f"Unknown dataset: {dataset_name}. Choose from: {list(DATASET_CONFIGS.keys())}")

        self.dataset_name = dataset_name
        self.config = DATASET_CONFIGS[dataset_name]
        self.output_dir = Path(self.config['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Print header
        print("=" * 80)
        print(f"SYNTHETIC {self.config['erp_system'].upper()} DATA GENERATOR")
        print("=" * 80)
        print(f"Company: {self.config['company_name']}")
        print(f"Industry: {self.config['industry']}")
        print(f"ERP System: {self.config['erp_system']}")
        print(f"Annual Revenue: ${self.config['annual_revenue']:,.0f}")
        print(f"Analysis Date: {ANALYSIS_DATE.strftime('%Y-%m-%d')}")
        print(f"Period: {PERIOD_START.strftime('%Y-%m-%d')} to {PERIOD_END.strftime('%Y-%m-%d')}")
        print(f"Random Seed: {RANDOM_SEED}")
        print("=" * 80)

    def generate_company_data(self):
        """Generate companies.csv"""
        print("\n[1/7] Generating companies.csv...")

        company_id = str(uuid.uuid4())

        # Determine company type based on dataset
        company_type = 'DISTRIBUTION' if self.dataset_name == 'infor' else 'MANUFACTURING'

        df = pd.DataFrame([{
            'company_id': company_id,
            'company_name': self.config['company_name'],
            'company_type': company_type,
            'industry': self.config['industry'],
            'erp_system': self.config['erp_system'],
            'revenue_annual': self.config['annual_revenue'],
            'analysis_date': ANALYSIS_DATE.strftime('%Y-%m-%d')
        }])

        output_path = self.output_dir / "companies.csv"
        df.to_csv(output_path, index=False)
        print(f"   ✓ Created {output_path} (1 row)")
        print(f"      - Company Type: {company_type}")
        print(f"      - Industry: {self.config['industry']}")

        return company_id

    def generate_dso_transactions(self, company_id):
        """Generate DSO (Accounts Receivable) transactions with intentional issues"""
        print("\n[2/7] Generating DSO transactions...")

        transactions = []
        event_logs = []

        # Issue counts (adjusted per dataset)
        target_counts = self._get_dso_issue_counts()
        issue_counts = {key: 0 for key in target_counts.keys()}

        # Generate customer list (scaled to volume)
        num_customers = max(30, int(self.config['dso_transactions'] / 50))
        customers = [fake.company() for _ in range(num_customers)]

        for i in range(self.config['dso_transactions']):
            trans_id = str(uuid.uuid4())
            customer = random.choice(customers)

            # Transaction date
            trans_date = PERIOD_START + timedelta(days=random.randint(0, 364))
            payment_terms = random.choice([30, 45, 60])
            due_date = trans_date + timedelta(days=payment_terms)
            days_outstanding = (ANALYSIS_DATE - trans_date).days

            # Amount (scale by industry)
            amount = self._generate_dso_amount()

            # Default status
            status = "OPEN"
            erp_metadata = {
                "payment_terms_days": payment_terms,
                "credit_hold": False,
                "dispute_flag": False
            }

            # Inject issues based on dataset
            issue_data = self._inject_dso_issue(
                i, trans_id, company_id, customer, trans_date,
                due_date, amount, issue_counts, target_counts
            )

            if issue_data:
                status = issue_data['status']
                event_logs.extend(issue_data['events'])
                if 'metadata' in issue_data:
                    erp_metadata.update(issue_data['metadata'])
            else:
                # Normal transactions
                outstanding, events = self._generate_normal_dso_flow(
                    trans_id, company_id, customer, trans_date, amount,
                    days_outstanding, payment_terms
                )
                event_logs.extend(events)

            # Create transaction record
            transactions.append({
                'transaction_id': trans_id,
                'company_id': company_id,
                'component_type': 'DSO',
                'transaction_number': f"{self.config['transaction_prefixes']['invoice']}-2024-{str(i).zfill(6)}",
                'transaction_date': trans_date.strftime('%Y-%m-%d'),
                'due_date': due_date.strftime('%Y-%m-%d'),
                'amount': amount,
                'outstanding_amount': 0.0 if status == 'PAID' else amount,
                'days_outstanding': days_outstanding,
                'gl_account': self.config['gl_ar'],
                'customer_vendor': customer,
                'status': status,
                'erp_metadata': json.dumps(erp_metadata)
            })

        print(f"   ✓ Generated {len(transactions)} DSO transactions")
        for issue_name, count in issue_counts.items():
            print(f"      - {issue_name}: {count} transactions")
        print(f"   ✓ Generated {len(event_logs)} DSO event logs")

        return transactions, event_logs

    def _get_dso_issue_counts(self):
        """Get target issue counts for DSO based on dataset"""
        if self.dataset_name == 'sap':
            return {
                'Billing trigger disabled': 143,
                'Approval stuck': 31,
                'Credit holds': 200,
                'Late payers': 187
            }
        elif self.dataset_name == 'infor':
            return {
                'Credit hold backlog': 156,
                'Payment application delays': 89,
                'Unapplied cash': 67,
                'Late payers': 245
            }
        else:  # oracle
            return {
                'Progress billing not triggered': 43,
                'Customer acceptance delays': 67,
                'Retainage not billed': 34,
                'Late payers': 142
            }

    def _generate_dso_amount(self):
        """Generate DSO amount scaled by industry"""
        if self.dataset_name == 'infor':
            # Distribution: higher volume, lower amounts
            return round(random.uniform(2000, 75000), 2)
        elif self.dataset_name == 'oracle':
            # Manufacturing: lower volume, higher amounts
            return round(random.uniform(15000, 350000), 2)
        else:  # SAP
            return round(random.uniform(5000, 150000), 2)

    def _inject_dso_issue(self, idx, trans_id, company_id, customer, trans_date,
                          due_date, amount, issue_counts, target_counts):
        """Inject dataset-specific DSO issues"""

        # Get configuration
        dates = self.config['issue_dates']
        events = self.config['event_types']
        modules = self.config['modules']
        approver = self.config['approver_names']['ar']

        # Issue #1: Billing/workflow issues (first issue type)
        issue1_name = list(target_counts.keys())[0]
        issue1_target = target_counts[issue1_name]

        if (issue_counts[issue1_name] < issue1_target and
            trans_date >= dates['billing_trigger_disabled'] and
            trans_date < dates['billing_trigger_disabled'] + timedelta(days=30)):

            issue_counts[issue1_name] += 1

            if self.dataset_name == 'sap':
                status = "FULFILLED_NOT_BILLED"
                event_list = [
                    self._create_event(trans_id, company_id, events['order_created'],
                                     trans_date - timedelta(days=5), 'SALES_REP', modules['sales'],
                                     'Sales order created', {'order_value': amount, 'customer': customer}),
                    self._create_event(trans_id, company_id, events['shipped'],
                                     trans_date - timedelta(days=1), 'WAREHOUSE', modules['sales'],
                                     'Goods shipped to customer', {'tracking': f'UPS{random.randint(100000, 999999)}'})
                ]
            elif self.dataset_name == 'infor':
                status = "CREDIT_HOLD"
                event_list = [
                    self._create_event(trans_id, company_id, events['order_created'],
                                     trans_date, 'SALES_REP', modules['sales'],
                                     'Order entered', {'order_value': amount}),
                    self._create_event(trans_id, company_id, events['approval_triggered'],
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['workflow'],
                                     'Credit check initiated', {'credit_limit_check': 'PENDING'})
                ]
            else:  # oracle
                status = "MILESTONE_ACHIEVED_NOT_BILLED"
                event_list = [
                    self._create_event(trans_id, company_id, 'PROJECT_MILESTONE_COMPLETE',
                                     trans_date, 'PROJECT_SYSTEM', modules['sales'],
                                     'Project milestone completed', {'milestone': '75% Complete', 'amount': amount}),
                    self._create_event(trans_id, company_id, events['shipped'],
                                     trans_date + timedelta(days=2), 'SHIPPING', modules['sales'],
                                     'Equipment shipped', {'tracking': f'FDX{random.randint(100000, 999999)}'})
                ]

            return {'status': status, 'events': event_list}

        # Issue #2: Approval/processing delays (second issue type)
        issue2_name = list(target_counts.keys())[1]
        issue2_target = target_counts[issue2_name]

        if (issue_counts[issue2_name] < issue2_target and
            trans_date >= dates['approver_left_ar'] - timedelta(days=10) and
            trans_date < dates['approver_left_ar'] + timedelta(days=5)):

            issue_counts[issue2_name] += 1

            if self.dataset_name == 'infor':
                status = "PAYMENT_RECEIVED_NOT_APPLIED"
                event_list = [
                    self._create_event(trans_id, company_id, events['order_created'],
                                     trans_date - timedelta(days=5), 'SALES_REP', modules['sales'],
                                     'Order entered', {'order_value': amount}),
                    self._create_event(trans_id, company_id, events['shipped'],
                                     trans_date - timedelta(days=2), 'WAREHOUSE', modules['sales'],
                                     'Shipment confirmed', {'tracking': f'UPS{random.randint(100000, 999999)}'})
,
                    self._create_event(trans_id, company_id, events['billed'],
                                     trans_date, 'SYSTEM_AUTO', modules['finance'],
                                     'Invoice posted', {'invoice_number': f'INV-2024-{str(idx).zfill(6)}'}),
                    self._create_event(trans_id, company_id, events['payment_received'],
                                     trans_date + timedelta(days=15), 'LOCKBOX', modules['finance'],
                                     'Payment received - no match', {'payment_ref': 'CHECK'})
                ]
            elif self.dataset_name == 'oracle':
                status = "PENDING_CUSTOMER_ACCEPTANCE"
                event_list = [
                    self._create_event(trans_id, company_id, events['order_created'],
                                     trans_date - timedelta(days=45), 'SALES_REP', modules['sales'],
                                     'Order booked', {'order_value': amount}),
                    self._create_event(trans_id, company_id, events['shipped'],
                                     trans_date - timedelta(days=5), 'SHIPPING', modules['sales'],
                                     'Ship confirmed', {'tracking': f'FDX{random.randint(100000, 999999)}'}),
                    self._create_event(trans_id, company_id, 'DELIVERED',
                                     trans_date, 'CARRIER', modules['sales'],
                                     'Delivered to customer site', {'signed_by': 'RECEIVING'})
                ]
            else:  # SAP
                status = "PENDING_APPROVAL"
                event_list = [
                    self._create_event(trans_id, company_id, events['order_created'],
                                     trans_date - timedelta(days=5), 'SALES_REP', modules['sales'],
                                     'Sales order created', {'order_value': amount}),
                    self._create_event(trans_id, company_id, events['shipped'],
                                     trans_date - timedelta(days=2), 'WAREHOUSE', modules['sales'],
                                     'Goods shipped to customer', {'tracking': f'UPS{random.randint(100000, 999999)}'}),
                    self._create_event(trans_id, company_id, events['billed'],
                                     trans_date, 'SYSTEM_AUTO', modules['sales'],
                                     'Invoice generated', {'invoice_number': f'INV-2024-{str(idx).zfill(6)}'}),
                    self._create_event(trans_id, company_id, events['approval_triggered'],
                                     trans_date + timedelta(hours=1), 'SYSTEM', modules['workflow'],
                                     'Approval workflow started', {'assigned_to': approver})
                ]

            return {'status': status, 'events': event_list}

        # Issue #3: Credit/system policy issues (third issue type)
        issue3_name = list(target_counts.keys())[2]
        issue3_target = target_counts[issue3_name]

        if (trans_date >= dates['credit_policy_change'] and
            random.random() < 0.15 and issue_counts[issue3_name] < issue3_target):

            issue_counts[issue3_name] += 1

            if self.dataset_name == 'infor':
                status = "UNAPPLIED_CASH"
                event_list = [
                    self._create_event(trans_id, company_id, events['order_created'],
                                     trans_date - timedelta(days=30), 'SALES_REP', modules['sales'],
                                     'Order entered', {'order_value': amount}),
                    self._create_event(trans_id, company_id, events['billed'],
                                     trans_date - timedelta(days=25), 'SYSTEM_AUTO', modules['finance'],
                                     'Invoice posted', {'invoice_number': f'INV-2024-{str(idx).zfill(6)}'}),
                    self._create_event(trans_id, company_id, 'PAYMENT_DEPOSITED',
                                     trans_date, 'LOCKBOX', modules['finance'],
                                     'Payment deposited - no remittance detail', {'deposit_amount': amount})
                ]
            elif self.dataset_name == 'oracle':
                status = "RETAINAGE_ELIGIBLE_NOT_BILLED"
                event_list = [
                    self._create_event(trans_id, company_id, 'PROJECT_CLOSED',
                                     trans_date - timedelta(days=60), 'PROJECT_MANAGER', modules['sales'],
                                     'Project closed successfully', {'project_id': f'PRJ-{random.randint(1000, 9999)}'}),
                    self._create_event(trans_id, company_id, 'RETAINAGE_PERIOD_EXPIRED',
                                     trans_date, 'SYSTEM_AUTO', modules['finance'],
                                     'Retainage hold period expired', {'retainage_pct': 10, 'amount': amount})
                ]
            else:  # SAP
                status = "CREDIT_HOLD"
                event_list = [
                    self._create_event(trans_id, company_id, events['order_created'],
                                     trans_date, 'SALES_REP', modules['sales'],
                                     'Sales order created', {'order_value': amount}),
                    self._create_event(trans_id, company_id, events['credit_hold'],
                                     trans_date + timedelta(hours=2), 'CREDIT_SYSTEM', modules['sales'],
                                     'Credit hold applied due to policy change',
                                     {'reason': 'POLICY_CHANGE_2024_08', 'threshold_exceeded': True})
                ]

            return {'status': status, 'events': event_list}

        # Issue #4: Late payers (behavioral, all datasets have this)
        issue4_name = list(target_counts.keys())[3]
        issue4_target = target_counts[issue4_name]

        if issue_counts[issue4_name] < issue4_target and random.random() < 0.10:
            issue_counts[issue4_name] += 1
            status = "OVERDUE"

            event_list = [
                self._create_event(trans_id, company_id, events['order_created'],
                                 trans_date - timedelta(days=5), 'SALES_REP', modules['sales'],
                                 'Order created', {'order_value': amount}),
                self._create_event(trans_id, company_id, events['shipped'],
                                 trans_date - timedelta(days=1), 'WAREHOUSE', modules['sales'],
                                 'Goods shipped', {'tracking': f'UPS{random.randint(100000, 999999)}'}),
                self._create_event(trans_id, company_id, events['billed'],
                                 trans_date, 'SYSTEM_AUTO', modules['sales'],
                                 'Invoice generated', {'invoice_number': f'INV-2024-{str(idx).zfill(6)}'}),
                self._create_event(trans_id, company_id, 'PAYMENT_REMINDER',
                                 due_date + timedelta(days=15), 'AR_CLERK', modules['finance'],
                                 'Payment reminder sent to customer', {'days_overdue': 15})
            ]

            return {'status': status, 'events': event_list}

        return None

    def _generate_normal_dso_flow(self, trans_id, company_id, customer, trans_date,
                                   amount, days_outstanding, payment_terms):
        """Generate normal DSO transaction flow"""
        events = self.config['event_types']
        modules = self.config['modules']

        event_list = [
            self._create_event(trans_id, company_id, events['order_created'],
                             trans_date - timedelta(days=5), 'SALES_REP', modules['sales'],
                             'Order created', {'order_value': amount}),
            self._create_event(trans_id, company_id, events['shipped'],
                             trans_date - timedelta(days=1), 'WAREHOUSE', modules['sales'],
                             'Goods shipped', {'tracking': f'UPS{random.randint(100000, 999999)}'}),
            self._create_event(trans_id, company_id, events['billed'],
                             trans_date, 'SYSTEM_AUTO', modules['sales'],
                             'Invoice generated', {'invoice_number': f'INV-2024-{random.randint(100000, 999999)}'})
        ]

        # Some are paid
        if random.random() < 0.3 and days_outstanding > payment_terms + 10:
            payment_date = trans_date + timedelta(days=payment_terms + random.randint(1, 30))
            event_list.append(
                self._create_event(trans_id, company_id, events['payment_received'],
                                 payment_date, 'SYSTEM_AUTO', modules['finance'],
                                 'Payment received and cleared',
                                 {'payment_method': 'WIRE', 'amount': amount})
            )

        return 0.0 if len(event_list) > 3 else amount, event_list

    def generate_dio_transactions(self, company_id):
        """Generate DIO (Inventory) transactions with intentional issues"""
        print("\n[3/7] Generating DIO transactions...")

        transactions = []
        event_logs = []
        inventory_movements = []

        # Issue counts
        target_counts = self._get_dio_issue_counts()
        issue_counts = {key: 0 for key in target_counts.keys()}

        # Generate vendor list
        num_vendors = max(15, int(self.config['dio_items'] / 40))
        vendors = [fake.company() for _ in range(num_vendors)]

        material_types = self._get_material_types()

        for i in range(self.config['dio_items']):
            trans_id = str(uuid.uuid4())
            material_id = f"{self.config['transaction_prefixes']['material']}-{str(random.randint(100000, 999999))}"
            material_type = random.choice(material_types)
            vendor = random.choice(vendors)

            # Transaction date
            trans_date = PERIOD_START + timedelta(days=random.randint(0, 364))
            days_outstanding = (ANALYSIS_DATE - trans_date).days

            # Quantity and amount
            quantity = random.randint(10, 1000)
            unit_price = self._generate_dio_unit_price()
            amount = round(quantity * unit_price, 2)

            # Default status
            status = "IN_STOCK"
            erp_metadata = {
                "quantity": quantity,
                "material_type": material_type,
                "unit_price": unit_price
            }

            # Inject issues
            issue_data = self._inject_dio_issue(
                i, trans_id, company_id, material_id, vendor, trans_date,
                quantity, amount, unit_price, issue_counts, target_counts, days_outstanding
            )

            if issue_data:
                status = issue_data['status']
                amount = issue_data.get('amount', amount)
                event_logs.extend(issue_data['events'])
                if 'movements' in issue_data:
                    inventory_movements.extend(issue_data['movements'])
                if 'erp_metadata' in issue_data:
                    erp_metadata.update(issue_data['erp_metadata'])
            else:
                # Normal flow
                events, movements = self._generate_normal_dio_flow(
                    trans_id, company_id, material_id, vendor, trans_date,
                    quantity, amount, unit_price, days_outstanding
                )
                event_logs.extend(events)
                inventory_movements.extend(movements)

            # Determine GL account (60% raw materials, 40% finished goods)
            if i < int(self.config['dio_items'] * 0.6):
                gl_account = self.config['gl_inventory_rm']
            else:
                gl_account = self.config['gl_inventory_fg']

            # Create transaction record
            transactions.append({
                'transaction_id': trans_id,
                'company_id': company_id,
                'component_type': 'DIO',
                'transaction_number': material_id,
                'transaction_date': trans_date.strftime('%Y-%m-%d'),
                'due_date': None,
                'amount': amount,
                'outstanding_amount': amount,
                'days_outstanding': days_outstanding,
                'gl_account': gl_account,
                'customer_vendor': None,
                'status': status,
                'erp_metadata': json.dumps(erp_metadata)
            })

        print(f"   ✓ Generated {len(transactions)} DIO transactions")
        for issue_name, count in issue_counts.items():
            print(f"      - {issue_name}: {count} items")
        print(f"   ✓ Generated {len(event_logs)} DIO event logs")
        print(f"   ✓ Generated {len(inventory_movements)} inventory movements")

        return transactions, event_logs, inventory_movements

    def _get_dio_issue_counts(self):
        """Get target issue counts for DIO based on dataset"""
        if self.dataset_name == 'sap':
            return {
                'GR without valuation': 87,
                'Quality hold stall': 43,
                'Ghost allocations': 28,
                'Obsolete inventory': 34
            }
        elif self.dataset_name == 'infor':
            return {
                'Cycle count positive variances': 148,  # 63% - trapped capital
                'Cycle count negative variances': 86,   # 37% - recognized losses
                'Cross-dock staging timeouts': 145,
                'RTV authorization delays (accepted)': 50,  # Trapped capital
                'RTV authorization delays (rejected)': 28,  # Losses
                'Obsolete inventory (liquidation)': 55,  # Partial recovery
                'Obsolete inventory (zero value)': 34   # Total loss
            }
        else:  # oracle
            return {
                'Work order release delays': 156,
                'Subcontract PO delays': 89,
                'Quarantine pending MRB (releasable)': 70,  # Trapped capital
                'Quarantine pending MRB (failed)': 42,      # Losses
                'Obsolete inventory (liquidation)': 40,     # Partial recovery
                'Obsolete inventory (zero value)': 27      # Total loss
            }

    def _get_material_types(self):
        """Get material types based on dataset"""
        if self.dataset_name == 'infor':
            return ['AFTERMARKET_PARTS', 'FILTERS', 'BRAKE_COMPONENTS', 'ELECTRICAL', 'BODY_PARTS']
        elif self.dataset_name == 'oracle':
            return ['RAW_MATERIALS', 'MACHINED_PARTS', 'ASSEMBLIES', 'SUBASSEMBLIES', 'PURCHASED_COMPONENTS']
        else:  # SAP
            return ['ELECTRONICS', 'RAW_MATERIALS', 'COMPONENTS', 'FINISHED_GOODS', 'PACKAGING']

    def _generate_dio_unit_price(self):
        """Generate DIO unit price scaled by industry"""
        if self.dataset_name == 'infor':
            # Distribution: lower unit prices, higher volumes
            return round(random.uniform(5, 250), 2)
        elif self.dataset_name == 'oracle':
            # Manufacturing: higher unit prices
            return round(random.uniform(50, 1500), 2)
        else:  # SAP
            return round(random.uniform(10, 500), 2)

    def _inject_dio_issue(self, idx, trans_id, company_id, material_id, vendor, trans_date,
                          quantity, amount, unit_price, issue_counts, target_counts, days_outstanding):
        """Inject dataset-specific DIO issues"""

        dates = self.config['issue_dates']
        events = self.config['event_types']
        modules = self.config['modules']

        # Issue #1: Valuation/posting issues (for SAP and Oracle) or cycle count variances (for Infor)
        issue1_name = list(target_counts.keys())[0]
        issue1_target = target_counts[issue1_name]

        if (issue_counts[issue1_name] < issue1_target and
            trans_date >= dates['valuation_issue_start'] and
            trans_date < dates['valuation_issue_start'] + timedelta(days=60)):

            issue_counts[issue1_name] += 1

            if self.dataset_name == 'sap':
                status = "RECEIVED_NOT_VALUED"
                event_list = [
                    self._create_event(trans_id, company_id, events['goods_receipt'],
                                     trans_date, 'RECEIVING', modules['materials'],
                                     'Goods received from vendor',
                                     {'quantity': quantity, 'vendor': vendor, 'material': material_id})
                ]
                movements = [
                    self._create_movement(company_id, material_id, trans_date, 'GOODS_RECEIPT',
                                        quantity, 0.0, 'GR', f'45{random.randint(10000000, 99999999)}')
                ]
                return {'status': status, 'amount': 0.0, 'events': event_list, 'movements': movements}

            elif self.dataset_name == 'infor':
                # Positive cycle count variance - trapped capital
                status = "COUNT_VARIANCE_POSITIVE"
                count_date = trans_date + timedelta(days=random.randint(1, 15))
                system_qty = quantity
                variance_qty = random.randint(5, max(5, int(quantity * 0.15)))
                actual_qty = system_qty + variance_qty
                variance_value = round(variance_qty * unit_price, 2)

                erp_metadata = {
                    'system_qty': system_qty,
                    'counted_qty': actual_qty,
                    'variance_qty': variance_qty,
                    'variance_value': variance_value,
                    'variance_type': 'OVERAGE',
                    'recovery_category': 'TRAPPED_CAPITAL',
                    'recovery_potential': variance_value,
                    'root_cause': 'Goods receipts posted without valuation or found during physical count'
                }

                event_list = [
                    self._create_event(trans_id, company_id, events['goods_receipt'],
                                     trans_date, 'RECEIVING', modules['materials'],
                                     'Receipt posted', {'quantity': system_qty}),
                    self._create_event(trans_id, company_id, events['valuation_posted'],
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                     'Inventory valued', {'amount': amount}),
                    self._create_event(trans_id, company_id, 'CYCLE_COUNT_ENTERED',
                                     count_date, 'CYCLE_COUNTER', modules['materials'],
                                     'Positive variance detected - physical count exceeds system',
                                     {'system_qty': system_qty, 'physical_qty': actual_qty, 'variance_qty': variance_qty, 'variance_value': variance_value, 'variance_type': 'OVERAGE'})
                ]
                movements = [
                    self._create_movement(company_id, material_id, trans_date, 'GOODS_RECEIPT',
                                        system_qty, amount, 'GR', f'45{random.randint(10000000, 99999999)}')
                ]
                return {'status': status, 'amount': variance_value, 'events': event_list, 'movements': movements, 'erp_metadata': erp_metadata}

            else:  # oracle
                status = "RELEASED_NOT_STARTED"
                erp_metadata = {
                    'recovery_category': 'TRAPPED_CAPITAL',
                    'recovery_potential': amount,
                    'root_cause': 'Work order released but materials not allocated - inventory stuck'
                }
                event_list = [
                    self._create_event(trans_id, company_id, 'WORK_ORDER_CREATED',
                                     trans_date - timedelta(days=5), 'PLANNER', modules['materials'],
                                     'Work order created', {'wo_number': f'WO-{random.randint(100000, 999999)}'}),
                    self._create_event(trans_id, company_id, 'WORK_ORDER_RELEASED',
                                     trans_date, 'PRODUCTION_SUPERVISOR', modules['materials'],
                                     'Work order released to shop floor', {'quantity': quantity})
                ]
                movements = []
                return {'status': status, 'events': event_list, 'movements': movements, 'erp_metadata': erp_metadata}

        # Issue #2: Negative cycle count variances (for Infor only)
        if self.dataset_name == 'infor':
            issue2_name = list(target_counts.keys())[1]
            issue2_target = target_counts[issue2_name]

            if (issue_counts[issue2_name] < issue2_target and
                trans_date >= dates['valuation_issue_start'] and
                trans_date < dates['valuation_issue_start'] + timedelta(days=90) and
                random.random() < 0.08):

                issue_counts[issue2_name] += 1

                # Negative cycle count variance - recognized loss
                status = "COUNT_VARIANCE_NEGATIVE"
                count_date = trans_date + timedelta(days=random.randint(1, 15))
                system_qty = quantity
                variance_qty = random.randint(5, max(5, int(quantity * 0.12)))
                actual_qty = system_qty - variance_qty
                variance_value = round(variance_qty * unit_price, 2)

                erp_metadata = {
                    'system_qty': system_qty,
                    'counted_qty': actual_qty,
                    'variance_qty': -variance_qty,
                    'variance_value': -variance_value,
                    'variance_type': 'SHORTAGE',
                    'recovery_category': 'RECOGNIZED_LOSS',
                    'recovery_potential': 0,
                    'root_cause': 'Shrinkage/theft - physical inventory missing, unrecorded consumption'
                }

                event_list = [
                    self._create_event(trans_id, company_id, events['goods_receipt'],
                                     trans_date, 'RECEIVING', modules['materials'],
                                     'Receipt posted', {'quantity': system_qty}),
                    self._create_event(trans_id, company_id, events['valuation_posted'],
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                     'Inventory valued', {'amount': amount}),
                    self._create_event(trans_id, company_id, 'CYCLE_COUNT_ENTERED',
                                     count_date, 'CYCLE_COUNTER', modules['materials'],
                                     'Negative variance detected - physical count less than system',
                                     {'system_qty': system_qty, 'physical_qty': actual_qty, 'variance_qty': -variance_qty, 'variance_value': -variance_value, 'variance_type': 'SHORTAGE'})
                ]
                movements = [
                    self._create_movement(company_id, material_id, trans_date, 'GOODS_RECEIPT',
                                        system_qty, amount, 'GR', f'45{random.randint(10000000, 99999999)}')
                ]
                return {'status': status, 'amount': variance_value, 'events': event_list, 'movements': movements, 'erp_metadata': erp_metadata}

        # Issue #3: Hold/staging issues
        issue2_name = list(target_counts.keys())[1] if self.dataset_name != 'infor' else list(target_counts.keys())[2]
        issue2_target = target_counts[issue2_name]

        if issue_counts[issue2_name] < issue2_target and random.random() < 0.12:
            issue_counts[issue2_name] += 1

            if self.dataset_name == 'sap':
                status = "QUALITY_HOLD"
                hold_date = trans_date + timedelta(days=2)
                event_list = [
                    self._create_event(trans_id, company_id, events['goods_receipt'],
                                     trans_date, 'RECEIVING', modules['materials'],
                                     'Goods received from vendor', {'quantity': quantity, 'vendor': vendor}),
                    self._create_event(trans_id, company_id, events['valuation_posted'],
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                     'Inventory valuation posted', {'amount': amount}),
                    self._create_event(trans_id, company_id, events['quality_hold'],
                                     hold_date, 'QA_INSPECTOR', modules['quality'],
                                     'Quality inspection hold applied',
                                     {'reason': 'INSPECTION_REQUIRED', 'hold_hours': (ANALYSIS_DATE - hold_date).total_seconds() / 3600})
                ]

            elif self.dataset_name == 'infor':
                status = "STAGED_NOT_SHIPPED"
                staged_date = trans_date + timedelta(days=random.randint(3, 10))
                erp_metadata = {
                    'recovery_category': 'TRAPPED_CAPITAL',
                    'recovery_potential': amount,
                    'root_cause': 'Cross-dock staging timeout - inventory exists but stuck in staging area'
                }
                event_list = [
                    self._create_event(trans_id, company_id, 'ORDER_PICK_RELEASED',
                                     trans_date, 'WAREHOUSE_SYSTEM', modules['sales'],
                                     'Pick released for cross-dock order', {'order': f'SO-{random.randint(10000, 99999)}'}),
                    self._create_event(trans_id, company_id, 'STAGED_CROSSDOCK',
                                     staged_date, 'PICKER', modules['materials'],
                                     'Staged to cross-dock location', {'location': 'XDOCK-' + str(random.randint(1, 20)), 'hours_waiting': (ANALYSIS_DATE - staged_date).total_seconds() / 3600})
                ]

            else:  # oracle
                status = "AT_SUBCONTRACTOR"
                issued_date = trans_date + timedelta(days=random.randint(5, 25))
                event_list = [
                    self._create_event(trans_id, company_id, 'SUBCONTRACT_PO_CREATED',
                                     trans_date, 'BUYER', modules['materials'],
                                     'Subcontract PO created', {'po': f'PO-{random.randint(10000, 99999)}', 'vendor': vendor}),
                    self._create_event(trans_id, company_id, 'SUBCONTRACT_ISSUED',
                                     issued_date, 'SUBCONTRACT_CLERK', modules['materials'],
                                     'Material issued to subcontractor', {'quantity': quantity, 'days_at_subcon': (ANALYSIS_DATE - issued_date).days})
                ]

            movements = [
                self._create_movement(company_id, material_id, trans_date, 'GOODS_RECEIPT',
                                    quantity, amount, 'GR', f'45{random.randint(10000000, 99999999)}')
            ]

            return {'status': status, 'events': event_list, 'movements': movements}

        # Issue #3: Authorization/disposition delays
        issue3_name = list(target_counts.keys())[2]
        issue3_target = target_counts[issue3_name]

        if issue_counts[issue3_name] < issue3_target and random.random() < 0.08:
            issue_counts[issue3_name] += 1

            if self.dataset_name == 'sap':
                status = "RESERVED_CANCELLED_ORDER"
                cancelled_order = f'SO-2024-{random.randint(10000, 99999)}'
                event_list = [
                    self._create_event(trans_id, company_id, events['goods_receipt'],
                                     trans_date, 'RECEIVING', modules['materials'],
                                     'Goods received from vendor', {'quantity': quantity, 'vendor': vendor}),
                    self._create_event(trans_id, company_id, events['valuation_posted'],
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                     'Inventory valuation posted', {'amount': amount}),
                    self._create_event(trans_id, company_id, 'RESERVATION_CREATED',
                                     trans_date + timedelta(days=10), 'SYSTEM_AUTO', modules['sales'],
                                     'Material reserved for sales order', {'order_number': cancelled_order, 'quantity': quantity}),
                    self._create_event(trans_id, company_id, 'ORDER_CANCELLED',
                                     trans_date + timedelta(days=20), 'SALES_REP', modules['sales'],
                                     'Sales order cancelled', {'order_number': cancelled_order, 'reason': 'CUSTOMER_CANCELLED'})
                ]

            elif self.dataset_name == 'infor':
                status = "DAMAGED_RTV_PENDING"
                rtv_date = trans_date + timedelta(days=random.randint(10, 30))
                event_list = [
                    self._create_event(trans_id, company_id, events['goods_receipt'],
                                     trans_date, 'RECEIVING', modules['materials'],
                                     'Receipt posted', {'quantity': quantity}),
                    self._create_event(trans_id, company_id, 'DAMAGE_REPORTED',
                                     rtv_date, 'WAREHOUSE', modules['quality'],
                                     'Damage discovered during inspection', {'damaged_qty': quantity}),
                    self._create_event(trans_id, company_id, 'RTV_CREATED',
                                     rtv_date + timedelta(hours=2), 'RECEIVING_CLERK', modules['materials'],
                                     'RTV authorization requested from buyer', {'vendor': vendor, 'awaiting_approval': True})
                ]

            else:  # oracle
                status = "QUARANTINE_PENDING_MRB"
                inspection_date = trans_date + timedelta(days=random.randint(2, 8))
                event_list = [
                    self._create_event(trans_id, company_id, events['goods_receipt'],
                                     trans_date, 'RECEIVING', modules['materials'],
                                     'Receipt created', {'quantity': quantity}),
                    self._create_event(trans_id, company_id, events['quality_hold'],
                                     inspection_date, 'QA_INSPECTOR', modules['quality'],
                                     'Inspection failed - moved to quarantine',
                                     {'failure_reason': 'DIMENSIONAL_VARIANCE', 'quantity': quantity}),
                    self._create_event(trans_id, company_id, 'MRB_CASE_OPENED',
                                     inspection_date + timedelta(hours=4), 'QA_SYSTEM', modules['quality'],
                                     'Material Review Board case opened', {'days_open': (ANALYSIS_DATE - inspection_date).days})
                ]

            movements = [
                self._create_movement(company_id, material_id, trans_date, 'GOODS_RECEIPT',
                                    quantity, amount, 'GR', f'45{random.randint(10000000, 99999999)}')
            ]

            return {'status': status, 'events': event_list, 'movements': movements}

        # Issue #4: Obsolete inventory
        issue4_name = list(target_counts.keys())[3]
        issue4_target = target_counts[issue4_name]

        if issue_counts[issue4_name] < issue4_target and trans_date < ANALYSIS_DATE - timedelta(days=180):
            issue_counts[issue4_name] += 1
            status = "OBSOLETE"

            event_list = [
                self._create_event(trans_id, company_id, events['goods_receipt'],
                                 trans_date, 'RECEIVING', modules['materials'],
                                 'Goods received from vendor', {'quantity': quantity, 'vendor': vendor}),
                self._create_event(trans_id, company_id, events['valuation_posted'],
                                 trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                 'Inventory valuation posted', {'amount': amount})
            ]

            movements = [
                self._create_movement(company_id, material_id, trans_date, 'GOODS_RECEIPT',
                                    quantity, amount, 'GR', f'45{random.randint(10000000, 99999999)}')
            ]

            return {'status': status, 'events': event_list, 'movements': movements}

        return None

    def _generate_normal_dio_flow(self, trans_id, company_id, material_id, vendor, trans_date,
                                   quantity, amount, unit_price, days_outstanding):
        """Generate normal DIO transaction flow"""
        events = self.config['event_types']
        modules = self.config['modules']

        event_list = [
            self._create_event(trans_id, company_id, events['goods_receipt'],
                             trans_date, 'RECEIVING', modules['materials'],
                             'Goods received from vendor', {'quantity': quantity, 'vendor': vendor}),
            self._create_event(trans_id, company_id, events['valuation_posted'],
                             trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                             'Inventory valuation posted', {'amount': amount})
        ]

        movements = [
            self._create_movement(company_id, material_id, trans_date, 'GOODS_RECEIPT',
                                quantity, amount, 'GR', f'45{random.randint(10000000, 99999999)}')
        ]

        # Some items have goods issues
        if random.random() < 0.4 and days_outstanding > 30:
            issue_qty = random.randint(10, min(100, quantity))
            issue_date = trans_date + timedelta(days=random.randint(10, min(60, days_outstanding)))
            issue_amount = round(issue_qty * unit_price, 2)

            event_list.append(
                self._create_event(trans_id, company_id, events['goods_issue'],
                                 issue_date, 'PRODUCTION', modules['materials'],
                                 'Material issued to production', {'quantity': issue_qty, 'order': f'PRO-{random.randint(10000, 99999)}'})
            )

            movements.append(
                self._create_movement(company_id, material_id, issue_date, 'GOODS_ISSUE',
                                    -issue_qty, -issue_amount, 'GI', f'45{random.randint(10000000, 99999999)}')
            )

        return event_list, movements

    def generate_dpo_transactions(self, company_id):
        """Generate DPO (Accounts Payable) transactions with intentional issues"""
        print("\n[4/7] Generating DPO transactions...")

        transactions = []
        event_logs = []
        purchase_orders = []

        # Issue counts
        target_counts = self._get_dpo_issue_counts()
        issue_counts = {key: 0 for key in target_counts.keys()}

        # Generate supplier list
        num_suppliers = max(20, int(self.config['dpo_invoices'] / 60))
        suppliers = [fake.company() for _ in range(num_suppliers)]

        for i in range(self.config['dpo_invoices']):
            trans_id = str(uuid.uuid4())
            po_id = str(uuid.uuid4())
            supplier = random.choice(suppliers)

            # Transaction date
            trans_date = PERIOD_START + timedelta(days=random.randint(0, 364))
            payment_terms = random.choice([30, 45, 60])
            due_date = trans_date + timedelta(days=payment_terms)
            days_outstanding = (ANALYSIS_DATE - trans_date).days

            # Amount
            amount = self._generate_dpo_amount()
            po_number = f"{self.config['transaction_prefixes']['po']}-2024-{str(i).zfill(5)}"

            # Default status
            status = "OPEN"
            erp_metadata = {
                "payment_terms_days": payment_terms,
                "po_number": po_number
            }

            # Create PO record
            purchase_orders.append({
                'po_id': po_id,
                'company_id': company_id,
                'po_number': po_number,
                'po_date': (trans_date - timedelta(days=random.randint(10, 30))).strftime('%Y-%m-%d'),
                'vendor': supplier,
                'total_amount': amount,
                'status': 'OPEN'
            })

            # Inject issues
            issue_data = self._inject_dpo_issue(
                i, trans_id, company_id, supplier, trans_date, po_number,
                amount, issue_counts, target_counts, payment_terms
            )

            if issue_data:
                status = issue_data['status']
                event_logs.extend(issue_data['events'])
                if issue_data.get('po_paid'):
                    purchase_orders[-1]['status'] = 'PAID'
            else:
                # Normal transactions
                events, is_paid = self._generate_normal_dpo_flow(
                    trans_id, company_id, supplier, trans_date, po_number,
                    amount, days_outstanding, payment_terms
                )
                event_logs.extend(events)
                if is_paid:
                    purchase_orders[-1]['status'] = 'PAID'
                    status = 'PAID'

            # Create transaction record
            transactions.append({
                'transaction_id': trans_id,
                'company_id': company_id,
                'component_type': 'DPO',
                'transaction_number': f"{self.config['transaction_prefixes']['ap_invoice']}-2024-{str(i).zfill(6)}",
                'transaction_date': trans_date.strftime('%Y-%m-%d'),
                'due_date': due_date.strftime('%Y-%m-%d'),
                'amount': amount,
                'outstanding_amount': 0.0 if status == 'PAID' else amount,
                'days_outstanding': days_outstanding,
                'gl_account': self.config['gl_ap'],
                'customer_vendor': supplier,
                'status': status,
                'erp_metadata': json.dumps(erp_metadata)
            })

        print(f"   ✓ Generated {len(transactions)} DPO transactions")
        for issue_name, count in issue_counts.items():
            print(f"      - {issue_name}: {count} invoices")
        print(f"   ✓ Generated {len(event_logs)} DPO event logs")
        print(f"   ✓ Generated {len(purchase_orders)} purchase orders")

        return transactions, event_logs, purchase_orders

    def _get_dpo_issue_counts(self):
        """Get target issue counts for DPO based on dataset"""
        if self.dataset_name == 'sap':
            return {
                'Approval stuck': 56,
                'Variance holds': 34,
                'Discount risks': 23,
                'GR/IR mismatches': 41
            }
        elif self.dataset_name == 'infor':
            return {
                'PO receipt matching failures': 92,
                'Freight invoice backlog': 187,
                'Discount risks': 45,
                'GR/IR mismatches': 67
            }
        else:  # oracle
            return {
                'PO change order approvals': 78,
                'Subcontractor milestone payments': 45,
                'Supplier terms mismatch': 134,
                'Discount risks': 34
            }

    def _generate_dpo_amount(self):
        """Generate DPO amount scaled by industry"""
        if self.dataset_name == 'infor':
            # Distribution: smaller POs, higher frequency
            return round(random.uniform(5000, 125000), 2)
        elif self.dataset_name == 'oracle':
            # Manufacturing: larger POs
            return round(random.uniform(20000, 300000), 2)
        else:  # SAP
            return round(random.uniform(10000, 200000), 2)

    def _inject_dpo_issue(self, idx, trans_id, company_id, supplier, trans_date, po_number,
                          amount, issue_counts, target_counts, payment_terms):
        """Inject dataset-specific DPO issues"""

        dates = self.config['issue_dates']
        events = self.config['event_types']
        modules = self.config['modules']
        approver = self.config['approver_names']['ap']

        # Issue #1: Approval/matching issues
        issue1_name = list(target_counts.keys())[0]
        issue1_target = target_counts[issue1_name]

        if (issue_counts[issue1_name] < issue1_target and
            trans_date >= dates['approver_left_ap'] and
            trans_date < dates['approver_left_ap'] + timedelta(days=30)):

            issue_counts[issue1_name] += 1

            if self.dataset_name == 'sap':
                status = "PENDING_APPROVAL"
                event_list = [
                    self._create_event(trans_id, company_id, events['invoice_received'],
                                     trans_date, 'AP_CLERK', modules['finance'],
                                     'Vendor invoice received and entered', {'invoice_amount': amount, 'vendor': supplier}),
                    self._create_event(trans_id, company_id, events['approval_triggered'],
                                     trans_date + timedelta(hours=2), 'SYSTEM', modules['workflow'],
                                     'Approval workflow started', {'assigned_to': approver, 'approval_threshold': 50000})
                ]

            elif self.dataset_name == 'infor':
                status = "MATCHING_EXCEPTION"
                variance_qty = random.randint(1, 5)
                event_list = [
                    self._create_event(trans_id, company_id, events['invoice_received'],
                                     trans_date, 'AP_CLERK', modules['finance'],
                                     'Invoice matched to PO', {'invoice_amount': amount, 'po_number': po_number}),
                    self._create_event(trans_id, company_id, events['variance_detected'],
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                     'Matching exception - quantity variance',
                                     {'po_qty': 100, 'invoice_qty': 100 + variance_qty, 'variance_pct': variance_qty})
                ]

            else:  # oracle
                status = "PO_CHANGE_NOT_CLOSED"
                event_list = [
                    self._create_event(trans_id, company_id, 'CHANGE_ORDER_APPROVED_EMAIL',
                                     trans_date - timedelta(days=5), 'BUYER', modules['materials'],
                                     'Change order approved via email', {'change_amount': amount * 0.1, 'new_total': amount}),
                    self._create_event(trans_id, company_id, events['invoice_received'],
                                     trans_date, 'AP_CLERK', modules['finance'],
                                     'Invoice validated', {'invoice_amount': amount, 'po_number': po_number}),
                    self._create_event(trans_id, company_id, 'MATCHING_FAILED',
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                     'PO change not closed in system', {'po_amount': amount * 0.9, 'invoice_amount': amount})
                ]

            return {'status': status, 'events': event_list}

        # Issue #2: Freight/milestone/variance issues
        issue2_name = list(target_counts.keys())[1]
        issue2_target = target_counts[issue2_name]

        if issue_counts[issue2_name] < issue2_target and random.random() < 0.08:
            issue_counts[issue2_name] += 1

            if self.dataset_name == 'sap':
                status = "VARIANCE_HOLD"
                po_price = amount * 0.95
                variance = amount - po_price
                event_list = [
                    self._create_event(trans_id, company_id, events['invoice_received'],
                                     trans_date, 'AP_CLERK', modules['finance'],
                                     'Vendor invoice received and entered', {'invoice_amount': amount, 'vendor': supplier}),
                    self._create_event(trans_id, company_id, events['variance_detected'],
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                     'Price variance detected in 3-way match',
                                     {'po_amount': po_price, 'invoice_amount': amount, 'variance': variance, 'variance_percent': 5.0}),
                    self._create_event(trans_id, company_id, 'VARIANCE_HOLD_APPLIED',
                                     trans_date + timedelta(hours=2), 'SYSTEM_AUTO', modules['materials'],
                                     'Invoice blocked due to variance', {'variance_threshold_exceeded': True})
                ]

            elif self.dataset_name == 'infor':
                status = "UNMATCHED_FREIGHT"
                carrier_invoice = f'FRT-{random.randint(100000, 999999)}'
                event_list = [
                    self._create_event(trans_id, company_id, 'FREIGHT_INVOICE_RECEIVED',
                                     trans_date, 'AP_CLERK', modules['finance'],
                                     'Freight invoice received', {'carrier_invoice': carrier_invoice, 'carrier': supplier, 'amount': amount}),
                    self._create_event(trans_id, company_id, 'SHIPMENT_MATCH_ATTEMPTED',
                                     trans_date + timedelta(hours=2), 'SYSTEM_AUTO', modules['materials'],
                                     'Shipment match failed - carrier code not mapped',
                                     {'carrier_code_invoice': 'XYZ', 'no_match_found': True})
                ]

            else:  # oracle
                status = "MILESTONE_NOT_CONFIRMED"
                milestone_pct = random.choice([25, 50, 75])
                event_list = [
                    self._create_event(trans_id, company_id, 'SUBCONTRACT_MILESTONE_INVOICE',
                                     trans_date, 'AP_CLERK', modules['finance'],
                                     'Subcontractor milestone invoice received',
                                     {'milestone': f'{milestone_pct}% Complete', 'amount': amount, 'vendor': supplier}),
                    self._create_event(trans_id, company_id, 'MILESTONE_CONFIRMATION_REQUIRED',
                                     trans_date + timedelta(hours=4), 'SYSTEM_AUTO', modules['materials'],
                                     'Awaiting buyer confirmation of milestone completion', {'assigned_to': 'BUYER'})
                ]

            return {'status': status, 'events': event_list}

        # Issue #3: Discount/terms issues
        issue3_name = list(target_counts.keys())[2]
        issue3_target = target_counts[issue3_name]

        if issue_counts[issue3_name] < issue3_target and random.random() < 0.02:
            issue_counts[issue3_name] += 1

            if self.dataset_name == 'oracle':
                status = "TERMS_MISMATCH_HOLD"
                event_list = [
                    self._create_event(trans_id, company_id, events['invoice_received'],
                                     trans_date, 'AP_CLERK', modules['finance'],
                                     'Invoice validated', {'invoice_amount': amount, 'invoice_terms': '2/10 net 30'}),
                    self._create_event(trans_id, company_id, 'TERMS_VARIANCE_DETECTED',
                                     trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                     'Payment terms mismatch with PO', {'po_terms': 'Net 45', 'invoice_terms': '2/10 net 30'})
                ]
            else:
                status = "DISCOUNT_AT_RISK"
                discount_date = trans_date + timedelta(days=10)
                days_to_discount = (discount_date - ANALYSIS_DATE).days

                event_list = [
                    self._create_event(trans_id, company_id, events['invoice_received'],
                                     trans_date, 'AP_CLERK', modules['finance'],
                                     'Vendor invoice received with discount terms',
                                     {'invoice_amount': amount, 'vendor': supplier, 'discount_terms': '2/10 net 30', 'discount_amount': round(amount * 0.02, 2)}),
                    self._create_event(trans_id, company_id, 'DISCOUNT_DEADLINE_WARNING',
                                     ANALYSIS_DATE - timedelta(days=2), 'SYSTEM_AUTO', modules['finance'],
                                     'Discount deadline approaching', {'days_remaining': days_to_discount})
                ]

            return {'status': status, 'events': event_list}

        # Issue #4: GR/IR mismatches
        issue4_name = list(target_counts.keys())[3]
        issue4_target = target_counts[issue4_name]

        if issue_counts[issue4_name] < issue4_target and random.random() < 0.03:
            issue_counts[issue4_name] += 1
            status = "GR_IR_MISMATCH"

            event_list = [
                self._create_event(trans_id, company_id, events['invoice_received'],
                                 trans_date, 'AP_CLERK', modules['finance'],
                                 'Vendor invoice received and entered',
                                 {'invoice_amount': amount, 'vendor': supplier, 'po_number': po_number}),
                self._create_event(trans_id, company_id, 'MATCHING_ATTEMPTED',
                                 trans_date + timedelta(hours=1), 'SYSTEM_AUTO', modules['materials'],
                                 '3-way match attempted', {'result': 'FAILED', 'reason': 'GR_NOT_FOUND'})
            ]

            return {'status': status, 'events': event_list}

        return None

    def _generate_normal_dpo_flow(self, trans_id, company_id, supplier, trans_date, po_number,
                                   amount, days_outstanding, payment_terms):
        """Generate normal DPO transaction flow"""
        events = self.config['event_types']
        modules = self.config['modules']

        event_list = [
            self._create_event(trans_id, company_id, events['invoice_received'],
                             trans_date, 'AP_CLERK', modules['finance'],
                             'Vendor invoice received and entered', {'invoice_amount': amount, 'vendor': supplier}),
            self._create_event(trans_id, company_id, events['matching_completed'],
                             trans_date + timedelta(hours=2), 'SYSTEM_AUTO', modules['materials'],
                             '3-way match successful', {'po_number': po_number})
        ]

        # Some are paid
        is_paid = False
        if random.random() < 0.25 and days_outstanding > payment_terms:
            payment_date = trans_date + timedelta(days=payment_terms - random.randint(1, 5))
            event_list.append(
                self._create_event(trans_id, company_id, events['payment_released'],
                                 payment_date, 'AP_MANAGER', modules['finance'],
                                 'Payment processed to vendor', {'payment_method': 'ACH', 'amount': amount})
            )
            is_paid = True

        return event_list, is_paid

    def _create_event(self, trans_id, company_id, event_type, event_time, user_id, module, description, data):
        """Helper to create event log entry"""
        if isinstance(event_time, datetime):
            event_time_str = event_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            event_time_str = event_time

        return {
            'event_id': str(uuid.uuid4()),
            'company_id': company_id,
            'transaction_id': trans_id,
            'event_type': event_type,
            'event_timestamp': event_time_str,
            'user_id': user_id,
            'module': module,
            'event_description': description,
            'event_data': json.dumps(data)
        }

    def _create_movement(self, company_id, material_id, movement_date, movement_type,
                        quantity, amount, reason_code, document_number):
        """Helper to create inventory movement entry"""
        if isinstance(movement_date, datetime):
            movement_date_str = movement_date.strftime('%Y-%m-%d')
        else:
            movement_date_str = movement_date

        return {
            'movement_id': str(uuid.uuid4()),
            'company_id': company_id,
            'material_id': material_id,
            'movement_date': movement_date_str,
            'movement_type': movement_type,
            'quantity': quantity,
            'amount': amount,
            'reason_code': reason_code,
            'document_number': document_number
        }

    def calculate_ccc_metrics(self, company_id, all_transactions):
        """Calculate CCC metrics based on generated transactions"""
        print("\n[5/7] Calculating CCC metrics...")

        df = pd.DataFrame(all_transactions)

        # Calculate DSO
        dso_df = df[df['component_type'] == 'DSO']
        total_ar = dso_df['outstanding_amount'].sum()
        daily_sales = self.config['annual_revenue'] / 365
        dso_value = round(total_ar / daily_sales, 2) if daily_sales > 0 else 0

        # Calculate DIO
        dio_df = df[df['component_type'] == 'DIO']
        total_inventory = dio_df['amount'].sum()
        cogs = self.config['annual_revenue'] * 0.65
        daily_cogs = cogs / 365
        dio_value = round(total_inventory / daily_cogs, 2) if daily_cogs > 0 else 0

        # Calculate DPO
        dpo_df = df[df['component_type'] == 'DPO']
        total_ap = dpo_df['outstanding_amount'].sum()
        dpo_value = round(total_ap / daily_cogs, 2) if daily_cogs > 0 else 0

        # Calculate CCC
        ccc_value = round(dso_value + dio_value - dpo_value, 2)

        metrics_df = pd.DataFrame([{
            'metric_id': str(uuid.uuid4()),
            'company_id': company_id,
            'calculation_date': ANALYSIS_DATE.strftime('%Y-%m-%d'),
            'dso_value': dso_value,
            'dio_value': dio_value,
            'dpo_value': dpo_value,
            'ccc_value': ccc_value
        }])

        output_path = self.output_dir / "ccc_metrics.csv"
        metrics_df.to_csv(output_path, index=False)

        print(f"   ✓ Created {output_path}")
        print(f"      - DSO: {dso_value} days")
        print(f"      - DIO: {dio_value} days")
        print(f"      - DPO: {dpo_value} days")
        print(f"      - CCC: {ccc_value} days")

        return metrics_df

    def generate_component_details(self, company_id, all_transactions):
        """Generate component_details.csv with GL account breakdowns"""
        print("\n[6/7] Generating component_details.csv...")

        df = pd.DataFrame(all_transactions)
        details = []

        # DSO details
        dso_df = df[df['component_type'] == 'DSO']
        dso_total = dso_df['outstanding_amount'].sum()
        dso_days = round(dso_total / (self.config['annual_revenue'] / 365), 2)

        details.append({
            'detail_id': str(uuid.uuid4()),
            'company_id': company_id,
            'component_type': 'DSO',
            'functional_area': 'Collections',
            'gl_account': self.config['gl_ar'],
            'gl_account_name': self.config['gl_ar_name'],
            'amount': round(dso_total, 2),
            'days_contribution': dso_days
        })

        # DIO details
        dio_df = df[df['component_type'] == 'DIO']
        dio_total = dio_df['amount'].sum()
        cogs = self.config['annual_revenue'] * 0.65
        dio_days = round(dio_total / (cogs / 365), 2)

        details.append({
            'detail_id': str(uuid.uuid4()),
            'company_id': company_id,
            'component_type': 'DIO',
            'functional_area': 'Inventory Management',
            'gl_account': self.config['gl_inventory_rm'],
            'gl_account_name': self.config['gl_inventory_rm_name'],
            'amount': round(dio_total * 0.6, 2),
            'days_contribution': round(dio_days * 0.6, 2)
        })

        details.append({
            'detail_id': str(uuid.uuid4()),
            'company_id': company_id,
            'component_type': 'DIO',
            'functional_area': 'Inventory Management',
            'gl_account': self.config['gl_inventory_fg'],
            'gl_account_name': self.config['gl_inventory_fg_name'],
            'amount': round(dio_total * 0.4, 2),
            'days_contribution': round(dio_days * 0.4, 2)
        })

        # DPO details
        dpo_df = df[df['component_type'] == 'DPO']
        dpo_total = dpo_df['outstanding_amount'].sum()
        dpo_days = round(dpo_total / (cogs / 365), 2)

        details.append({
            'detail_id': str(uuid.uuid4()),
            'company_id': company_id,
            'component_type': 'DPO',
            'functional_area': 'Vendor Payables',
            'gl_account': self.config['gl_ap'],
            'gl_account_name': self.config['gl_ap_name'],
            'amount': round(dpo_total, 2),
            'days_contribution': dpo_days
        })

        details_df = pd.DataFrame(details)
        output_path = self.output_dir / "component_details.csv"
        details_df.to_csv(output_path, index=False)

        print(f"   ✓ Created {output_path} ({len(details)} rows)")

    def save_transactions(self, all_transactions, all_events, inventory_movements, purchase_orders, manufacturing_data=None):
        """Save all transaction data to CSV files"""
        print("\n[7/7] Saving transaction files...")

        # Save transactions
        trans_df = pd.DataFrame(all_transactions)
        trans_output = self.output_dir / "transactions.csv"
        trans_df.to_csv(trans_output, index=False)
        print(f"   ✓ Created {trans_output} ({len(all_transactions)} rows)")

        # Save event logs
        events_df = pd.DataFrame(all_events)
        events_output = self.output_dir / "event_logs.csv"
        events_df.to_csv(events_output, index=False)
        print(f"   ✓ Created {events_output} ({len(all_events)} rows)")

        # Save inventory movements
        inv_df = pd.DataFrame(inventory_movements)
        inv_output = self.output_dir / "inventory_movements.csv"
        inv_df.to_csv(inv_output, index=False)
        print(f"   ✓ Created {inv_output} ({len(inventory_movements)} rows)")

        # Save purchase orders
        po_df = pd.DataFrame(purchase_orders)
        po_output = self.output_dir / "purchase_orders.csv"
        po_df.to_csv(po_output, index=False)
        print(f"   ✓ Created {po_output} ({len(purchase_orders)} rows)")

        # Save manufacturing-specific data if provided
        if manufacturing_data:
            print("\n   [Manufacturing Data]")

            # BOM structures
            bom_df = pd.DataFrame(manufacturing_data['bom_structures'])
            bom_output = self.output_dir / "bom_structure.csv"
            bom_df.to_csv(bom_output, index=False)
            print(f"   ✓ Created {bom_output} ({len(manufacturing_data['bom_structures'])} rows)")

            # BOM components
            comp_df = pd.DataFrame(manufacturing_data['bom_components'])
            comp_output = self.output_dir / "bom_components.csv"
            comp_df.to_csv(comp_output, index=False)
            print(f"   ✓ Created {comp_output} ({len(manufacturing_data['bom_components'])} rows)")

            # Work orders
            wo_df = pd.DataFrame(manufacturing_data['work_orders'])
            wo_output = self.output_dir / "work_orders.csv"
            wo_df.to_csv(wo_output, index=False)
            print(f"   ✓ Created {wo_output} ({len(manufacturing_data['work_orders'])} rows)")

            # Component availability snapshots
            snap_df = pd.DataFrame(manufacturing_data['component_snapshots'])
            snap_output = self.output_dir / "component_availability_snapshots.csv"
            snap_df.to_csv(snap_output, index=False)
            print(f"   ✓ Created {snap_output} ({len(manufacturing_data['component_snapshots'])} rows)")

            # Component shortages
            short_df = pd.DataFrame(manufacturing_data['component_shortages'])
            short_output = self.output_dir / "component_shortages.csv"
            short_df.to_csv(short_output, index=False)
            print(f"   ✓ Created {short_output} ({len(manufacturing_data['component_shortages'])} rows)")

            # Inventory snapshots
            inv_snap_df = pd.DataFrame(manufacturing_data['inventory_snapshots'])
            inv_snap_output = self.output_dir / "inventory_snapshots.csv"
            inv_snap_df.to_csv(inv_snap_output, index=False)
            print(f"   ✓ Created {inv_snap_output} ({len(manufacturing_data['inventory_snapshots'])} rows)")

            # Subcontract items
            sub_df = pd.DataFrame(manufacturing_data['subcontract_items'])
            sub_output = self.output_dir / "subcontract_items.csv"
            sub_df.to_csv(sub_output, index=False)
            print(f"   ✓ Created {sub_output} ({len(manufacturing_data['subcontract_items'])} rows)")

            # Quarantine items
            quar_df = pd.DataFrame(manufacturing_data['quarantine_items'])
            quar_output = self.output_dir / "quarantine_items.csv"
            quar_df.to_csv(quar_output, index=False)
            print(f"   ✓ Created {quar_output} ({len(manufacturing_data['quarantine_items'])} rows)")

    def generate(self):
        """Main generation function"""
        # Generate company
        company_id = self.generate_company_data()

        # Generate DSO transactions and events
        dso_trans, dso_events = self.generate_dso_transactions(company_id)

        # Generate DIO transactions and events
        dio_trans, dio_events, inventory_movements = self.generate_dio_transactions(company_id)

        # Generate DPO transactions and events
        dpo_trans, dpo_events, purchase_orders = self.generate_dpo_transactions(company_id)

        # Generate manufacturing-specific data for SAP and Oracle
        manufacturing_data = None
        if self.dataset_name in ['sap', 'oracle']:
            print("\n" + "="*80)
            print("GENERATING MANUFACTURING-SPECIFIC DATA")
            print("="*80)

            mfg_generator = ManufacturingDataGenerator(self.dataset_name, self.config, ANALYSIS_DATE)

            # Generate BOMs and work orders
            (bom_structures, bom_components, work_orders, component_snapshots,
             component_shortages, inventory_snapshots) = mfg_generator.generate_bom_and_work_orders(company_id)

            # Generate subcontract items
            subcontract_items = mfg_generator.generate_subcontract_items(company_id)

            # Generate quarantine items
            quarantine_items = mfg_generator.generate_quarantine_items(company_id)

            # Package all manufacturing data
            manufacturing_data = {
                'bom_structures': bom_structures,
                'bom_components': bom_components,
                'work_orders': work_orders,
                'component_snapshots': component_snapshots,
                'component_shortages': component_shortages,
                'inventory_snapshots': inventory_snapshots,
                'subcontract_items': subcontract_items,
                'quarantine_items': quarantine_items
            }

        # Combine all transactions
        all_transactions = dso_trans + dio_trans + dpo_trans
        all_events = dso_events + dio_events + dpo_events

        # Save transaction files
        self.save_transactions(all_transactions, all_events, inventory_movements, purchase_orders, manufacturing_data)

        # Calculate CCC metrics
        self.calculate_ccc_metrics(company_id, all_transactions)

        # Generate component details
        self.generate_component_details(company_id, all_transactions)

        # Print summary
        print("\n" + "=" * 80)
        print("GENERATION COMPLETE")
        print("=" * 80)
        print(f"\nTotal records generated:")
        print(f"  - Companies: 1")
        print(f"  - Transactions: {len(all_transactions)}")
        print(f"    • DSO: {len(dso_trans)}")
        print(f"    • DIO: {len(dio_trans)}")
        print(f"    • DPO: {len(dpo_trans)}")
        print(f"  - Event Logs: {len(all_events)}")
        print(f"  - Inventory Movements: {len(inventory_movements)}")
        print(f"  - Purchase Orders: {len(purchase_orders)}")
        print(f"  - CCC Metrics: 1")
        print(f"  - Component Details: 4")

        print(f"\n📁 All files saved to: {self.output_dir.absolute()}")
        print("\n✅ Ready for ingestion!")
        print(f"\nNext step: python scripts/ingest_synthetic_data.py --dataset {self.dataset_name}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Generate synthetic ERP data for working capital analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available datasets:
  sap    - TechMfg Industries (Electronics Manufacturing, SAP ECC 6.0)
  infor  - AmeriParts Distribution (Automotive Parts, Infor CloudSuite)
  oracle - PrecisionTech Manufacturing (Industrial Equipment, Oracle EBS)

Examples:
  python generate_synthetic_data.py --dataset sap
  python generate_synthetic_data.py --dataset infor
  python generate_synthetic_data.py --dataset oracle
        """
    )

    parser.add_argument(
        '--dataset',
        type=str,
        required=True,
        choices=['sap', 'infor', 'oracle'],
        help='Dataset to generate (sap, infor, or oracle)'
    )

    args = parser.parse_args()

    # Generate the dataset
    generator = SyntheticDataGenerator(args.dataset)
    generator.generate()


if __name__ == "__main__":
    main()
