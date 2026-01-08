-- Grant Permissions to Anon Role for Data Ingestion
-- This allows the public API key to insert/update/delete data

-- Grant ALL permissions on ALL tables to anon role
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO anon;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO anon;

-- Specifically grant on each table (belt and suspenders approach)
GRANT ALL ON companies TO anon;
GRANT ALL ON ccc_metrics TO anon;
GRANT ALL ON component_details TO anon;
GRANT ALL ON transactions TO anon;
GRANT ALL ON event_logs TO anon;
GRANT ALL ON cross_module_links TO anon;
GRANT ALL ON trapped_cash_analysis TO anon;
GRANT ALL ON inventory_movements TO anon;
GRANT ALL ON purchase_orders TO anon;

-- Also ensure RLS is disabled (in case it wasn't done earlier)
ALTER TABLE IF EXISTS companies DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ccc_metrics DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS component_details DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS event_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cross_module_links DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS trapped_cash_analysis DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS inventory_movements DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS purchase_orders DISABLE ROW LEVEL SECURITY;

SELECT 'Permissions granted to anon role + RLS disabled!' as status;
