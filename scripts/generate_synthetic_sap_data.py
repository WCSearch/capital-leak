"""
Generate Synthetic SAP Data for Working Capital Analysis Dashboard

This script creates realistic SAP data for TechMfg Industries, a fictional
mid-market electronics manufacturing company, including intentional issues
for testing the dashboard's forensic capabilities.

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
from pathlib import Path

# Set random seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)

# Initialize Faker
fake = Faker()

# Configuration
COMPANY_NAME = "TechMfg Industries"
ERP_SYSTEM = "SAP ECC 6.0"
ANNUAL_REVENUE = 85000000
ANALYSIS_DATE = datetime(2025, 1, 7)
PERIOD_START = datetime(2024, 1, 1)
PERIOD_END = datetime(2024, 12, 31)

# Data volumes
DSO_TRANSACTIONS = 2500
DIO_ITEMS = 800
DPO_INVOICES = 1800

# Output directory
OUTPUT_DIR = Path("data/synthetic")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Critical dates for injected issues
BILLING_TRIGGER_DISABLED_DATE = datetime(2024, 3, 17)
APPROVER_BWILSON_LEFT_DATE = datetime(2024, 6, 15)
CREDIT_POLICY_CHANGE_DATE = datetime(2024, 8, 1)
GR_VALUATION_ISSUE_START = datetime(2024, 5, 12)
APPROVER_JSMITH_LEFT_DATE = datetime(2024, 7, 22)

print("=" * 80)
print("SYNTHETIC SAP DATA GENERATOR")
print("=" * 80)
print(f"Company: {COMPANY_NAME}")
print(f"ERP System: {ERP_SYSTEM}")
print(f"Annual Revenue: ${ANNUAL_REVENUE:,.0f}")
print(f"Analysis Date: {ANALYSIS_DATE.strftime('%Y-%m-%d')}")
print(f"Period: {PERIOD_START.strftime('%Y-%m-%d')} to {PERIOD_END.strftime('%Y-%m-%d')}")
print(f"Random Seed: {RANDOM_SEED}")
print("=" * 80)


def generate_company_data():
    """Generate companies.csv"""
    print("\n[1/7] Generating companies.csv...")

    company_id = str(uuid.uuid4())

    df = pd.DataFrame([{
        'company_id': company_id,
        'company_name': COMPANY_NAME,
        'erp_system': ERP_SYSTEM,
        'revenue_annual': ANNUAL_REVENUE,
        'analysis_date': ANALYSIS_DATE.strftime('%Y-%m-%d')
    }])

    output_path = OUTPUT_DIR / "companies.csv"
    df.to_csv(output_path, index=False)
    print(f"   ✓ Created {output_path} (1 row)")

    return company_id


def generate_dso_transactions(company_id):
    """Generate DSO (Accounts Receivable) transactions with intentional issues"""
    print("\n[2/7] Generating DSO transactions...")

    transactions = []
    event_logs = []

    # Issue counts
    billing_disabled_count = 0
    approval_stuck_count = 0
    credit_hold_count = 0
    late_payer_count = 0

    customers = [fake.company() for _ in range(50)]

    for i in range(DSO_TRANSACTIONS):
        trans_id = str(uuid.uuid4())
        customer = random.choice(customers)

        # Transaction date
        trans_date = PERIOD_START + timedelta(days=random.randint(0, 364))
        payment_terms = random.choice([30, 45, 60])
        due_date = trans_date + timedelta(days=payment_terms)

        # Calculate days outstanding
        days_outstanding = (ANALYSIS_DATE - trans_date).days

        # Amount
        amount = round(random.uniform(5000, 150000), 2)

        # Default status
        status = "OPEN"
        erp_metadata = {
            "payment_terms_days": payment_terms,
            "credit_hold": False,
            "dispute_flag": False
        }

        # Inject Issue #1: Billing trigger disabled (143 invoices)
        if (billing_disabled_count < 143 and
            trans_date >= BILLING_TRIGGER_DISABLED_DATE and
            trans_date < BILLING_TRIGGER_DISABLED_DATE + timedelta(days=30)):

            status = "FULFILLED_NOT_BILLED"
            billing_disabled_count += 1

            # Event log: Order created and shipped, but NO billing event
            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'ORDER_CREATED',
                    'event_timestamp': (trans_date - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SALES_REP',
                    'module': 'SD',
                    'event_description': 'Sales order created',
                    'event_data': json.dumps({'order_value': amount, 'customer': customer})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'SHIPPED',
                    'event_timestamp': (trans_date - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'WAREHOUSE',
                    'module': 'SD',
                    'event_description': 'Goods shipped to customer',
                    'event_data': json.dumps({'tracking': f'UPS{random.randint(100000, 999999)}'})
                }
                # MISSING: BILLED event - this is the issue
            ])

        # Inject Issue #2: Approver left company (31 invoices)
        elif (approval_stuck_count < 31 and
              trans_date >= APPROVER_BWILSON_LEFT_DATE - timedelta(days=10) and
              trans_date < APPROVER_BWILSON_LEFT_DATE + timedelta(days=5)):

            status = "PENDING_APPROVAL"
            approval_stuck_count += 1

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'ORDER_CREATED',
                    'event_timestamp': (trans_date - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SALES_REP',
                    'module': 'SD',
                    'event_description': 'Sales order created',
                    'event_data': json.dumps({'order_value': amount})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'SHIPPED',
                    'event_timestamp': (trans_date - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'WAREHOUSE',
                    'module': 'SD',
                    'event_description': 'Goods shipped to customer',
                    'event_data': json.dumps({'tracking': f'UPS{random.randint(100000, 999999)}'})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'BILLED',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'SD',
                    'event_description': 'Invoice generated',
                    'event_data': json.dumps({'invoice_number': f'INV-2024-{str(i).zfill(6)}'})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'APPROVAL_TRIGGERED',
                    'event_timestamp': (trans_date + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM',
                    'module': 'WF',
                    'event_description': 'Approval workflow started',
                    'event_data': json.dumps({'assigned_to': 'BWILSON'})
                }
                # MISSING: APPROVED event - BWILSON left company
            ])

        # Inject Issue #3: Credit hold after policy change (random sample)
        elif (trans_date >= CREDIT_POLICY_CHANGE_DATE and
              random.random() < 0.15 and credit_hold_count < 200):

            status = "CREDIT_HOLD"
            erp_metadata['credit_hold'] = True
            credit_hold_count += 1

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'ORDER_CREATED',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SALES_REP',
                    'module': 'SD',
                    'event_description': 'Sales order created',
                    'event_data': json.dumps({'order_value': amount})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'CREDIT_HOLD_APPLIED',
                    'event_timestamp': (trans_date + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'CREDIT_SYSTEM',
                    'module': 'SD',
                    'event_description': 'Credit hold applied due to policy change',
                    'event_data': json.dumps({'reason': 'POLICY_CHANGE_2024_08', 'threshold_exceeded': True})
                }
            ])

        # Issue #4: Late payers (behavioral, no system issue) - 187 count
        elif late_payer_count < 187 and random.random() < 0.10:
            status = "OVERDUE"
            late_payer_count += 1

            # Normal invoice flow, just overdue
            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'ORDER_CREATED',
                    'event_timestamp': (trans_date - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SALES_REP',
                    'module': 'SD',
                    'event_description': 'Sales order created',
                    'event_data': json.dumps({'order_value': amount})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'SHIPPED',
                    'event_timestamp': (trans_date - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'WAREHOUSE',
                    'module': 'SD',
                    'event_description': 'Goods shipped to customer',
                    'event_data': json.dumps({'tracking': f'UPS{random.randint(100000, 999999)}'})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'BILLED',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'SD',
                    'event_description': 'Invoice generated',
                    'event_data': json.dumps({'invoice_number': f'INV-2024-{str(i).zfill(6)}'})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'PAYMENT_REMINDER',
                    'event_timestamp': (due_date + timedelta(days=15)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'AR_CLERK',
                    'module': 'FI',
                    'event_description': 'Payment reminder sent to customer',
                    'event_data': json.dumps({'days_overdue': 15})
                }
            ])

        # Normal transactions
        else:
            # Some paid, some still open
            if random.random() < 0.3 and days_outstanding > payment_terms + 10:
                status = "PAID"
                outstanding = 0.0

                payment_date = trans_date + timedelta(days=payment_terms + random.randint(1, 30))

                event_logs.extend([
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'ORDER_CREATED',
                        'event_timestamp': (trans_date - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'SALES_REP',
                        'module': 'SD',
                        'event_description': 'Sales order created',
                        'event_data': json.dumps({'order_value': amount})
                    },
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'SHIPPED',
                        'event_timestamp': (trans_date - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'WAREHOUSE',
                        'module': 'SD',
                        'event_description': 'Goods shipped to customer',
                        'event_data': json.dumps({'tracking': f'UPS{random.randint(100000, 999999)}'})
                    },
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'BILLED',
                        'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'SYSTEM_AUTO',
                        'module': 'SD',
                        'event_description': 'Invoice generated',
                        'event_data': json.dumps({'invoice_number': f'INV-2024-{str(i).zfill(6)}'})
                    },
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'PAYMENT_RECEIVED',
                        'event_timestamp': payment_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'SYSTEM_AUTO',
                        'module': 'FI',
                        'event_description': 'Payment received and cleared',
                        'event_data': json.dumps({'payment_method': 'WIRE', 'amount': amount})
                    }
                ])
            else:
                outstanding = amount

                event_logs.extend([
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'ORDER_CREATED',
                        'event_timestamp': (trans_date - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'SALES_REP',
                        'module': 'SD',
                        'event_description': 'Sales order created',
                        'event_data': json.dumps({'order_value': amount})
                    },
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'SHIPPED',
                        'event_timestamp': (trans_date - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'WAREHOUSE',
                        'module': 'SD',
                        'event_description': 'Goods shipped to customer',
                        'event_data': json.dumps({'tracking': f'UPS{random.randint(100000, 999999)}'})
                    },
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'BILLED',
                        'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'SYSTEM_AUTO',
                        'module': 'SD',
                        'event_description': 'Invoice generated',
                        'event_data': json.dumps({'invoice_number': f'INV-2024-{str(i).zfill(6)}'})
                    }
                ])

        # Create transaction record
        transactions.append({
            'transaction_id': trans_id,
            'company_id': company_id,
            'component_type': 'DSO',
            'transaction_number': f'INV-2024-{str(i).zfill(6)}',
            'transaction_date': trans_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'amount': amount,
            'outstanding_amount': outstanding if status != 'PAID' else 0.0,
            'days_outstanding': days_outstanding,
            'gl_account': '1300000',
            'customer_vendor': customer,
            'status': status,
            'erp_metadata': json.dumps(erp_metadata)
        })

    print(f"   ✓ Generated {len(transactions)} DSO transactions")
    print(f"      - Billing disabled issue: {billing_disabled_count} transactions")
    print(f"      - Approval stuck (BWILSON): {approval_stuck_count} transactions")
    print(f"      - Credit holds: {credit_hold_count} transactions")
    print(f"      - Late payers: {late_payer_count} transactions")
    print(f"   ✓ Generated {len(event_logs)} DSO event logs")

    return transactions, event_logs


def generate_dio_transactions(company_id):
    """Generate DIO (Inventory) transactions with intentional issues"""
    print("\n[3/7] Generating DIO transactions...")

    transactions = []
    event_logs = []
    inventory_movements = []

    # Issue counts
    gr_no_valuation_count = 0
    quality_hold_count = 0
    ghost_allocation_count = 0
    obsolete_count = 0

    material_types = ['ELECTRONICS', 'RAW_MATERIALS', 'COMPONENTS', 'FINISHED_GOODS', 'PACKAGING']
    vendors = [fake.company() for _ in range(20)]

    for i in range(DIO_ITEMS):
        trans_id = str(uuid.uuid4())
        material_id = f'MAT-{str(random.randint(100000, 999999))}'
        material_type = random.choice(material_types)
        vendor = random.choice(vendors)

        # Transaction date
        trans_date = PERIOD_START + timedelta(days=random.randint(0, 364))
        days_outstanding = (ANALYSIS_DATE - trans_date).days

        # Quantity and amount
        quantity = random.randint(10, 1000)
        unit_price = round(random.uniform(10, 500), 2)
        amount = round(quantity * unit_price, 2)

        # Default status
        status = "IN_STOCK"
        erp_metadata = {
            "quantity": quantity,
            "material_type": material_type,
            "unit_price": unit_price
        }

        # Inject Issue #1: Goods receipt without valuation (87 items)
        if (gr_no_valuation_count < 87 and
            trans_date >= GR_VALUATION_ISSUE_START and
            trans_date < GR_VALUATION_ISSUE_START + timedelta(days=60)):

            status = "RECEIVED_NOT_VALUED"
            amount = 0.0  # No valuation posted
            gr_no_valuation_count += 1

            # Event log: Goods receipt but NO valuation event
            event_logs.append({
                'event_id': str(uuid.uuid4()),
                'company_id': company_id,
                'transaction_id': trans_id,
                'event_type': 'GOODS_RECEIPT',
                'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': 'RECEIVING',
                'module': 'MM',
                'event_description': 'Goods received from vendor',
                'event_data': json.dumps({'quantity': quantity, 'vendor': vendor, 'material': material_id})
            })
            # MISSING: VALUATION_POSTED event

            inventory_movements.append({
                'movement_id': str(uuid.uuid4()),
                'company_id': company_id,
                'material_id': material_id,
                'movement_date': trans_date.strftime('%Y-%m-%d'),
                'movement_type': 'GOODS_RECEIPT',
                'quantity': quantity,
                'amount': 0.0,  # No value!
                'reason_code': 'GR',
                'document_number': f'45{random.randint(10000000, 99999999)}'
            })

        # Inject Issue #2: Quality hold stall (43 items)
        elif quality_hold_count < 43 and random.random() < 0.06:
            status = "QUALITY_HOLD"
            quality_hold_count += 1

            hold_date = trans_date + timedelta(days=2)

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'GOODS_RECEIPT',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'RECEIVING',
                    'module': 'MM',
                    'event_description': 'Goods received from vendor',
                    'event_data': json.dumps({'quantity': quantity, 'vendor': vendor})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'VALUATION_POSTED',
                    'event_timestamp': (trans_date + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'MM',
                    'event_description': 'Inventory valuation posted',
                    'event_data': json.dumps({'amount': amount})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'QUALITY_HOLD_APPLIED',
                    'event_timestamp': hold_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'QA_INSPECTOR',
                    'module': 'QM',
                    'event_description': 'Quality inspection hold applied',
                    'event_data': json.dumps({'reason': 'INSPECTION_REQUIRED', 'hold_hours': (ANALYSIS_DATE - hold_date).total_seconds() / 3600})
                }
                # MISSING: QUALITY_RELEASED event - stuck >48 hours
            ])

            inventory_movements.append({
                'movement_id': str(uuid.uuid4()),
                'company_id': company_id,
                'material_id': material_id,
                'movement_date': trans_date.strftime('%Y-%m-%d'),
                'movement_type': 'GOODS_RECEIPT',
                'quantity': quantity,
                'amount': amount,
                'reason_code': 'GR',
                'document_number': f'45{random.randint(10000000, 99999999)}'
            })

        # Inject Issue #3: Ghost allocations (28 items)
        elif ghost_allocation_count < 28 and random.random() < 0.04:
            status = "RESERVED_CANCELLED_ORDER"
            ghost_allocation_count += 1

            cancelled_order = f'SO-2024-{random.randint(10000, 99999)}'

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'GOODS_RECEIPT',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'RECEIVING',
                    'module': 'MM',
                    'event_description': 'Goods received from vendor',
                    'event_data': json.dumps({'quantity': quantity, 'vendor': vendor})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'VALUATION_POSTED',
                    'event_timestamp': (trans_date + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'MM',
                    'event_description': 'Inventory valuation posted',
                    'event_data': json.dumps({'amount': amount})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'RESERVATION_CREATED',
                    'event_timestamp': (trans_date + timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'SD',
                    'event_description': 'Material reserved for sales order',
                    'event_data': json.dumps({'order_number': cancelled_order, 'quantity': quantity})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'ORDER_CANCELLED',
                    'event_timestamp': (trans_date + timedelta(days=20)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SALES_REP',
                    'module': 'SD',
                    'event_description': 'Sales order cancelled',
                    'event_data': json.dumps({'order_number': cancelled_order, 'reason': 'CUSTOMER_CANCELLED'})
                }
                # MISSING: RESERVATION_RELEASED event - ghost allocation
            ])

            inventory_movements.append({
                'movement_id': str(uuid.uuid4()),
                'company_id': company_id,
                'material_id': material_id,
                'movement_date': trans_date.strftime('%Y-%m-%d'),
                'movement_type': 'GOODS_RECEIPT',
                'quantity': quantity,
                'amount': amount,
                'reason_code': 'GR',
                'document_number': f'45{random.randint(10000000, 99999999)}'
            })

        # Inject Issue #4: Obsolete inventory (34 items, no movement >180 days)
        elif obsolete_count < 34 and trans_date < ANALYSIS_DATE - timedelta(days=180):
            status = "OBSOLETE"
            obsolete_count += 1

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'GOODS_RECEIPT',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'RECEIVING',
                    'module': 'MM',
                    'event_description': 'Goods received from vendor',
                    'event_data': json.dumps({'quantity': quantity, 'vendor': vendor})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'VALUATION_POSTED',
                    'event_timestamp': (trans_date + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'MM',
                    'event_description': 'Inventory valuation posted',
                    'event_data': json.dumps({'amount': amount})
                }
                # NO SUBSEQUENT MOVEMENT - obsolete
            ])

            inventory_movements.append({
                'movement_id': str(uuid.uuid4()),
                'company_id': company_id,
                'material_id': material_id,
                'movement_date': trans_date.strftime('%Y-%m-%d'),
                'movement_type': 'GOODS_RECEIPT',
                'quantity': quantity,
                'amount': amount,
                'reason_code': 'GR',
                'document_number': f'45{random.randint(10000000, 99999999)}'
            })

        # Normal transactions
        else:
            # Normal flow with some movements
            receipt_date = trans_date

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'GOODS_RECEIPT',
                    'event_timestamp': receipt_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'RECEIVING',
                    'module': 'MM',
                    'event_description': 'Goods received from vendor',
                    'event_data': json.dumps({'quantity': quantity, 'vendor': vendor})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'VALUATION_POSTED',
                    'event_timestamp': (receipt_date + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'MM',
                    'event_description': 'Inventory valuation posted',
                    'event_data': json.dumps({'amount': amount})
                }
            ])

            inventory_movements.append({
                'movement_id': str(uuid.uuid4()),
                'company_id': company_id,
                'material_id': material_id,
                'movement_date': receipt_date.strftime('%Y-%m-%d'),
                'movement_type': 'GOODS_RECEIPT',
                'quantity': quantity,
                'amount': amount,
                'reason_code': 'GR',
                'document_number': f'45{random.randint(10000000, 99999999)}'
            })

            # Some items have goods issues (consumption)
            if random.random() < 0.4 and days_outstanding > 30:
                issue_qty = random.randint(10, min(100, quantity))
                issue_date = receipt_date + timedelta(days=random.randint(10, min(60, days_outstanding)))
                issue_amount = round(issue_qty * unit_price, 2)

                event_logs.append({
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'GOODS_ISSUE',
                    'event_timestamp': issue_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'PRODUCTION',
                    'module': 'MM',
                    'event_description': 'Material issued to production',
                    'event_data': json.dumps({'quantity': issue_qty, 'order': f'PRO-{random.randint(10000, 99999)}'})
                })

                inventory_movements.append({
                    'movement_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'material_id': material_id,
                    'movement_date': issue_date.strftime('%Y-%m-%d'),
                    'movement_type': 'GOODS_ISSUE',
                    'quantity': -issue_qty,
                    'amount': -issue_amount,
                    'reason_code': 'GI',
                    'document_number': f'45{random.randint(10000000, 99999999)}'
                })

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
            'gl_account': '1400000',
            'customer_vendor': None,
            'status': status,
            'erp_metadata': json.dumps(erp_metadata)
        })

    print(f"   ✓ Generated {len(transactions)} DIO transactions")
    print(f"      - GR without valuation: {gr_no_valuation_count} items")
    print(f"      - Quality hold stall: {quality_hold_count} items")
    print(f"      - Ghost allocations: {ghost_allocation_count} items")
    print(f"      - Obsolete inventory: {obsolete_count} items")
    print(f"   ✓ Generated {len(event_logs)} DIO event logs")
    print(f"   ✓ Generated {len(inventory_movements)} inventory movements")

    return transactions, event_logs, inventory_movements


def generate_dpo_transactions(company_id):
    """Generate DPO (Accounts Payable) transactions with intentional issues"""
    print("\n[4/7] Generating DPO transactions...")

    transactions = []
    event_logs = []
    purchase_orders = []

    # Issue counts
    approval_stuck_count = 0
    variance_hold_count = 0
    discount_risk_count = 0
    gr_ir_mismatch_count = 0

    suppliers = [fake.company() for _ in range(30)]

    for i in range(DPO_INVOICES):
        trans_id = str(uuid.uuid4())
        po_id = str(uuid.uuid4())
        supplier = random.choice(suppliers)

        # Transaction date
        trans_date = PERIOD_START + timedelta(days=random.randint(0, 364))
        payment_terms = random.choice([30, 45, 60])
        due_date = trans_date + timedelta(days=payment_terms)
        days_outstanding = (ANALYSIS_DATE - trans_date).days

        # Amount
        amount = round(random.uniform(10000, 200000), 2)
        po_number = f'PO-2024-{str(i).zfill(5)}'

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

        # Inject Issue #1: Approval workflow bottleneck (56 invoices)
        if (approval_stuck_count < 56 and
            trans_date >= APPROVER_JSMITH_LEFT_DATE and
            trans_date < APPROVER_JSMITH_LEFT_DATE + timedelta(days=30)):

            status = "PENDING_APPROVAL"
            approval_stuck_count += 1

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'INVOICE_RECEIVED',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'AP_CLERK',
                    'module': 'FI',
                    'event_description': 'Vendor invoice received and entered',
                    'event_data': json.dumps({'invoice_amount': amount, 'vendor': supplier})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'APPROVAL_TRIGGERED',
                    'event_timestamp': (trans_date + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM',
                    'module': 'WF',
                    'event_description': 'Approval workflow started',
                    'event_data': json.dumps({'assigned_to': 'JSMITH', 'approval_threshold': 50000})
                }
                # MISSING: APPROVED event - JSMITH left company on 2024-07-22
            ])

        # Inject Issue #2: Variance holds (34 invoices with price mismatches)
        elif variance_hold_count < 34 and random.random() < 0.025:
            status = "VARIANCE_HOLD"
            variance_hold_count += 1

            po_price = amount * 0.95  # PO was 5% lower
            variance = amount - po_price

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'INVOICE_RECEIVED',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'AP_CLERK',
                    'module': 'FI',
                    'event_description': 'Vendor invoice received and entered',
                    'event_data': json.dumps({'invoice_amount': amount, 'vendor': supplier})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'VARIANCE_DETECTED',
                    'event_timestamp': (trans_date + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'MM',
                    'event_description': 'Price variance detected in 3-way match',
                    'event_data': json.dumps({
                        'po_amount': po_price,
                        'invoice_amount': amount,
                        'variance': variance,
                        'variance_percent': 5.0
                    })
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'VARIANCE_HOLD_APPLIED',
                    'event_timestamp': (trans_date + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'MM',
                    'event_description': 'Invoice blocked due to variance',
                    'event_data': json.dumps({'variance_threshold_exceeded': True})
                }
                # MISSING: VARIANCE_RESOLVED event
            ])

        # Inject Issue #3: Discount risks (23 invoices approaching 2/10 net 30)
        elif discount_risk_count < 23 and random.random() < 0.015:
            status = "DISCOUNT_AT_RISK"
            discount_risk_count += 1

            # 2% discount if paid within 10 days, net 30
            discount_date = trans_date + timedelta(days=10)
            days_to_discount = (discount_date - ANALYSIS_DATE).days

            erp_metadata['discount_terms'] = '2/10 net 30'
            erp_metadata['discount_deadline'] = discount_date.strftime('%Y-%m-%d')

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'INVOICE_RECEIVED',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'AP_CLERK',
                    'module': 'FI',
                    'event_description': 'Vendor invoice received with discount terms',
                    'event_data': json.dumps({
                        'invoice_amount': amount,
                        'vendor': supplier,
                        'discount_terms': '2/10 net 30',
                        'discount_amount': round(amount * 0.02, 2)
                    })
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'DISCOUNT_DEADLINE_WARNING',
                    'event_timestamp': (ANALYSIS_DATE - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'FI',
                    'event_description': 'Discount deadline approaching',
                    'event_data': json.dumps({'days_remaining': days_to_discount})
                }
            ])

        # Inject Issue #4: GR/IR mismatches (41 invoices waiting for 3-way match)
        elif gr_ir_mismatch_count < 41 and random.random() < 0.03:
            status = "GR_IR_MISMATCH"
            gr_ir_mismatch_count += 1

            event_logs.extend([
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'INVOICE_RECEIVED',
                    'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'AP_CLERK',
                    'module': 'FI',
                    'event_description': 'Vendor invoice received and entered',
                    'event_data': json.dumps({'invoice_amount': amount, 'vendor': supplier, 'po_number': po_number})
                },
                {
                    'event_id': str(uuid.uuid4()),
                    'company_id': company_id,
                    'transaction_id': trans_id,
                    'event_type': 'MATCHING_ATTEMPTED',
                    'event_timestamp': (trans_date + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': 'SYSTEM_AUTO',
                    'module': 'MM',
                    'event_description': '3-way match attempted',
                    'event_data': json.dumps({'result': 'FAILED', 'reason': 'GR_NOT_FOUND'})
                }
                # MISSING: GOODS_RECEIPT or MATCHING_COMPLETED event
            ])

        # Normal transactions
        else:
            # Some paid, some still open
            if random.random() < 0.25 and days_outstanding > payment_terms:
                status = "PAID"

                payment_date = trans_date + timedelta(days=payment_terms - random.randint(1, 5))

                event_logs.extend([
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'INVOICE_RECEIVED',
                        'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'AP_CLERK',
                        'module': 'FI',
                        'event_description': 'Vendor invoice received and entered',
                        'event_data': json.dumps({'invoice_amount': amount, 'vendor': supplier})
                    },
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'MATCHING_COMPLETED',
                        'event_timestamp': (trans_date + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'SYSTEM_AUTO',
                        'module': 'MM',
                        'event_description': '3-way match successful',
                        'event_data': json.dumps({'po_number': po_number})
                    },
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'PAYMENT_RELEASED',
                        'event_timestamp': payment_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'AP_MANAGER',
                        'module': 'FI',
                        'event_description': 'Payment processed to vendor',
                        'event_data': json.dumps({'payment_method': 'ACH', 'amount': amount})
                    }
                ])

                purchase_orders[-1]['status'] = 'PAID'
            else:
                event_logs.extend([
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'INVOICE_RECEIVED',
                        'event_timestamp': trans_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'AP_CLERK',
                        'module': 'FI',
                        'event_description': 'Vendor invoice received and entered',
                        'event_data': json.dumps({'invoice_amount': amount, 'vendor': supplier})
                    },
                    {
                        'event_id': str(uuid.uuid4()),
                        'company_id': company_id,
                        'transaction_id': trans_id,
                        'event_type': 'MATCHING_COMPLETED',
                        'event_timestamp': (trans_date + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': 'SYSTEM_AUTO',
                        'module': 'MM',
                        'event_description': '3-way match successful',
                        'event_data': json.dumps({'po_number': po_number})
                    }
                ])

        # Create transaction record
        transactions.append({
            'transaction_id': trans_id,
            'company_id': company_id,
            'component_type': 'DPO',
            'transaction_number': f'APINV-2024-{str(i).zfill(6)}',
            'transaction_date': trans_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'amount': amount,
            'outstanding_amount': amount if status != 'PAID' else 0.0,
            'days_outstanding': days_outstanding,
            'gl_account': '2100000',
            'customer_vendor': supplier,
            'status': status,
            'erp_metadata': json.dumps(erp_metadata)
        })

    print(f"   ✓ Generated {len(transactions)} DPO transactions")
    print(f"      - Approval stuck (JSMITH): {approval_stuck_count} invoices")
    print(f"      - Variance holds: {variance_hold_count} invoices")
    print(f"      - Discount risks: {discount_risk_count} invoices")
    print(f"      - GR/IR mismatches: {gr_ir_mismatch_count} invoices")
    print(f"   ✓ Generated {len(event_logs)} DPO event logs")
    print(f"   ✓ Generated {len(purchase_orders)} purchase orders")

    return transactions, event_logs, purchase_orders


def calculate_ccc_metrics(company_id, all_transactions):
    """Calculate CCC metrics based on generated transactions"""
    print("\n[5/7] Calculating CCC metrics...")

    df = pd.DataFrame(all_transactions)

    # Calculate DSO
    dso_df = df[df['component_type'] == 'DSO']
    total_ar = dso_df['outstanding_amount'].sum()
    daily_sales = ANNUAL_REVENUE / 365
    dso_value = round(total_ar / daily_sales, 2) if daily_sales > 0 else 0

    # Calculate DIO
    dio_df = df[df['component_type'] == 'DIO']
    total_inventory = dio_df['amount'].sum()
    cogs = ANNUAL_REVENUE * 0.65  # Assume 65% COGS
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

    output_path = OUTPUT_DIR / "ccc_metrics.csv"
    metrics_df.to_csv(output_path, index=False)

    print(f"   ✓ Created {output_path}")
    print(f"      - DSO: {dso_value} days")
    print(f"      - DIO: {dio_value} days")
    print(f"      - DPO: {dpo_value} days")
    print(f"      - CCC: {ccc_value} days")

    return metrics_df


def generate_component_details(company_id, all_transactions):
    """Generate component_details.csv with GL account breakdowns"""
    print("\n[6/7] Generating component_details.csv...")

    df = pd.DataFrame(all_transactions)

    details = []

    # DSO details
    dso_df = df[df['component_type'] == 'DSO']
    dso_total = dso_df['outstanding_amount'].sum()
    dso_days = round(dso_total / (ANNUAL_REVENUE / 365), 2)

    details.append({
        'detail_id': str(uuid.uuid4()),
        'company_id': company_id,
        'component_type': 'DSO',
        'functional_area': 'Collections',
        'gl_account': '1300000',
        'gl_account_name': 'Accounts Receivable',
        'amount': round(dso_total, 2),
        'days_contribution': dso_days
    })

    # DIO details - break down by material type
    dio_df = df[df['component_type'] == 'DIO']
    dio_total = dio_df['amount'].sum()
    cogs = ANNUAL_REVENUE * 0.65
    dio_days = round(dio_total / (cogs / 365), 2)

    details.append({
        'detail_id': str(uuid.uuid4()),
        'company_id': company_id,
        'component_type': 'DIO',
        'functional_area': 'Inventory Management',
        'gl_account': '1400000',
        'gl_account_name': 'Raw Materials Inventory',
        'amount': round(dio_total * 0.6, 2),  # 60% raw materials
        'days_contribution': round(dio_days * 0.6, 2)
    })

    details.append({
        'detail_id': str(uuid.uuid4()),
        'company_id': company_id,
        'component_type': 'DIO',
        'functional_area': 'Inventory Management',
        'gl_account': '1410000',
        'gl_account_name': 'Finished Goods Inventory',
        'amount': round(dio_total * 0.4, 2),  # 40% finished goods
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
        'gl_account': '2100000',
        'gl_account_name': 'Accounts Payable',
        'amount': round(dpo_total, 2),
        'days_contribution': dpo_days
    })

    details_df = pd.DataFrame(details)
    output_path = OUTPUT_DIR / "component_details.csv"
    details_df.to_csv(output_path, index=False)

    print(f"   ✓ Created {output_path} ({len(details)} rows)")


def main():
    """Main execution function"""

    # Generate company
    company_id = generate_company_data()

    # Generate DSO transactions and events
    dso_trans, dso_events = generate_dso_transactions(company_id)

    # Generate DIO transactions and events
    dio_trans, dio_events, inventory_movements = generate_dio_transactions(company_id)

    # Generate DPO transactions and events
    dpo_trans, dpo_events, purchase_orders = generate_dpo_transactions(company_id)

    # Combine all transactions
    all_transactions = dso_trans + dio_trans + dpo_trans
    all_events = dso_events + dio_events + dpo_events

    # Save transactions
    trans_df = pd.DataFrame(all_transactions)
    trans_output = OUTPUT_DIR / "transactions.csv"
    trans_df.to_csv(trans_output, index=False)
    print(f"\n   ✓ Created {trans_output} ({len(all_transactions)} rows)")

    # Save event logs
    events_df = pd.DataFrame(all_events)
    events_output = OUTPUT_DIR / "event_logs.csv"
    events_df.to_csv(events_output, index=False)
    print(f"   ✓ Created {events_output} ({len(all_events)} rows)")

    # Save inventory movements
    inv_df = pd.DataFrame(inventory_movements)
    inv_output = OUTPUT_DIR / "inventory_movements.csv"
    inv_df.to_csv(inv_output, index=False)
    print(f"   ✓ Created {inv_output} ({len(inventory_movements)} rows)")

    # Save purchase orders
    po_df = pd.DataFrame(purchase_orders)
    po_output = OUTPUT_DIR / "purchase_orders.csv"
    po_df.to_csv(po_output, index=False)
    print(f"   ✓ Created {po_output} ({len(purchase_orders)} rows)")

    # Calculate CCC metrics
    calculate_ccc_metrics(company_id, all_transactions)

    # Generate component details
    generate_component_details(company_id, all_transactions)

    # Summary
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

    print(f"\n📁 All files saved to: {OUTPUT_DIR.absolute()}")
    print("\n✅ Ready for ingestion!")
    print("\nNext step: python scripts/ingest_synthetic_data.py")


if __name__ == "__main__":
    main()
