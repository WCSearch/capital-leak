-- Verification Query: Check RLS Status and Policies
-- Run this in Supabase SQL Editor to verify the policies were created

-- 1. Check if tables exist
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN ('companies', 'transactions', 'event_logs', 'ccc_metrics', 'component_details')
ORDER BY tablename;

-- 2. Check RLS status on tables
SELECT
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN ('companies', 'transactions', 'event_logs', 'ccc_metrics', 'component_details')
ORDER BY tablename;

-- 3. Check existing policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
    AND tablename IN ('companies', 'transactions', 'event_logs', 'ccc_metrics', 'component_details')
ORDER BY tablename, policyname;

-- 4. Count policies per table
SELECT
    tablename,
    COUNT(*) as policy_count
FROM pg_policies
WHERE schemaname = 'public'
    AND tablename IN ('companies', 'transactions', 'event_logs', 'ccc_metrics', 'component_details')
GROUP BY tablename
ORDER BY tablename;
