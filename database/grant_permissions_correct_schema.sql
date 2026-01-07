-- Grant Permissions to Anon Role - Correct Schema
-- Based on actual Supabase schema (no inventory_movements or purchase_orders)

-- Grant ALL permissions to anon role on all existing tables
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO anon;

-- Specific grants for each table in your schema
GRANT ALL ON analysis_progress TO anon;
GRANT ALL ON benchmarks TO anon;
GRANT ALL ON ccc_metrics TO anon;
GRANT ALL ON companies TO anon;
GRANT ALL ON component_details TO anon;
GRANT ALL ON cross_module_links TO anon;
GRANT ALL ON dso_recovery_confidence_summary TO anon;
GRANT ALL ON dso_root_cause_summary TO anon;
GRANT ALL ON dso_time_state_summary TO anon;
GRANT ALL ON entity_analysis TO anon;
GRANT ALL ON event_logs TO anon;
GRANT ALL ON functional_area_analysis TO anon;
GRANT ALL ON root_cause_findings TO anon;
GRANT ALL ON transactions TO anon;
GRANT ALL ON trapped_cash_analysis TO anon;

-- Disable RLS on all tables
ALTER TABLE IF EXISTS analysis_progress DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS benchmarks DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ccc_metrics DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS companies DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS component_details DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cross_module_links DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS dso_recovery_confidence_summary DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS dso_root_cause_summary DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS dso_time_state_summary DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS entity_analysis DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS event_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS functional_area_analysis DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS root_cause_findings DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS trapped_cash_analysis DISABLE ROW LEVEL SECURITY;

SELECT 'Permissions granted to anon role + RLS disabled on all tables!' as status;
