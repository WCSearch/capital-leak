# Diagnostic PDF Data Validation Guide

## Overview
This guide provides step-by-step instructions to validate that the synthetic data in Supabase matches the diagnostic PDFs for the three companies:
- TechMfg Industries
- AmeriParts Distribution
- PrecisionTech Manufacturing

## Expected Values from PDFs

### CCC Metrics
| Company | Expected CCC | Notes |
|---------|-------------|-------|
| TechMfg Industries | 628.8 | High CCC indicating trapped cash |
| AmeriParts Distribution | 124.8 | Moderate CCC |
| PrecisionTech Manufacturing | 2114.7 | Very high CCC, severe trapped cash |

### Example Transactions (from PDFs)
| Company | Transaction Number | Type |
|---------|-------------------|------|
| TechMfg Industries | INV-2024-000543 | DSO (Invoice) |
| AmeriParts Distribution | PART-515688 | DIO (Inventory) |
| PrecisionTech Manufacturing | ITEM-364255 | DIO (Inventory) |

## Validation Steps

### 1. CCC Metrics Validation ✅❌

**What to check:** Verify that CCC values in the database match the PDFs

**SQL Query:**
```sql
SELECT
    c.company_name,
    m.dso_value,
    m.dio_value,
    m.dpo_value,
    m.ccc_value
FROM ccc_metrics m
JOIN companies c ON m.company_id = c.company_id
WHERE c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
ORDER BY c.company_name;
```

**Expected Results:**
- TechMfg Industries: CCC = 628.8 (±0.1 tolerance)
- AmeriParts Distribution: CCC = 124.8 (±0.1 tolerance)
- PrecisionTech Manufacturing: CCC = 2114.7 (±0.1 tolerance)

**Validation Checklist:**
- [ ] TechMfg Industries CCC matches
- [ ] AmeriParts Distribution CCC matches
- [ ] PrecisionTech Manufacturing CCC matches
- [ ] DSO, DIO, DPO values are non-zero
- [ ] CCC = DSO + DIO - DPO formula holds

---

### 2. Transaction Counts by Status ✅❌

**What to check:** Verify transaction distribution by component type and status

**SQL Query for TechMfg:**
```sql
SELECT
    c.company_name,
    t.component_type,
    t.status,
    COUNT(*) as count,
    SUM(t.outstanding_amount) as total_amount
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE c.company_name = 'TechMfg Industries'
GROUP BY c.company_name, t.component_type, t.status
ORDER BY total_amount DESC;
```

**Repeat for AmeriParts and PrecisionTech**

**Validation Checklist:**
- [ ] All three component types (DSO, DIO, DPO) present for each company
- [ ] Multiple status values exist (Current, Overdue, Aged, etc.)
- [ ] Total amounts are significant (millions of dollars)
- [ ] Distribution looks realistic (not all same status)

---

### 3. Example Transaction Verification ✅❌

**What to check:** Confirm specific example transactions from PDFs exist with correct data

**SQL Queries:**

**TechMfg Example:**
```sql
SELECT * FROM transactions
WHERE transaction_number = 'INV-2024-000543'
AND company_id = (
    SELECT company_id FROM companies
    WHERE company_name = 'TechMfg Industries'
);
```

**AmeriParts Example:**
```sql
SELECT * FROM transactions
WHERE transaction_number = 'PART-515688'
AND company_id = (
    SELECT company_id FROM companies
    WHERE company_name = 'AmeriParts Distribution'
);
```

**PrecisionTech Example:**
```sql
SELECT * FROM transactions
WHERE transaction_number = 'ITEM-364255'
AND company_id = (
    SELECT company_id FROM companies
    WHERE company_name = 'PrecisionTech Manufacturing'
);
```

**Validation Checklist:**
- [ ] TechMfg transaction INV-2024-000543 exists
- [ ] AmeriParts transaction PART-515688 exists
- [ ] PrecisionTech transaction ITEM-364255 exists
- [ ] Each has non-zero amounts
- [ ] Component types match expected (DSO for invoice, DIO for parts/items)
- [ ] Status is populated
- [ ] GL accounts are assigned

---

### 4. Event Logs Verification ✅❌

**What to check:** Verify event logs exist for the example transactions

**SQL Query Example (TechMfg):**
```sql
SELECT
    el.event_type,
    el.event_timestamp,
    el.event_description,
    el.event_data
FROM event_logs el
JOIN transactions t ON el.transaction_id = t.transaction_id
WHERE t.transaction_number = 'INV-2024-000543'
AND t.company_id = (
    SELECT company_id FROM companies
    WHERE company_name = 'TechMfg Industries'
)
ORDER BY el.event_timestamp;
```

**Repeat for other companies**

**Validation Checklist:**
- [ ] Event logs exist for TechMfg example transaction
- [ ] Event logs exist for AmeriParts example transaction
- [ ] Event logs exist for PrecisionTech example transaction
- [ ] Events show chronological progression
- [ ] Event types are realistic (created, updated, approved, etc.)
- [ ] Event timestamps are in 2024

---

### 5. Data Quality Checks ⚠️

**What to check:** Ensure no NULL values where there shouldn't be

**SQL Query:**
```sql
SELECT
    c.company_name,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN t.transaction_number IS NULL THEN 1 ELSE 0 END) as null_transaction_numbers,
    SUM(CASE WHEN t.transaction_date IS NULL THEN 1 ELSE 0 END) as null_dates,
    SUM(CASE WHEN t.amount IS NULL THEN 1 ELSE 0 END) as null_amounts,
    SUM(CASE WHEN t.status IS NULL THEN 1 ELSE 0 END) as null_statuses
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
GROUP BY c.company_name;
```

**Validation Checklist:**
- [ ] No NULL transaction numbers
- [ ] No NULL transaction dates
- [ ] No NULL amounts
- [ ] No NULL statuses
- [ ] All transactions have company_id
- [ ] All transactions have component_type

---

### 6. GL Account Distribution (DIO) ✅❌

**What to check:** Verify GL accounts follow 60/40 split for inventory (DIO)

**SQL Query:**
```sql
SELECT
    c.company_name,
    t.component_type,
    t.gl_account,
    COUNT(*) as transaction_count,
    SUM(t.amount) as total_amount,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (
            PARTITION BY c.company_name, t.component_type
        ),
        1
    ) as percent
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE t.component_type = 'DIO'
AND c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
GROUP BY c.company_name, t.component_type, t.gl_account
ORDER BY c.company_name, total_amount DESC;
```

**Expected Results:**
- Each company should have 2 GL accounts for DIO
- Split should be approximately 60% / 40%
- Typical accounts:
  - "1400 - Raw Materials" (60%)
  - "1410 - Finished Goods" (40%)

**Validation Checklist:**
- [ ] TechMfg has 2 DIO GL accounts with ~60/40 split
- [ ] AmeriParts has 2 DIO GL accounts with ~60/40 split
- [ ] PrecisionTech has 2 DIO GL accounts with ~60/40 split
- [ ] GL account names are realistic
- [ ] Both accounts have significant transaction counts

---

## Additional Validation Queries

### Check Overall Data Volume
```sql
-- Transaction counts per company
SELECT
    c.company_name,
    COUNT(*) as total_transactions,
    SUM(t.amount) as total_amount,
    MIN(t.transaction_date) as earliest_date,
    MAX(t.transaction_date) as latest_date
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
GROUP BY c.company_name
ORDER BY c.company_name;
```

### Check Component Type Distribution
```sql
-- Distribution across DSO, DIO, DPO
SELECT
    c.company_name,
    t.component_type,
    COUNT(*) as count,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as avg_amount
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
GROUP BY c.company_name, t.component_type
ORDER BY c.company_name, t.component_type;
```

### Check Status Distribution
```sql
-- Transaction status breakdown
SELECT
    c.company_name,
    t.status,
    COUNT(*) as count,
    SUM(t.outstanding_amount) as total_outstanding
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
GROUP BY c.company_name, t.status
ORDER BY c.company_name, total_outstanding DESC;
```

### Check Cross-Module Links
```sql
-- Verify cross-module link data exists
SELECT
    c.company_name,
    cml.source_module,
    cml.target_module,
    COUNT(*) as link_count
FROM cross_module_links cml
JOIN companies c ON cml.company_id = c.company_id
GROUP BY c.company_name, cml.source_module, cml.target_module
ORDER BY c.company_name, link_count DESC;
```

---

## Validation Scoring

### Pass Criteria
- ✅ **PASS**: All expected data matches, no critical issues
- ⚠️ **WARNING**: Minor discrepancies or missing optional data
- ❌ **FAIL**: Missing required data or incorrect values

### Overall Assessment

| Test Category | TechMfg | AmeriParts | PrecisionTech | Notes |
|--------------|---------|------------|---------------|-------|
| 1. CCC Metrics | | | | |
| 2. Transaction Counts | | | | |
| 3. Example Transactions | | | | |
| 4. Event Logs | | | | |
| 5. Data Quality | | | | |
| 6. GL Distribution | | | | |

---

## Running the Validation

### Option 1: Use Python Script
```bash
# With database access
python scripts/validate_diagnostic_data_postgres.py
```

### Option 2: Run SQL Manually
1. Connect to Supabase database using psql or SQL editor
2. Run queries from this guide in order
3. Compare results with expected values
4. Fill out validation checklist

### Option 3: Use Supabase Dashboard
1. Log into Supabase dashboard
2. Navigate to SQL Editor
3. Run queries one by one
4. Export results for documentation

---

## Troubleshooting

### Common Issues

**Issue: Can't connect to database**
- Check DATABASE_URL in .env file
- Verify Supabase project is active
- Ensure service role key has proper permissions

**Issue: Query returns no results**
- Check company names match exactly (case-sensitive)
- Verify data was ingested properly
- Check if tables are empty: `SELECT COUNT(*) FROM companies;`

**Issue: 403 Forbidden errors**
- Use service role key instead of anon key
- Update .streamlit/secrets.toml with service_role_key
- Check Row Level Security (RLS) policies

**Issue: Transaction numbers don't match**
- Data generation is random, specific numbers may vary
- Validate pattern and structure instead of exact match
- Ensure at least some example transactions exist

---

## Next Steps After Validation

1. **If all tests pass**: Document results and mark PDFs as accurate
2. **If warnings found**: Investigate and document acceptable variances
3. **If tests fail**:
   - Re-run data ingestion scripts
   - Check PDF generation parameters
   - Validate source data files
   - Review data generation logic

---

## Contact

For questions about this validation process:
- Check documentation in `/docs`
- Review scripts in `/scripts`
- Check issue tracker for known issues
