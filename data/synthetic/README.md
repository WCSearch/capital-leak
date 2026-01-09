# Synthetic ERP Datasets

This directory contains three synthetic datasets for working capital analysis, each representing a different industry and ERP system.

## Datasets

### 1. SAP ECC 6.0 - TechMfg Industries
**Industry:** Electronics Manufacturing
**Annual Revenue:** $85,000,000
**Location:** `data/synthetic/sap/`

**Volumes:**
- DSO Transactions: 2,500
- DIO Items: 800
- DPO Invoices: 1,800

**Injected Issues:**
- Billing trigger disabled (143 invoices)
- Approval workflow stuck - BWILSON left (31 invoices)
- Credit policy change holds (146 invoices)
- GR without valuation (87 items)
- Quality hold stalls (43 items)
- AP approval stuck - JSMITH left (56 invoices)
- Variance holds (34 invoices)

**ERP-Specific Details:**
- Modules: SD, MM, FI, WF, QM
- GL Accounts: 1300000 (AR), 1400000/1410000 (Inventory), 2100000 (AP)
- Event Types: ORDER_CREATED, SHIPPED, BILLED, GOODS_RECEIPT, VALUATION_POSTED

---

### 2. Infor CloudSuite Distribution - AmeriParts Distribution
**Industry:** Automotive Parts Wholesale Distribution
**Annual Revenue:** $120,000,000
**Location:** `data/synthetic/infor/`

**Volumes:**
- DSO Transactions: 3,200 (higher volume, lower $ per transaction)
- DIO Items: 1,200
- DPO Invoices: 2,400

**Injected Issues:**
- Credit hold backlog from system upgrade (156 orders)
- Payment application delays - lockbox processor changed (89 invoices)
- Unapplied cash - poor remittance detail (67 payments)
- Cycle count adjustments not posted (200+ items)
- Cross-dock staging timeouts (145 orders)
- RTV authorization delays (78 items)
- PO receipt matching failures (92 invoices)
- Freight invoice backlog (187 invoices)

**ERP-Specific Details:**
- Modules: OE, IC, AR/AP, WF, QC
- GL Accounts: 11200 (AR), 13000/13100 (Inventory), 21000 (AP)
- Event Types: ORDER_ENTERED, SHIPMENT_CONFIRMED, INVOICE_POSTED, RECEIPT_POSTED, CYCLE_COUNT_VARIANCE

**Industry Characteristics:**
- Multi-location distribution (5 warehouses)
- 8,000+ SKUs
- Mix of stock orders and drop-ship
- High volume, lower margin (~18%)
- Payment terms: Net 30

---

### 3. Oracle E-Business Suite R12.2 - PrecisionTech Manufacturing
**Industry:** Industrial Equipment Manufacturing
**Annual Revenue:** $95,000,000
**Location:** `data/synthetic/oracle/`

**Volumes:**
- DSO Transactions: 1,800 (lower volume, higher $ per transaction)
- DIO Items: 900
- DPO Invoices: 1,600

**Injected Issues:**
- Progress billing not triggered (43 projects)
- Customer acceptance delays (67 orders)
- Retainage invoicing backlog (34 projects)
- Work order release delays (156 orders)
- Subcontract PO delays (89 items)
- Quarantine hold - no MRB disposition (112 items)
- PO change order approvals (78 invoices)
- Subcontractor milestone payments (45 invoices)
- Supplier terms mismatch (134 invoices)

**ERP-Specific Details:**
- Modules: AR, INV, GL, AME, QA
- GL Accounts: 1120 (AR), 1510/1520 (Inventory), 2100 (AP)
- Event Types: ORDER_BOOKED, SHIP_CONFIRM, INVOICE_VALIDATED, WORK_ORDER_RELEASED, INSPECTION_FAILED

**Industry Characteristics:**
- Engineer-to-order and configure-to-order
- Complex BOMs, multi-level assemblies
- Mix of in-house manufacturing and subcontract
- Longer lead times (30-90 days)
- Payment terms: Varies (Net 30 to Progress Billing)

---

## File Structure

Each dataset contains the following CSV files:

1. **companies.csv** - Company master data (1 row)
2. **transactions.csv** - All DSO/DIO/DPO transactions
3. **event_logs.csv** - ERP event audit trail with timestamps
4. **inventory_movements.csv** - Material movements (receipts, issues)
5. **purchase_orders.csv** - Purchase order data for DPO analysis
6. **ccc_metrics.csv** - Calculated Cash Conversion Cycle metrics
7. **component_details.csv** - GL account breakdown for CCC components

## Generation

To regenerate any dataset:

```bash
# SAP dataset
python scripts/generate_synthetic_data.py --dataset sap

# Infor dataset
python scripts/generate_synthetic_data.py --dataset infor

# Oracle dataset
python scripts/generate_synthetic_data.py --dataset oracle
```

## Data Quality

- **Reproducibility:** All datasets use `RANDOM_SEED = 42` for consistent generation
- **ERP Authenticity:** Event types, module names, and GL accounts match real ERP systems
- **Industry Patterns:** Transaction volumes and amounts reflect industry norms
- **Intentional Issues:** Each dataset has 8-12 specific root cause issues injected
- **Event Correlation:** Event logs provide full audit trail for forensic analysis

## Use Cases

1. **Dashboard Testing:** Validate working capital analytics across different ERPs
2. **Sales Demos:** Show cross-ERP capability with industry-specific examples
3. **Forensic Validation:** Test event log analysis and root cause detection
4. **PDF Report Generation:** Generate professional diagnostic reports

## Next Steps

After generating datasets, use the ingestion script to load into Supabase:

```bash
python scripts/ingest_synthetic_data.py --dataset sap
python scripts/ingest_synthetic_data.py --dataset infor
python scripts/ingest_synthetic_data.py --dataset oracle
```

Then generate diagnostic PDFs:

```bash
python scripts/generate_diagnostic_pdf.py --company-id <company_id>
```
