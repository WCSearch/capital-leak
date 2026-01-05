# Sample Data Directory

This directory contains sample data files for testing the Capital Leak Analysis Platform.

## Data File Formats

### Invoices (invoices.csv)

Required fields for invoice data:

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| invoice_id | String | Unique invoice identifier | INV-2024-001 |
| customer_id | String | Customer identifier | CUST-123 |
| customer_name | String | Customer name | Acme Corp |
| invoice_date | Date | Invoice creation date | 2024-01-15 |
| due_date | Date | Payment due date | 2024-02-15 |
| payment_date | Date | Actual payment date (null if unpaid) | 2024-02-10 |
| amount | Decimal | Invoice amount | 15000.00 |
| currency | String | Currency code | USD |
| status | String | Invoice status | PAID, OPEN, OVERDUE |

**Example CSV:**
```csv
invoice_id,customer_id,customer_name,invoice_date,due_date,payment_date,amount,currency,status
INV-2024-001,CUST-123,Acme Corp,2024-01-15,2024-02-15,2024-02-10,15000.00,USD,PAID
INV-2024-002,CUST-456,TechStart Inc,2024-01-20,2024-02-20,,25000.00,USD,OPEN
INV-2024-003,CUST-789,Global Industries,2024-01-25,2024-02-10,,50000.00,USD,OVERDUE
```

### Inventory (inventory.csv)

Required fields for inventory data:

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| sku | String | Product SKU | SKU-001 |
| product_name | String | Product name | Widget A |
| category | String | Product category | Electronics |
| quantity | Integer | Quantity | 100 |
| unit_cost | Decimal | Cost per unit | 50.00 |
| total_value | Decimal | Total value | 5000.00 |
| location | String | Warehouse location | WH-01 |
| movement_date | Date | Transaction date | 2024-01-15 |
| movement_type | String | Type of movement | RECEIPT, SALE, PURCHASE |

**Example CSV:**
```csv
sku,product_name,category,quantity,unit_cost,total_value,location,movement_date,movement_type
SKU-001,Widget A,Electronics,100,50.00,5000.00,WH-01,2024-01-15,RECEIPT
SKU-002,Widget B,Electronics,50,75.00,3750.00,WH-01,2024-01-16,PURCHASE
SKU-001,Widget A,Electronics,-20,50.00,1000.00,WH-01,2024-01-20,SALE
```

### Payables (payables.csv)

Required fields for payable data:

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| payable_id | String | Unique payable identifier | PAY-2024-001 |
| vendor_id | String | Vendor identifier | VEND-123 |
| vendor_name | String | Vendor name | Supplier One |
| invoice_date | Date | Invoice date | 2024-01-15 |
| due_date | Date | Payment due date | 2024-02-15 |
| payment_date | Date | Actual payment date | 2024-02-14 |
| amount | Decimal | Payable amount | 10000.00 |
| currency | String | Currency code | USD |
| status | String | Payable status | PAID, OPEN, APPROVED |

**Example CSV:**
```csv
payable_id,vendor_id,vendor_name,invoice_date,due_date,payment_date,amount,currency,status
PAY-2024-001,VEND-123,Supplier One,2024-01-15,2024-02-15,2024-02-14,10000.00,USD,PAID
PAY-2024-002,VEND-456,Supplier Two,2024-01-20,2024-02-20,,15000.00,USD,OPEN
PAY-2024-003,VEND-789,Logistics Inc,2024-01-25,2024-02-25,2024-02-20,5000.00,USD,PAID
```

### Revenue (revenue.csv)

Required fields for revenue/COGS data:

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| period_start | Date | Period start date | 2024-01-01 |
| period_end | Date | Period end date | 2024-01-31 |
| revenue | Decimal | Total revenue | 500000.00 |
| cogs | Decimal | Cost of goods sold | 300000.00 |
| currency | String | Currency code | USD |

**Example CSV:**
```csv
period_start,period_end,revenue,cogs,currency
2024-01-01,2024-01-31,500000.00,300000.00,USD
2024-02-01,2024-02-29,550000.00,330000.00,USD
2024-03-01,2024-03-31,600000.00,360000.00,USD
```

## Date Format

All dates should be in ISO format: `YYYY-MM-DD`

Supported formats:
- `2024-01-15` (preferred)
- `01/15/2024`
- `15/01/2024`
- `20240115`

## Status Values

### Invoice Status
- `OPEN` - Invoice issued, not yet paid
- `PAID` - Invoice paid in full
- `OVERDUE` - Past due date, not paid
- `CANCELLED` - Invoice cancelled
- `PARTIAL` - Partially paid

### Payable Status
- `OPEN` - Received, not yet paid
- `APPROVED` - Approved for payment
- `PAID` - Payment made
- `CANCELLED` - Cancelled
- `DISPUTED` - Under dispute

### Inventory Movement Types
- `RECEIPT` - Goods received into inventory
- `PURCHASE` - Purchased goods
- `SALE` - Goods sold
- `ADJUSTMENT` - Inventory adjustment
- `TRANSFER` - Transfer between locations
- `RETURN` - Customer/supplier return

## Loading Sample Data

### Using Python

```python
from app.main import CapitalLeakAnalyzer
from config.field_mappings import ERPSystem

analyzer = CapitalLeakAnalyzer()

# Load each data type
analyzer.load_data_from_csv('invoice', 'data/sample/invoices.csv', ERPSystem.CUSTOM)
analyzer.load_data_from_csv('inventory', 'data/sample/inventory.csv', ERPSystem.CUSTOM)
analyzer.load_data_from_csv('payable', 'data/sample/payables.csv', ERPSystem.CUSTOM)
analyzer.load_data_from_csv('revenue', 'data/sample/revenue.csv', ERPSystem.CUSTOM)
```

### Using Custom Script

```python
import sys
sys.path.insert(0, '../..')

from etl import CSVExtractor, DataTransformer, DataLoader
from config.field_mappings import ERPSystem

# Extract
extractor = CSVExtractor()
invoice_data = extractor.extract('invoices.csv')

# Transform
transformer = DataTransformer(ERPSystem.CUSTOM)
transformed = transformer.transform_invoices(invoice_data)

# Load
loader = DataLoader()
loaded = loader.load_invoices(transformed)
print(f"Loaded {loaded} invoices")
```

## Generating Test Data

You can generate larger test datasets using this Python script:

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate sample invoices
num_invoices = 1000
start_date = datetime(2024, 1, 1)

invoices = []
for i in range(num_invoices):
    invoice_date = start_date + timedelta(days=np.random.randint(0, 365))
    due_date = invoice_date + timedelta(days=30)

    # 70% paid, 20% open, 10% overdue
    status_choice = np.random.choice(['PAID', 'OPEN', 'OVERDUE'], p=[0.7, 0.2, 0.1])

    if status_choice == 'PAID':
        payment_date = invoice_date + timedelta(days=np.random.randint(15, 45))
    else:
        payment_date = None

    invoices.append({
        'invoice_id': f'INV-2024-{i:05d}',
        'customer_id': f'CUST-{np.random.randint(1, 100):03d}',
        'customer_name': f'Customer {np.random.randint(1, 100)}',
        'invoice_date': invoice_date.strftime('%Y-%m-%d'),
        'due_date': due_date.strftime('%Y-%m-%d'),
        'payment_date': payment_date.strftime('%Y-%m-%d') if payment_date else '',
        'amount': round(np.random.uniform(1000, 100000), 2),
        'currency': 'USD',
        'status': status_choice
    })

df = pd.DataFrame(invoices)
df.to_csv('generated_invoices.csv', index=False)
print(f"Generated {num_invoices} sample invoices")
```

## Data Quality Guidelines

### Required Data
For accurate analysis, ensure you have:
1. **At least 90 days of data** for meaningful trends
2. **Complete invoice data** with dates and amounts
3. **Revenue and COGS** for each analysis period
4. **Inventory movements** for DIO calculation
5. **Payables data** for DPO calculation

### Data Quality Checks
- No missing values in required fields
- Dates in valid range
- Amounts are positive numbers
- Status values match expected values
- Customer/Vendor IDs are consistent

### Common Issues

**Issue:** Analysis returns zero values
**Solution:** Ensure revenue and COGS data exists for the period

**Issue:** DSO/DIO/DPO are extremely high
**Solution:** Check for outliers in invoice amounts or dates

**Issue:** Missing customers in analysis
**Solution:** Verify customer_id is consistent across files

## ERP-Specific Formats

### SAP Export Format

SAP uses specific field names. Create mappings in `config/field_mappings.py` or use pre-configured SAP mappings:

```python
from config.field_mappings import ERPSystem

analyzer.load_data_from_csv('invoice', 'sap_export.csv', ERPSystem.SAP)
```

### Oracle ERP Format

```python
analyzer.load_data_from_csv('invoice', 'oracle_export.csv', ERPSystem.ORACLE)
```

### NetSuite Format

```python
analyzer.load_data_from_csv('invoice', 'netsuite_export.csv', ERPSystem.NETSUITE)
```

## Exporting Data from Your ERP

### General Guidelines
1. Export in CSV format
2. Include all required fields
3. Use ISO date format (YYYY-MM-DD)
4. Export at least 12 months of data
5. Include both open and closed transactions

### SQL Export Example

If you have database access to your ERP:

```sql
-- Export invoices
COPY (
    SELECT
        invoice_id,
        customer_id,
        customer_name,
        invoice_date,
        due_date,
        payment_date,
        amount,
        currency,
        status
    FROM invoices
    WHERE invoice_date >= '2024-01-01'
) TO '/path/to/invoices.csv' WITH CSV HEADER;
```

## Need Help?

- Check `docs/SETUP.md` for detailed setup instructions
- Review main `README.md` for usage examples
- See field mappings in `config/field_mappings.py`
- Open an issue on GitHub for support
