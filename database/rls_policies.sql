-- RLS Policies for Synthetic Data Ingestion
-- These policies allow public inserts for testing and data ingestion

-- Enable RLS on all tables (if not already enabled)
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE ccc_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE component_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cross_module_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE trapped_cash_analysis ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to allow re-running this script)
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

-- Create policies for companies table
CREATE POLICY "Allow public insert on companies" ON companies FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on companies" ON companies FOR SELECT USING (true);
CREATE POLICY "Allow public update on companies" ON companies FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on companies" ON companies FOR DELETE USING (true);

-- Create policies for ccc_metrics table
CREATE POLICY "Allow public insert on ccc_metrics" ON ccc_metrics FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on ccc_metrics" ON ccc_metrics FOR SELECT USING (true);
CREATE POLICY "Allow public update on ccc_metrics" ON ccc_metrics FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on ccc_metrics" ON ccc_metrics FOR DELETE USING (true);

-- Create policies for component_details table
CREATE POLICY "Allow public insert on component_details" ON component_details FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on component_details" ON component_details FOR SELECT USING (true);
CREATE POLICY "Allow public update on component_details" ON component_details FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on component_details" ON component_details FOR DELETE USING (true);

-- Create policies for transactions table
CREATE POLICY "Allow public insert on transactions" ON transactions FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on transactions" ON transactions FOR SELECT USING (true);
CREATE POLICY "Allow public update on transactions" ON transactions FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on transactions" ON transactions FOR DELETE USING (true);

-- Create policies for event_logs table
CREATE POLICY "Allow public insert on event_logs" ON event_logs FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on event_logs" ON event_logs FOR SELECT USING (true);
CREATE POLICY "Allow public update on event_logs" ON event_logs FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on event_logs" ON event_logs FOR DELETE USING (true);

-- Create policies for cross_module_links table
CREATE POLICY "Allow public insert on cross_module_links" ON cross_module_links FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on cross_module_links" ON cross_module_links FOR SELECT USING (true);
CREATE POLICY "Allow public update on cross_module_links" ON cross_module_links FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on cross_module_links" ON cross_module_links FOR DELETE USING (true);

-- Create policies for trapped_cash_analysis table
CREATE POLICY "Allow public insert on trapped_cash_analysis" ON trapped_cash_analysis FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public select on trapped_cash_analysis" ON trapped_cash_analysis FOR SELECT USING (true);
CREATE POLICY "Allow public update on trapped_cash_analysis" ON trapped_cash_analysis FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on trapped_cash_analysis" ON trapped_cash_analysis FOR DELETE USING (true);
