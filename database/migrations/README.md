# Database Migrations

This directory contains SQL migration scripts for schema changes.

## Migration Files

### 001_add_business_model_classification.sql
- **Date**: 2026-01-10
- **Description**: Adds business model classification support (Distribution vs Manufacturing)
- **Tables Added**:
  - `company_classification` - Business model classification with evidence
  - `dio_distribution_analysis` - Distribution-specific DIO metrics
  - `dio_manufacturing_analysis` - Manufacturing-specific DIO metrics
  - Detail tables for drill-down analysis
- **Tables Modified**:
  - Added `business_model` column to `component_details`, `trapped_cash_analysis`, `transactions`

## Running Migrations

### PostgreSQL (Local)
```bash
psql -U postgres -d wcsearch -f database/migrations/001_add_business_model_classification.sql
```

### Supabase
```bash
# Using Supabase CLI
supabase db push

# Or apply manually in Supabase SQL Editor
# Copy and paste migration file contents
```

## Migration History

Track applied migrations in your deployment:

| Migration | Date Applied | Applied By | Notes |
|-----------|-------------|------------|-------|
| 001 | YYYY-MM-DD | Name | Initial business model classification |

## Rollback

To rollback migration 001:

```sql
-- Drop new tables
DROP VIEW IF EXISTS dio_analysis_summary;
DROP VIEW IF EXISTS companies_with_classification;

DROP TABLE IF EXISTS dio_manufacturing_qa_detail CASCADE;
DROP TABLE IF EXISTS dio_manufacturing_yield_detail CASCADE;
DROP TABLE IF EXISTS dio_manufacturing_bottleneck_detail CASCADE;
DROP TABLE IF EXISTS dio_distribution_movement_detail CASCADE;
DROP TABLE IF EXISTS dio_distribution_stockout_detail CASCADE;
DROP TABLE IF EXISTS dio_distribution_velocity_detail CASCADE;

DROP TABLE IF EXISTS dio_manufacturing_analysis CASCADE;
DROP TABLE IF EXISTS dio_distribution_analysis CASCADE;
DROP TABLE IF EXISTS company_classification CASCADE;

-- Remove added columns
ALTER TABLE component_details DROP COLUMN IF EXISTS business_model;
ALTER TABLE component_details DROP COLUMN IF EXISTS calculation_method;
ALTER TABLE trapped_cash_analysis DROP COLUMN IF EXISTS business_model;
ALTER TABLE trapped_cash_analysis DROP COLUMN IF EXISTS calculation_method;
ALTER TABLE transactions DROP COLUMN IF EXISTS business_model;
```

⚠️ **Warning**: Rollback will delete all business model classification data. Backup before rolling back!
