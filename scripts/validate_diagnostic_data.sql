-- ============================================================================
-- DIAGNOSTIC PDF DATA VALIDATION QUERIES
-- ============================================================================
-- This SQL script contains all queries needed to validate synthetic data
-- against the diagnostic PDFs for three companies:
-- - TechMfg Industries (Expected CCC: 628.8)
-- - AmeriParts Distribution (Expected CCC: 124.8)
-- - PrecisionTech Manufacturing (Expected CCC: 2114.7)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. CCC METRICS VALIDATION
-- ----------------------------------------------------------------------------
-- Verify CCC values match expected values from PDFs
-- Expected: TechMfg=628.8, AmeriParts=124.8, PrecisionTech=2114.7

SELECT
    c.company_name,
    m.dso_value,
    m.dio_value,
    m.dpo_value,
    m.ccc_value,
    -- Verify formula: CCC = DSO + DIO - DPO
    (m.dso_value + m.dio_value - m.dpo_value) as calculated_ccc,
    -- Check if matches expected
    CASE c.company_name
        WHEN 'TechMfg Industries' THEN
            CASE WHEN ABS(m.ccc_value - 628.8) < 0.1 THEN '✓ PASS' ELSE '✗ FAIL' END
        WHEN 'AmeriParts Distribution' THEN
            CASE WHEN ABS(m.ccc_value - 124.8) < 0.1 THEN '✓ PASS' ELSE '✗ FAIL' END
        WHEN 'PrecisionTech Manufacturing' THEN
            CASE WHEN ABS(m.ccc_value - 2114.7) < 0.1 THEN '✓ PASS' ELSE '✗ FAIL' END
    END as validation_result
FROM ccc_metrics m
JOIN companies c ON m.company_id = c.company_id
WHERE c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
ORDER BY c.company_name;


-- ----------------------------------------------------------------------------
-- 2. TRANSACTION COUNTS BY STATUS - TechMfg Industries
-- ----------------------------------------------------------------------------
-- Verify transaction distribution and volumes

SELECT
    c.company_name,
    t.component_type,
    t.status,
    COUNT(*) as count,
    SUM(t.outstanding_amount) as total_outstanding,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as avg_amount,
    MIN(t.transaction_date) as earliest_date,
    MAX(t.transaction_date) as latest_date
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE c.company_name = 'TechMfg Industries'
GROUP BY c.company_name, t.component_type, t.status
ORDER BY total_outstanding DESC;


-- ----------------------------------------------------------------------------
-- 2b. TRANSACTION COUNTS BY STATUS - AmeriParts Distribution
-- ----------------------------------------------------------------------------

SELECT
    c.company_name,
    t.component_type,
    t.status,
    COUNT(*) as count,
    SUM(t.outstanding_amount) as total_outstanding,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as avg_amount
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE c.company_name = 'AmeriParts Distribution'
GROUP BY c.company_name, t.component_type, t.status
ORDER BY total_outstanding DESC;


-- ----------------------------------------------------------------------------
-- 2c. TRANSACTION COUNTS BY STATUS - PrecisionTech Manufacturing
-- ----------------------------------------------------------------------------

SELECT
    c.company_name,
    t.component_type,
    t.status,
    COUNT(*) as count,
    SUM(t.outstanding_amount) as total_outstanding,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as avg_amount
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE c.company_name = 'PrecisionTech Manufacturing'
GROUP BY c.company_name, t.component_type, t.status
ORDER BY total_outstanding DESC;


-- ----------------------------------------------------------------------------
-- 3. EXAMPLE TRANSACTION VERIFICATION - TechMfg
-- ----------------------------------------------------------------------------
-- Check if specific example transaction from PDF exists

SELECT
    t.*,
    c.company_name,
    -- Check for event logs
    (SELECT COUNT(*) FROM event_logs WHERE transaction_id = t.transaction_id) as event_log_count
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE t.transaction_number = 'INV-2024-000543'
AND c.company_name = 'TechMfg Industries';


-- ----------------------------------------------------------------------------
-- 3b. EXAMPLE TRANSACTION VERIFICATION - AmeriParts
-- ----------------------------------------------------------------------------

SELECT
    t.*,
    c.company_name,
    (SELECT COUNT(*) FROM event_logs WHERE transaction_id = t.transaction_id) as event_log_count
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE t.transaction_number = 'PART-515688'
AND c.company_name = 'AmeriParts Distribution';


-- ----------------------------------------------------------------------------
-- 3c. EXAMPLE TRANSACTION VERIFICATION - PrecisionTech
-- ----------------------------------------------------------------------------

SELECT
    t.*,
    c.company_name,
    (SELECT COUNT(*) FROM event_logs WHERE transaction_id = t.transaction_id) as event_log_count
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE t.transaction_number = 'ITEM-364255'
AND c.company_name = 'PrecisionTech Manufacturing';


-- ----------------------------------------------------------------------------
-- 4. EVENT LOGS VERIFICATION - TechMfg Example
-- ----------------------------------------------------------------------------
-- Verify event logs exist for the example transaction

SELECT
    c.company_name,
    t.transaction_number,
    el.event_type,
    el.event_timestamp,
    el.event_description,
    el.event_data,
    el.user_id,
    el.module_name
FROM event_logs el
JOIN transactions t ON el.transaction_id = t.transaction_id
JOIN companies c ON t.company_id = c.company_id
WHERE t.transaction_number = 'INV-2024-000543'
AND c.company_name = 'TechMfg Industries'
ORDER BY el.event_timestamp;


-- ----------------------------------------------------------------------------
-- 4b. EVENT LOGS VERIFICATION - AmeriParts Example
-- ----------------------------------------------------------------------------

SELECT
    c.company_name,
    t.transaction_number,
    el.event_type,
    el.event_timestamp,
    el.event_description,
    el.event_data
FROM event_logs el
JOIN transactions t ON el.transaction_id = t.transaction_id
JOIN companies c ON t.company_id = c.company_id
WHERE t.transaction_number = 'PART-515688'
AND c.company_name = 'AmeriParts Distribution'
ORDER BY el.event_timestamp;


-- ----------------------------------------------------------------------------
-- 4c. EVENT LOGS VERIFICATION - PrecisionTech Example
-- ----------------------------------------------------------------------------

SELECT
    c.company_name,
    t.transaction_number,
    el.event_type,
    el.event_timestamp,
    el.event_description,
    el.event_data
FROM event_logs el
JOIN transactions t ON el.transaction_id = t.transaction_id
JOIN companies c ON t.company_id = c.company_id
WHERE t.transaction_number = 'ITEM-364255'
AND c.company_name = 'PrecisionTech Manufacturing'
ORDER BY el.event_timestamp;


-- ----------------------------------------------------------------------------
-- 5. DATA QUALITY CHECKS
-- ----------------------------------------------------------------------------
-- Check for NULL values and data completeness

SELECT
    c.company_name,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN t.transaction_number IS NULL THEN 1 ELSE 0 END) as null_transaction_numbers,
    SUM(CASE WHEN t.transaction_date IS NULL THEN 1 ELSE 0 END) as null_dates,
    SUM(CASE WHEN t.amount IS NULL THEN 1 ELSE 0 END) as null_amounts,
    SUM(CASE WHEN t.outstanding_amount IS NULL THEN 1 ELSE 0 END) as null_outstanding,
    SUM(CASE WHEN t.status IS NULL THEN 1 ELSE 0 END) as null_statuses,
    SUM(CASE WHEN t.component_type IS NULL THEN 1 ELSE 0 END) as null_component_types,
    SUM(CASE WHEN t.gl_account IS NULL THEN 1 ELSE 0 END) as null_gl_accounts,
    -- Overall data quality score
    CASE
        WHEN SUM(CASE WHEN t.transaction_number IS NULL
                    OR t.transaction_date IS NULL
                    OR t.amount IS NULL
                    OR t.status IS NULL THEN 1 ELSE 0 END) = 0
        THEN '✓ PASS'
        ELSE '⚠ WARNING'
    END as quality_result
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
GROUP BY c.company_name
ORDER BY c.company_name;


-- ----------------------------------------------------------------------------
-- 6. GL ACCOUNT DISTRIBUTION (DIO) - All Companies
-- ----------------------------------------------------------------------------
-- Verify GL accounts follow 60/40 split for inventory

WITH dio_distribution AS (
    SELECT
        c.company_name,
        t.gl_account,
        COUNT(*) as transaction_count,
        SUM(t.amount) as total_amount,
        -- Calculate percentage of transactions
        ROUND(
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY c.company_name),
            1
        ) as percent_of_transactions
    FROM transactions t
    JOIN companies c ON t.company_id = c.company_id
    WHERE t.component_type = 'DIO'
    AND c.company_name IN (
        'TechMfg Industries',
        'AmeriParts Distribution',
        'PrecisionTech Manufacturing'
    )
    GROUP BY c.company_name, t.gl_account
)
SELECT
    company_name,
    gl_account,
    transaction_count,
    total_amount,
    percent_of_transactions,
    -- Check if approximately 60/40 split
    CASE
        WHEN percent_of_transactions BETWEEN 55 AND 65 THEN '✓ Primary (60%)'
        WHEN percent_of_transactions BETWEEN 35 AND 45 THEN '✓ Secondary (40%)'
        ELSE '⚠ Unexpected %'
    END as distribution_check
FROM dio_distribution
ORDER BY company_name, total_amount DESC;


-- ----------------------------------------------------------------------------
-- 7. COMPONENT DETAILS VERIFICATION
-- ----------------------------------------------------------------------------
-- Verify component_details table has breakdown data

SELECT
    c.company_name,
    cd.component_type,
    cd.functional_area,
    cd.amount,
    cd.percentage_of_total,
    cd.days_value,
    cd.status_breakdown
FROM component_details cd
JOIN companies c ON cd.company_id = c.company_id
WHERE c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
ORDER BY c.company_name, cd.component_type, cd.amount DESC;


-- ----------------------------------------------------------------------------
-- 8. OVERALL DATA VOLUME CHECK
-- ----------------------------------------------------------------------------
-- Summary of data volume across all tables

SELECT
    c.company_name,
    COUNT(DISTINCT t.transaction_id) as transaction_count,
    COUNT(DISTINCT el.event_log_id) as event_log_count,
    COUNT(DISTINCT cd.component_id) as component_detail_count,
    COUNT(DISTINCT cml.link_id) as cross_module_link_count,
    SUM(t.amount) as total_transaction_amount,
    MIN(t.transaction_date) as earliest_transaction,
    MAX(t.transaction_date) as latest_transaction
FROM companies c
LEFT JOIN transactions t ON c.company_id = t.company_id
LEFT JOIN event_logs el ON t.transaction_id = el.transaction_id
LEFT JOIN component_details cd ON c.company_id = cd.company_id
LEFT JOIN cross_module_links cml ON c.company_id = cml.company_id
WHERE c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
GROUP BY c.company_name
ORDER BY c.company_name;


-- ----------------------------------------------------------------------------
-- 9. STATUS DISTRIBUTION ANALYSIS
-- ----------------------------------------------------------------------------
-- Analyze transaction status distribution

SELECT
    c.company_name,
    t.component_type,
    t.status,
    COUNT(*) as count,
    SUM(t.outstanding_amount) as total_outstanding,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (
            PARTITION BY c.company_name, t.component_type
        ),
        1
    ) as percent_of_component
FROM transactions t
JOIN companies c ON t.company_id = c.company_id
WHERE c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
GROUP BY c.company_name, t.component_type, t.status
ORDER BY c.company_name, t.component_type, total_outstanding DESC;


-- ----------------------------------------------------------------------------
-- 10. CROSS-MODULE LINKS CHECK
-- ----------------------------------------------------------------------------
-- Verify cross-module link data exists and is realistic

SELECT
    c.company_name,
    cml.source_module,
    cml.target_module,
    cml.link_type,
    COUNT(*) as link_count,
    COUNT(DISTINCT cml.source_transaction_id) as unique_sources,
    COUNT(DISTINCT cml.target_transaction_id) as unique_targets
FROM cross_module_links cml
JOIN companies c ON cml.company_id = c.company_id
WHERE c.company_name IN (
    'TechMfg Industries',
    'AmeriParts Distribution',
    'PrecisionTech Manufacturing'
)
GROUP BY c.company_name, cml.source_module, cml.target_module, cml.link_type
ORDER BY c.company_name, link_count DESC;


-- ----------------------------------------------------------------------------
-- VALIDATION SUMMARY
-- ----------------------------------------------------------------------------
-- Quick summary of all critical checks

WITH validation_summary AS (
    SELECT
        c.company_name,
        m.ccc_value,
        CASE c.company_name
            WHEN 'TechMfg Industries' THEN ABS(m.ccc_value - 628.8) < 0.1
            WHEN 'AmeriParts Distribution' THEN ABS(m.ccc_value - 124.8) < 0.1
            WHEN 'PrecisionTech Manufacturing' THEN ABS(m.ccc_value - 2114.7) < 0.1
        END as ccc_matches,
        (SELECT COUNT(*) FROM transactions WHERE company_id = c.company_id) as txn_count,
        (SELECT COUNT(*) FROM event_logs el
         JOIN transactions t ON el.transaction_id = t.transaction_id
         WHERE t.company_id = c.company_id) as event_count,
        (SELECT COUNT(*) FROM component_details WHERE company_id = c.company_id) as component_count
    FROM companies c
    JOIN ccc_metrics m ON c.company_id = m.company_id
    WHERE c.company_name IN (
        'TechMfg Industries',
        'AmeriParts Distribution',
        'PrecisionTech Manufacturing'
    )
)
SELECT
    company_name,
    ccc_value,
    CASE WHEN ccc_matches THEN '✓ PASS' ELSE '✗ FAIL' END as ccc_validation,
    txn_count,
    CASE WHEN txn_count > 0 THEN '✓ PASS' ELSE '✗ FAIL' END as txn_validation,
    event_count,
    CASE WHEN event_count > 0 THEN '✓ PASS' ELSE '✗ FAIL' END as event_validation,
    component_count,
    CASE WHEN component_count > 0 THEN '✓ PASS' ELSE '✗ FAIL' END as component_validation,
    CASE
        WHEN ccc_matches AND txn_count > 0 AND event_count > 0 AND component_count > 0
        THEN '✓✓✓ ALL PASS'
        ELSE '✗✗✗ ISSUES FOUND'
    END as overall_status
FROM validation_summary
ORDER BY company_name;


-- ============================================================================
-- END OF VALIDATION QUERIES
-- ============================================================================
--
-- INSTRUCTIONS:
-- 1. Run these queries in order against your Supabase database
-- 2. Compare results with expected values in VALIDATION_GUIDE.md
-- 3. Record any discrepancies or issues found
-- 4. Use validation results to verify diagnostic PDF accuracy
-- ============================================================================
