# Synthetic SAP Data Generation & Ingestion Pipeline

This directory contains scripts to generate realistic synthetic SAP data and ingest it into Supabase for testing the Working Capital Analysis Dashboard.

## Overview

The pipeline consists of three main scripts:

1. **`generate_synthetic_sap_data.py`** - Generates realistic SAP transaction data with intentional issues
2. **`ingest_synthetic_data.py`** - Loads the generated CSV files into Supabase
3. **`validate_synthetic_data.py`** - Validates the data was loaded correctly and issues are present

## Prerequisites

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Supabase Credentials

You need valid Supabase credentials to run the ingestion and validation scripts.

#### Option A: Update `.streamlit/secrets.toml`

```toml
[supabase]
url = "https://YOUR_PROJECT_REF.supabase.co"
key = "YOUR_SUPABASE_ANON_KEY"
```

#### Option B: Update `.env` file

```bash
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=YOUR_SUPABASE_ANON_KEY
```

**Where to find your Supabase credentials:**
1. Go to your Supabase project dashboard
2. Navigate to Settings → API
3. Copy the "Project URL" and "anon/public" key
4. The anon key typically starts with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

## Usage

### Step 1: Generate Synthetic Data

```bash
python scripts/generate_synthetic_sap_data.py
```

**Output:**
- Creates 7 CSV files in `data/synthetic/`:
  - `companies.csv` - Company profile (1 row)
  - `transactions.csv` - 5,100 transactions (DSO: 2,500, DIO: 800, DPO: 1,800)
  - `event_logs.csv` - ~15,000 event log entries
  - `ccc_metrics.csv` - Calculated CCC metrics (1 row)
  - `component_details.csv` - GL account breakdowns (4 rows)
  - `inventory_movements.csv` - Inventory movement history (~1,000 rows)
  - `purchase_orders.csv` - Purchase order records (~1,800 rows)

**What's Generated:**
- Company: TechMfg Industries (Electronics Manufacturing, $85M revenue)
- Period: January 2024 - December 2024
- Analysis Date: 2025-01-07
- Reproducible data using random seed: 42

### Step 2: Ingest into Supabase

```bash
python scripts/ingest_synthetic_data.py
```

**Features:**
- Batch inserts (100 rows at a time) with progress bars
- Proper error handling and rollback
- Validates foreign key relationships
- Parses JSON fields (erp_metadata, event_data)
- Converts dates to proper format

**Note:** If you get a `403 Forbidden` error, verify your Supabase credentials are correct.

### Step 3: Validate Data

```bash
python scripts/validate_synthetic_data.py
```

**Validation Checks:**
- ✅ Row counts match CSV files
- ✅ Referential integrity (foreign keys)
- ✅ Date ranges are correct
- ✅ All intentional issues are present

**Output:**
- Console report with pass/fail status
- Detailed validation report saved to `data/synthetic/validation_report.txt`

## Intentional Issues for Testing

The synthetic data includes specific issues designed to test the dashboard's forensic capabilities:

### DSO Issues

1. **Billing Trigger Disabled** (143 invoices)
   - Date: 2024-03-17 onwards
   - Symptom: Orders fulfilled and shipped but never billed
   - Status: `FULFILLED_NOT_BILLED`

2. **Approver Left Company** (31 invoices)
   - Approver: BWILSON
   - Left Date: 2024-06-15
   - Symptom: Invoices stuck in approval workflow
   - Status: `PENDING_APPROVAL`

3. **Credit Policy Change** (~150-200 invoices)
   - Date: 2024-08-01
   - Symptom: Increased credit holds after policy change
   - Status: `CREDIT_HOLD`

4. **Late Payers** (187 invoices)
   - Behavioral issue, no system problem
   - Status: `OVERDUE`

### DIO Issues

1. **Goods Receipt Without Valuation** (87 items)
   - Date: 2024-05-12 onwards
   - Symptom: Materials received but $0 inventory value
   - Status: `RECEIVED_NOT_VALUED`
   - Missing Event: `VALUATION_POSTED`

2. **Quality Hold Stall** (43 items)
   - Symptom: Items stuck in QA inspection >48 hours
   - Status: `QUALITY_HOLD`
   - Missing Event: `QUALITY_RELEASED`

3. **Ghost Allocations** (28 items)
   - Symptom: Reservations exist for cancelled sales orders
   - Status: `RESERVED_CANCELLED_ORDER`
   - Missing Event: `RESERVATION_RELEASED`

4. **Obsolete Inventory** (34 items)
   - Symptom: No movement in >180 days
   - Status: `OBSOLETE`

### DPO Issues

1. **Approval Workflow Bottleneck** (56 invoices)
   - Approver: JSMITH
   - Left Date: 2024-07-22
   - Symptom: Invoices stuck in approval
   - Status: `PENDING_APPROVAL`

2. **Variance Holds** (34 invoices)
   - Symptom: Price mismatch between PO and invoice (5% difference)
   - Status: `VARIANCE_HOLD`

3. **Discount Risks** (23 invoices)
   - Terms: 2/10 net 30
   - Symptom: Approaching discount deadline
   - Status: `DISCOUNT_AT_RISK`

4. **GR/IR Mismatches** (41 invoices)
   - Symptom: Waiting for 3-way match (PO, GR, Invoice)
   - Status: `GR_IR_MISMATCH`

## Expected Metrics

After ingestion, the dashboard should show:

- **DSO:** ~70-80 days (elevated due to intentional issues)
- **DIO:** ~85-95 days (elevated due to valuation issues)
- **DPO:** ~40-45 days
- **CCC:** ~115-125 days

## Troubleshooting

### Issue: `403 Forbidden` during ingestion

**Solution:** Update your Supabase credentials in `.streamlit/secrets.toml` or `.env` file with valid API keys from your Supabase project dashboard.

### Issue: `ModuleNotFoundError`

**Solution:** Install dependencies: `pip install -r requirements.txt`

### Issue: Validation checks fail

**Solution:**
1. Re-run the generation script: `python scripts/generate_synthetic_sap_data.py`
2. Clear existing data in Supabase tables
3. Re-run ingestion: `python scripts/ingest_synthetic_data.py`

### Issue: Data looks unrealistic

**Solution:** The script uses a fixed random seed (42) for reproducibility. To generate different data, modify the `RANDOM_SEED` constant in `generate_synthetic_sap_data.py`.

## Files Generated

All output files are saved to `data/synthetic/`:

```
data/synthetic/
├── companies.csv              (1 row)
├── transactions.csv           (5,100 rows)
├── event_logs.csv            (~15,000 rows)
├── ccc_metrics.csv           (1 row)
├── component_details.csv     (4 rows)
├── inventory_movements.csv   (~1,000 rows)
├── purchase_orders.csv       (~1,800 rows)
└── validation_report.txt     (generated after validation)
```

## Testing the Dashboard

After running all three scripts successfully:

```bash
streamlit run app/dashboard.py
```

The dashboard should now:
- ✅ Load without errors
- ✅ Display data for all three components (DSO, DIO, DPO)
- ✅ Show event log forensics with detected issues
- ✅ Highlight root causes in the heatmap
- ✅ Populate the execution queue with high-impact items
- ✅ Enable generation of a sample diagnostic report

## Support

For issues or questions about the synthetic data pipeline, please refer to the main project README or create an issue in the repository.
