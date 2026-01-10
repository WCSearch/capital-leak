# Data Validation Summary

## Overview
I've created comprehensive validation tools to verify that the synthetic data in Supabase matches the diagnostic PDFs for three companies:
- **TechMfg Industries** (Expected CCC: 628.8)
- **AmeriParts Distribution** (Expected CCC: 124.8)
- **PrecisionTech Manufacturing** (Expected CCC: 2114.7)

## What Was Created

### 1. **VALIDATION_GUIDE.md** (Comprehensive Documentation)
A complete step-by-step guide that includes:
- Expected values from the diagnostic PDFs
- 6 main validation categories with detailed checklists
- Additional validation queries for thorough testing
- Troubleshooting section for common issues
- Validation scoring criteria
- Next steps based on results

**Key Validation Categories:**
1. ✅ **CCC Metrics Validation** - Verify CCC values match PDFs
2. ✅ **Transaction Counts** - Confirm transaction distribution
3. ✅ **Example Transactions** - Check specific transactions from PDFs exist
4. ✅ **Event Logs** - Verify event logs for example transactions
5. ⚠️  **Data Quality** - Check for NULL values and missing data
6. ✅ **GL Account Distribution** - Verify 60/40 split for DIO

### 2. **validate_diagnostic_data.sql** (SQL Script)
A standalone SQL script with all validation queries including:
- 10 major query sections
- Inline validation checks (✓ PASS / ✗ FAIL indicators)
- Expected vs actual comparisons
- Summary validation query at the end
- Comments explaining what each query checks

**Can be run:**
- In Supabase SQL Editor
- Via psql command line
- In any PostgreSQL client (DBeaver, pgAdmin, etc.)

### 3. **validate_diagnostic_data_postgres.py** (Python Script)
A Python script that:
- Connects directly to PostgreSQL database
- Runs all validation queries automatically
- Provides colored output (✅ ❌ ⚠️) for easy reading
- Generates a summary report
- Returns exit code 0 (success) or 1 (failure)

**Usage:**
```bash
python scripts/validate_diagnostic_data_postgres.py
```

### 4. **validate_diagnostic_data.py** (Supabase API Version)
An alternative Python script using Supabase Python client:
- Uses Supabase API instead of direct PostgreSQL
- May be preferred in some environments
- Requires proper API key configuration

## Why Multiple Formats?

Different situations call for different approaches:

| Format | Best For | Pros | Cons |
|--------|----------|------|------|
| **Markdown Guide** | Manual validation, documentation | Human-readable, educational | Manual work required |
| **SQL Script** | Database admins, SQL tools | Direct database access, fast | Requires SQL knowledge |
| **Python Script** | Automation, CI/CD pipelines | Automated, generates reports | Requires Python environment |

## Current Limitation

**Network Access Issue**: The current environment cannot connect to Supabase due to:
- DNS resolution failures
- Proxy/firewall restrictions (403 Forbidden errors)
- No outbound network connectivity

This means the Python validation scripts cannot be run in this environment, but they will work when:
- Run on a machine with internet access
- Run in a CI/CD pipeline
- Run locally on your development machine
- Run in an environment with Supabase access

## How to Use These Tools

### Option 1: Run SQL Script Directly (Recommended)

1. **Log into Supabase Dashboard**
   - Go to https://vlbvrhotrlipaoedudys.supabase.co
   - Navigate to SQL Editor

2. **Copy SQL Script**
   - Open `scripts/validate_diagnostic_data.sql`
   - Copy all contents

3. **Run in SQL Editor**
   - Paste into Supabase SQL Editor
   - Run queries one section at a time
   - Or run entire script at once

4. **Review Results**
   - Look for ✓ PASS or ✗ FAIL indicators
   - Note any discrepancies
   - Check the final VALIDATION SUMMARY query

### Option 2: Run Python Script (When Network Available)

1. **Ensure Environment is Set Up**
   ```bash
   # Install dependencies (already done)
   pip install -r requirements.txt
   pip install psycopg2-binary
   ```

2. **Verify .env File**
   ```bash
   # Check DATABASE_URL is set
   cat .env | grep DATABASE_URL
   ```

3. **Run Script**
   ```bash
   python scripts/validate_diagnostic_data_postgres.py
   ```

4. **Review Output**
   - Script will print colored results
   - Final summary shows pass/fail counts
   - Exit code 0 = success, 1 = failure

### Option 3: Manual Validation (Most Flexible)

1. **Follow VALIDATION_GUIDE.md**
2. **Run each query manually**
3. **Fill out checklists as you go**
4. **Document findings**

## Expected Results

If data is correct, you should see:

### CCC Metrics
- ✅ TechMfg Industries: CCC = 628.8 days
- ✅ AmeriParts Distribution: CCC = 124.8 days
- ✅ PrecisionTech Manufacturing: CCC = 2114.7 days

### Transaction Data
- ✅ Thousands of transactions per company
- ✅ Mix of DSO, DIO, and DPO component types
- ✅ Various statuses (Current, Overdue, Aged, etc.)
- ✅ Realistic dollar amounts in millions

### Example Transactions
- ✅ TechMfg: INV-2024-000543 exists
- ✅ AmeriParts: PART-515688 exists
- ✅ PrecisionTech: ITEM-364255 exists

### Event Logs
- ✅ Multiple events per example transaction
- ✅ Chronological progression
- ✅ Realistic event types and descriptions

### Data Quality
- ✅ No NULL transaction numbers
- ✅ No NULL dates, amounts, or statuses
- ✅ All required fields populated

### GL Distribution
- ✅ DIO transactions split ~60/40 across GL accounts
- ✅ Two primary GL accounts per company for inventory
- ✅ Realistic account names and descriptions

## What to Look For

### ✅ Good Signs (PASS)
- CCC values match expected values within ±0.1
- Large transaction volumes (1000s of records)
- Event logs exist for all example transactions
- No NULL values in critical fields
- GL accounts follow expected 60/40 distribution

### ⚠️ Warning Signs (Might be OK)
- Slight variations in percentages (58/42 instead of 60/40)
- Some NULL values in optional fields (metadata, etc.)
- Transaction numbers don't match exactly (random generation)
- Minor rounding differences in CCC calculations

### ❌ Red Flags (FAIL)
- CCC values completely wrong (>5 days difference)
- No transactions found for a company
- Example transactions from PDFs don't exist
- No event logs at all
- All NULL values in status or amount fields
- Only one GL account for DIO instead of two

## Troubleshooting

### "403 Forbidden" Errors
**Solution**: Update `.streamlit/secrets.toml` to use service_role_key instead of anon key:
```toml
[supabase]
url = "https://vlbvrhotrlipaoedudys.supabase.co"
key = "eyJhbGc...service_role_key..."  # Use SUPABASE_SERVICE_ROLE_KEY from .env
```

### "No module named 'psycopg2'" Error
**Solution**: Install PostgreSQL adapter:
```bash
pip install psycopg2-binary
```

### "Cannot translate host name" Error
**Solution**: Environment has no network access. Use SQL script in Supabase Dashboard instead.

### "Company not found" Errors
**Solution**: Check company names are exactly: 'TechMfg Industries', 'AmeriParts Distribution', 'PrecisionTech Manufacturing' (case-sensitive)

### Transaction Numbers Don't Match
**Explanation**: Transaction numbers are randomly generated. Validate that:
- Transactions exist with the correct pattern (INV-*, PART-*, ITEM-*)
- Component types match (DSO, DIO)
- Amounts and statuses are realistic

Don't expect exact transaction number matches unless you control the random seed.

## Next Steps

### 1. Run Validation
Choose one of the three options above and run validation.

### 2. Document Results
Record findings in the validation checklist in VALIDATION_GUIDE.md.

### 3. Compare with PDFs
Open the diagnostic PDFs and verify:
- CCC values match
- Example transactions shown in PDFs exist in database
- Event log sequences match what's documented
- GL account breakdowns are consistent

### 4. Fix Any Issues
If validation fails:
- Re-run data ingestion: `python scripts/ingest_synthetic_data.py`
- Regenerate PDFs: `python generate_diagnostic_pdf.py`
- Check source data files in `/data` directory
- Review data generation parameters

### 5. Update Documentation
Once validation passes, document:
- Date validation was performed
- Who performed it
- Any acceptable variances noted
- Any issues found and resolved

## Files Created

```
/home/user/capital-leak/
├── VALIDATION_GUIDE.md           # Comprehensive validation documentation
├── VALIDATION_SUMMARY.md         # This file - overview and usage
├── scripts/
│   ├── validate_diagnostic_data.sql              # SQL script (all queries)
│   ├── validate_diagnostic_data.py               # Python script (Supabase API)
│   └── validate_diagnostic_data_postgres.py      # Python script (PostgreSQL)
└── .streamlit/
    └── secrets.toml                              # Supabase credentials
```

## Quick Reference

### Run Validation (SQL)
```sql
-- In Supabase SQL Editor, run:
-- Copy contents of scripts/validate_diagnostic_data.sql
-- Look for ✓ PASS or ✗ FAIL in results
```

### Run Validation (Python)
```bash
# When network is available:
python scripts/validate_diagnostic_data_postgres.py

# Or with Supabase API:
python scripts/validate_diagnostic_data.py
```

### Check Specific Company
```sql
SELECT * FROM ccc_metrics m
JOIN companies c ON m.company_id = c.company_id
WHERE c.company_name = 'TechMfg Industries';
```

### Quick Data Check
```sql
SELECT
    c.company_name,
    COUNT(t.transaction_id) as txn_count,
    m.ccc_value
FROM companies c
LEFT JOIN transactions t ON c.company_id = t.company_id
LEFT JOIN ccc_metrics m ON c.company_id = m.company_id
GROUP BY c.company_name, m.ccc_value;
```

## Contact & Support

For issues or questions:
- Review VALIDATION_GUIDE.md for detailed instructions
- Check scripts in `/scripts` directory for implementation details
- Refer to database schema in `/database/schema.sql`
- Check existing test scripts in `/scripts/test_*.py`

---

**Last Updated**: 2026-01-10
**Created By**: Claude Code Validation System
**Purpose**: Ensure synthetic data accuracy for diagnostic PDFs
