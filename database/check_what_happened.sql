-- Diagnostic Query: Check what's blocking the API
-- Run this in Supabase SQL Editor to see what's happening

-- 1. Check if tables exist
SELECT 'Tables that exist:' as info;
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 2. Check RLS status
SELECT '' as spacer;
SELECT 'RLS Status:' as info;
SELECT
    tablename,
    CASE WHEN rowsecurity THEN 'ENABLED' ELSE 'DISABLED' END as rls_status
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 3. Try a test insert (will show actual error)
SELECT '' as spacer;
SELECT 'Testing INSERT (you should see this fail if RLS is still blocking):' as info;

-- This will fail with the actual error message
INSERT INTO companies (company_name, erp_system, analysis_date, revenue_annual)
VALUES ('Test Company', 'SAP', '2025-01-07', 1000000)
RETURNING company_id, company_name;

-- If the above worked, clean up:
-- DELETE FROM companies WHERE company_name = 'Test Company';
