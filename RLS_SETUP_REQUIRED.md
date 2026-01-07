# RLS Setup Required for Data Ingestion

## Current Status

✅ **Completed:**
- Generated 18,820 synthetic SAP records
- All CSV files created in `data/synthetic/`
- Python dependencies installed

❌ **Blocked:**
- Data ingestion failed with 403 Forbidden errors
- Cause: Supabase Row Level Security (RLS) blocks API inserts

## Quick Fix

### Option 1: Run SQL in Supabase Dashboard (Recommended)

1. **Open Supabase Dashboard:**
   ```
   https://app.supabase.com/project/vlbvrhotrlipaoedudys
   ```

2. **Navigate to:** SQL Editor (left sidebar)

3. **Click:** "New Query"

4. **Copy and paste** the contents of:
   ```
   database/rls_policies.sql
   ```

5. **Click:** "Run"

6. **Verify:** You should see "Success. No rows returned"

7. **Run ingestion:**
   ```bash
   python scripts/ingest_synthetic_data.py
   ```

### Option 2: Copy SQL Directly

<details>
<summary>Click to expand full SQL</summary>

```sql
-- Enable RLS on all tables
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE ccc_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE component_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cross_module_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE trapped_cash_analysis ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Allow public insert on companies" ON companies;
DROP POLICY IF EXISTS "Allow public select on companies" ON companies;
DROP POLICY IF EXISTS "Allow public update on companies" ON companies;
DROP POLICY IF EXISTS "Allow public delete on companies" ON companies;

DROP POLICY IF EXISTS "Allow public insert on ccc_metrics" ON ccc_metrics;
DROP POLICY IF EXISTS "Allow public select on ccc_metrics" ON ccc_metrics;
DROP POLICY IF EXISTS "Allow public update on ccc_metrics" ON ccc_metrics;
DROP POLICY IF EXISTS "Allow public delete on ccc_metrics" ON ccc_metrics;

DROP POLICY IF EXISTS "Allow public insert on component_details" ON component_details;
DROP POLICY IF EXISTS "Allow public select on component_details" ON component_details;
DROP POLICY IF EXISTS "Allow public update on component_details" ON component_details;
DROP POLICY IF EXISTS "Allow public delete on component_details" ON component_details;

DROP POLICY IF EXISTS "Allow public insert on transactions" ON transactions;
DROP POLICY IF EXISTS "Allow public select on transactions" ON transactions;
DROP POLICY IF EXISTS "Allow public update on transactions" ON transactions;
DROP POLICY IF EXISTS "Allow public delete on transactions" ON transactions;

DROP POLICY IF EXISTS "Allow public insert on event_logs" ON event_logs;
DROP POLICY IF EXISTS "Allow public select on event_logs" ON event_logs;
DROP POLICY IF EXISTS "Allow public update on event_logs" ON event_logs;
DROP POLICY IF EXISTS "Allow public delete on event_logs" ON event_logs;

DROP POLICY IF EXISTS "Allow public insert on cross_module_links" ON cross_module_links;
DROP POLICY IF EXISTS "Allow public select on cross_module_links" ON cross_module_links;
DROP POLICY IF EXISTS "Allow public update on cross_module_links" ON cross_module_links;
DROP POLICY IF EXISTS "Allow public delete on cross_module_links" ON cross_module_links;

DROP POLICY IF EXISTS "Allow public insert on trapped_cash_analysis" ON trapped_cash_analysis;
DROP POLICY IF EXISTS "Allow public select on trapped_cash_analysis" ON trapped_cash_analysis;
DROP POLICY IF EXISTS "Allow public update on trapped_cash_analysis" ON trapped_cash_analysis;
DROP POLICY IF EXISTS "Allow public delete on trapped_cash_analysis" ON trapped_cash_analysis;

-- Create permissive policies for all tables
CREATE POLICY "Allow public insert on companies" ON companies FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on companies" ON companies FOR SELECT USING (true);
CREATE POLICY "Allow public update on companies" ON companies FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on companies" ON companies FOR DELETE USING (true);

CREATE POLICY "Allow public insert on ccc_metrics" ON ccc_metrics FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on ccc_metrics" ON ccc_metrics FOR SELECT USING (true);
CREATE POLICY "Allow public update on ccc_metrics" ON ccc_metrics FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on ccc_metrics" ON ccc_metrics FOR DELETE USING (true);

CREATE POLICY "Allow public insert on component_details" ON component_details FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on component_details" ON component_details FOR SELECT USING (true);
CREATE POLICY "Allow public update on component_details" ON component_details FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on component_details" ON component_details FOR DELETE USING (true);

CREATE POLICY "Allow public insert on transactions" ON transactions FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on transactions" ON transactions FOR SELECT USING (true);
CREATE POLICY "Allow public update on transactions" ON transactions FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on transactions" ON transactions FOR DELETE USING (true);

CREATE POLICY "Allow public insert on event_logs" ON event_logs FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on event_logs" ON event_logs FOR SELECT USING (true);
CREATE POLICY "Allow public update on event_logs" ON event_logs FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on event_logs" ON event_logs FOR DELETE USING (true);

CREATE POLICY "Allow public insert on cross_module_links" ON cross_module_links FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on cross_module_links" ON cross_module_links FOR SELECT USING (true);
CREATE POLICY "Allow public update on cross_module_links" ON cross_module_links FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on cross_module_links" ON cross_module_links FOR DELETE USING (true);

CREATE POLICY "Allow public insert on trapped_cash_analysis" ON trapped_cash_analysis FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on trapped_cash_analysis" ON trapped_cash_analysis FOR SELECT USING (true);
CREATE POLICY "Allow public update on trapped_cash_analysis" ON trapped_cash_analysis FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on trapped_cash_analysis" ON trapped_cash_analysis FOR DELETE USING (true);
```

</details>

## What This Does

The SQL above:
- ✅ Enables Row Level Security on all tables
- ✅ Creates policies allowing public INSERT, SELECT, UPDATE, DELETE
- ✅ Allows the anon API key to ingest data
- ✅ Safe for testing/development (tighten in production)

## After Setup

Once RLS policies are applied, run:

```bash
python scripts/ingest_synthetic_data.py
```

**Expected output:**
```
✅ Companies inserted: 1
✅ Transactions inserted: 5,100
✅ Event logs inserted: 13,714
✅ CCC Metrics inserted: 1
✅ Component Details inserted: 4
```

## Files Created

- `database/rls_policies.sql` - RLS policy definitions
- `scripts/setup_rls_policies.py` - Helper script with instructions
- `data/synthetic/` - All generated CSV files (18,820 records)

## Why This Is Needed

Supabase enables Row Level Security by default to protect data. Without policies, the public `anon` API key has no permissions. These policies grant full access for testing purposes.

**⚠️ Security Note:** These policies allow public access. For production, implement proper authentication and restrictive policies.
