-- Diagnostic: Check if permissions were actually granted
-- Run this in Supabase SQL Editor to see what's configured

-- 1. Check table privileges for anon role
SELECT
    'Table Privileges for anon role:' as info;

SELECT
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'anon'
    AND table_schema = 'public'
ORDER BY table_name, privilege_type;

-- 2. Check RLS status on tables
SELECT '' as spacer;
SELECT 'RLS Status on Tables:' as info;

SELECT
    tablename,
    CASE WHEN rowsecurity THEN '❌ ENABLED (blocking API)' ELSE '✅ DISABLED (good)' END as rls_status
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 3. Check if anon role exists and has proper grants
SELECT '' as spacer;
SELECT 'Checking anon role configuration:' as info;

SELECT
    rolname,
    rolsuper,
    rolinherit,
    rolcreaterole,
    rolcreatedb,
    rolcanlogin
FROM pg_roles
WHERE rolname = 'anon';

-- 4. Check schema privileges
SELECT '' as spacer;
SELECT 'Schema Privileges for anon:' as info;

SELECT
    nspname as schema_name,
    has_schema_privilege('anon', nspname, 'USAGE') as has_usage,
    has_schema_privilege('anon', nspname, 'CREATE') as has_create
FROM pg_namespace
WHERE nspname = 'public';
