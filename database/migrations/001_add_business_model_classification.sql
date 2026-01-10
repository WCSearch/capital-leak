-- Migration: Add Business Model Classification Support
-- Date: 2026-01-10
-- Description: Adds tables and columns to support Distribution vs Manufacturing business model classification

-- ============================================================================
-- 1. COMPANY CLASSIFICATION TABLE
-- ============================================================================

CREATE TABLE company_classification (
    classification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    business_model VARCHAR(20) NOT NULL CHECK (business_model IN ('DISTRIBUTION', 'MANUFACTURING', 'HYBRID', 'UNKNOWN')),
    classification_confidence DECIMAL(3,2) CHECK (classification_confidence BETWEEN 0 AND 1),
    classification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    classification_method VARCHAR(50) CHECK (classification_method IN ('AUTOMATIC', 'MANUAL_OVERRIDE')),

    -- Classification evidence scores
    distribution_score INT DEFAULT 0,
    manufacturing_score INT DEFAULT 0,

    -- Supporting evidence flags - Distribution signals
    has_cross_dock BOOLEAN DEFAULT FALSE,
    has_warehouse_transfers BOOLEAN DEFAULT FALSE,
    cross_dock_transaction_count INT DEFAULT 0,
    warehouse_transfer_volume INT DEFAULT 0,

    -- Supporting evidence flags - Manufacturing signals
    has_work_orders BOOLEAN DEFAULT FALSE,
    has_wip_accounts BOOLEAN DEFAULT FALSE,
    has_routing_operations BOOLEAN DEFAULT FALSE,
    has_manufacturing_variances BOOLEAN DEFAULT FALSE,
    production_order_volume INT DEFAULT 0,

    -- GL account pattern evidence
    purchased_cogs_pct DECIMAL(5,2),  -- % of COGS from purchased goods
    manufactured_cogs_pct DECIMAL(5,2),  -- % of COGS from labor/overhead

    -- Notes and override reason
    notes TEXT,
    override_reason TEXT,  -- Required when classification_method = 'MANUAL_OVERRIDE'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(company_id)  -- One classification per company
);

CREATE INDEX idx_company_classification_model ON company_classification(business_model);
CREATE INDEX idx_company_classification_confidence ON company_classification(classification_confidence);

-- ============================================================================
-- 2. MODIFY EXISTING TABLES - Add Business Model Columns
-- ============================================================================

-- Add business_model and calculation_method to component_details
ALTER TABLE component_details ADD COLUMN IF NOT EXISTS business_model VARCHAR(20);
ALTER TABLE component_details ADD COLUMN IF NOT EXISTS calculation_method VARCHAR(50);

-- Add business_model to trapped_cash_analysis
ALTER TABLE trapped_cash_analysis ADD COLUMN IF NOT EXISTS business_model VARCHAR(20);
ALTER TABLE trapped_cash_analysis ADD COLUMN IF NOT EXISTS calculation_method VARCHAR(50);

-- Add business_model to transactions (for filtering)
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS business_model VARCHAR(20);

-- ============================================================================
-- 3. DISTRIBUTION DIO ANALYSIS TABLE
-- ============================================================================

CREATE TABLE dio_distribution_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Velocity/Turns Analysis
    velocity_issues_count INT DEFAULT 0,
    velocity_inventory_value DECIMAL(15,2) DEFAULT 0,
    velocity_normal_turns DECIMAL(5,2) DEFAULT 0,
    velocity_actual_turns DECIMAL(5,2) DEFAULT 0,
    velocity_lost_turns DECIMAL(5,2) DEFAULT 0,
    velocity_cash_impact DECIMAL(15,2) DEFAULT 0,

    -- Stockout Analysis
    stockout_events_count INT DEFAULT 0,
    stockout_lost_revenue DECIMAL(15,2) DEFAULT 0,
    stockout_lost_margin DECIMAL(15,2) DEFAULT 0,
    stockout_items_affected INT DEFAULT 0,

    -- Excess/Obsolete Inventory
    excess_inventory_value DECIMAL(15,2) DEFAULT 0,
    dead_stock_value DECIMAL(15,2) DEFAULT 0,
    slow_mover_value DECIMAL(15,2) DEFAULT 0,
    excess_carrying_cost DECIMAL(15,2) DEFAULT 0,

    -- Movement Bottlenecks - Cross-Dock
    cross_dock_delays_count INT DEFAULT 0,
    cross_dock_inventory_value DECIMAL(15,2) DEFAULT 0,
    cross_dock_excess_days DECIMAL(8,2) DEFAULT 0,
    cross_dock_lost_turns DECIMAL(5,2) DEFAULT 0,
    cross_dock_cash_impact DECIMAL(15,2) DEFAULT 0,

    -- Movement Bottlenecks - Warehouse Transfers
    warehouse_transfer_delays_count INT DEFAULT 0,
    wt_inventory_value DECIMAL(15,2) DEFAULT 0,
    wt_excess_days DECIMAL(8,2) DEFAULT 0,
    wt_cash_impact DECIMAL(15,2) DEFAULT 0,

    -- Movement Bottlenecks - Putaway
    putaway_delays_count INT DEFAULT 0,
    putaway_inventory_value DECIMAL(15,2) DEFAULT 0,
    putaway_excess_days DECIMAL(8,2) DEFAULT 0,
    putaway_cash_impact DECIMAL(15,2) DEFAULT 0,

    -- Total Impact
    total_cash_impact DECIMAL(15,2) DEFAULT 0,
    total_annual_opportunity DECIMAL(15,2) DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dio_dist_company ON dio_distribution_analysis(company_id);
CREATE INDEX idx_dio_dist_date ON dio_distribution_analysis(analysis_date);

-- ============================================================================
-- 4. MANUFACTURING DIO ANALYSIS TABLE
-- ============================================================================

CREATE TABLE dio_manufacturing_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- WIP Queue/Bottleneck Analysis
    bottleneck_operations_count INT DEFAULT 0,
    bottleneck_wip_value DECIMAL(15,2) DEFAULT 0,
    bottleneck_avg_queue_days DECIMAL(8,2) DEFAULT 0,
    bottleneck_carrying_cost DECIMAL(15,2) DEFAULT 0,
    bottleneck_throughput_impact DECIMAL(15,2) DEFAULT 0,

    -- Production Delay Analysis
    delayed_work_orders_count INT DEFAULT 0,
    delayed_wip_value DECIMAL(15,2) DEFAULT 0,
    delayed_avg_excess_days DECIMAL(8,2) DEFAULT 0,
    delayed_carrying_cost DECIMAL(15,2) DEFAULT 0,
    delayed_revenue_impact DECIMAL(15,2) DEFAULT 0,

    -- Yield/Scrap Analysis
    scrap_events_count INT DEFAULT 0,
    scrap_material_cost DECIMAL(15,2) DEFAULT 0,
    scrap_labor_cost DECIMAL(15,2) DEFAULT 0,
    scrap_overhead_cost DECIMAL(15,2) DEFAULT 0,
    scrap_total_impact DECIMAL(15,2) DEFAULT 0,

    -- Rework Analysis
    rework_events_count INT DEFAULT 0,
    rework_labor_cost DECIMAL(15,2) DEFAULT 0,
    rework_material_cost DECIMAL(15,2) DEFAULT 0,
    rework_total_impact DECIMAL(15,2) DEFAULT 0,

    -- QA Delay Analysis
    qa_hold_events_count INT DEFAULT 0,
    qa_hold_wip_value DECIMAL(15,2) DEFAULT 0,
    qa_hold_avg_days DECIMAL(8,2) DEFAULT 0,
    qa_hold_carrying_cost DECIMAL(15,2) DEFAULT 0,
    qa_hold_throughput_impact DECIMAL(15,2) DEFAULT 0,

    -- Variance Analysis
    material_variance DECIMAL(15,2) DEFAULT 0,
    labor_variance DECIMAL(15,2) DEFAULT 0,
    overhead_variance DECIMAL(15,2) DEFAULT 0,
    total_variance_cost DECIMAL(15,2) DEFAULT 0,

    -- Total Impact
    total_cash_impact DECIMAL(15,2) DEFAULT 0,
    total_annual_impact DECIMAL(15,2) DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dio_mfg_company ON dio_manufacturing_analysis(company_id);
CREATE INDEX idx_dio_mfg_date ON dio_manufacturing_analysis(analysis_date);

-- ============================================================================
-- 5. DISTRIBUTION DIO DETAIL TABLES
-- ============================================================================

-- Distribution - Velocity Issues Detail
CREATE TABLE dio_distribution_velocity_detail (
    detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES dio_distribution_analysis(analysis_id) ON DELETE CASCADE,
    item_id VARCHAR(50),
    item_description VARCHAR(200),

    avg_monthly_demand DECIMAL(12,2),
    avg_inventory_on_hand DECIMAL(12,2),
    inventory_value DECIMAL(15,2),

    expected_turn_days INT,
    actual_turn_days INT,
    excess_days INT,

    normal_annual_turns DECIMAL(5,2),
    actual_annual_turns DECIMAL(5,2),
    lost_turns DECIMAL(5,2),

    gross_margin_pct DECIMAL(5,4),
    cash_impact_annual DECIMAL(15,2),

    root_cause VARCHAR(200),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dio_dist_velocity_analysis ON dio_distribution_velocity_detail(analysis_id);

-- Distribution - Stockout Detail
CREATE TABLE dio_distribution_stockout_detail (
    detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES dio_distribution_analysis(analysis_id) ON DELETE CASCADE,
    item_id VARCHAR(50),
    warehouse_id VARCHAR(50),

    stockout_start_date TIMESTAMP,
    stockout_end_date TIMESTAMP,
    days_stockout INT,

    avg_daily_demand DECIMAL(12,2),
    unit_price DECIMAL(12,2),
    gross_margin_pct DECIMAL(5,4),

    lost_units DECIMAL(12,2),
    lost_revenue DECIMAL(15,2),
    lost_margin DECIMAL(15,2),

    -- Root cause diagnosis
    reorder_point DECIMAL(12,2),
    safety_stock DECIMAL(12,2),
    lead_time_days INT,
    parameter_issue VARCHAR(200),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dio_dist_stockout_analysis ON dio_distribution_stockout_detail(analysis_id);

-- Distribution - Movement Bottleneck Detail
CREATE TABLE dio_distribution_movement_detail (
    detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES dio_distribution_analysis(analysis_id) ON DELETE CASCADE,

    bottleneck_type VARCHAR(50) CHECK (bottleneck_type IN ('CROSS_DOCK', 'WAREHOUSE_TRANSFER', 'PUTAWAY', 'RECEIVING')),

    transaction_id VARCHAR(50),
    item_id VARCHAR(50),
    warehouse_location VARCHAR(50),

    timestamp_entered TIMESTAMP,
    timestamp_exited TIMESTAMP,
    expected_hours DECIMAL(8,2),
    actual_hours DECIMAL(8,2),
    excess_days DECIMAL(8,2),

    quantity DECIMAL(12,2),
    unit_cost DECIMAL(12,2),
    inventory_value DECIMAL(15,2),

    normal_turn_days INT,
    normal_annual_turns DECIMAL(5,2),
    actual_annual_turns DECIMAL(5,2),
    lost_turns DECIMAL(5,2),

    gross_margin_pct DECIMAL(5,4),
    cash_impact DECIMAL(15,2),

    root_cause VARCHAR(200),
    system_event VARCHAR(200),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dio_dist_movement_analysis ON dio_distribution_movement_detail(analysis_id);
CREATE INDEX idx_dio_dist_movement_type ON dio_distribution_movement_detail(bottleneck_type);

-- ============================================================================
-- 6. MANUFACTURING DIO DETAIL TABLES
-- ============================================================================

-- Manufacturing - Bottleneck Detail
CREATE TABLE dio_manufacturing_bottleneck_detail (
    detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES dio_manufacturing_analysis(analysis_id) ON DELETE CASCADE,

    work_order_id VARCHAR(50),
    operation_seq INT,
    department_id VARCHAR(50),
    resource_code VARCHAR(50),

    scheduled_start_date TIMESTAMP,
    actual_start_date TIMESTAMP,
    days_delayed INT,

    quantity_in_queue DECIMAL(12,2),
    quantity_running DECIMAL(12,2),
    unit_wip_cost DECIMAL(12,2),
    wip_value_in_queue DECIMAL(15,2),

    standard_hours_per_unit DECIMAL(8,4),
    actual_hours_per_unit DECIMAL(8,4),
    hours_variance_per_unit DECIMAL(8,4),

    carrying_cost DECIMAL(15,2),
    throughput_impact DECIMAL(15,2),
    total_cash_impact DECIMAL(15,2),

    bottleneck_severity VARCHAR(20) CHECK (bottleneck_severity IN ('CRITICAL', 'MODERATE', 'MINOR')),
    root_cause VARCHAR(200),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dio_mfg_bottleneck_analysis ON dio_manufacturing_bottleneck_detail(analysis_id);
CREATE INDEX idx_dio_mfg_bottleneck_severity ON dio_manufacturing_bottleneck_detail(bottleneck_severity);

-- Manufacturing - Scrap/Rework Detail
CREATE TABLE dio_manufacturing_yield_detail (
    detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES dio_manufacturing_analysis(analysis_id) ON DELETE CASCADE,

    event_type VARCHAR(20) CHECK (event_type IN ('SCRAP', 'REWORK')),
    work_order_id VARCHAR(50),
    operation_seq INT,
    transaction_date TIMESTAMP,

    item_id VARCHAR(50),
    quantity_affected DECIMAL(12,2),

    material_cost DECIMAL(15,2),
    labor_cost DECIMAL(15,2),
    overhead_cost DECIMAL(15,2),
    total_cost DECIMAL(15,2),

    reason_code VARCHAR(50),
    reason_description VARCHAR(200),

    preventable BOOLEAN DEFAULT FALSE,
    estimated_prevention_cost DECIMAL(15,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dio_mfg_yield_analysis ON dio_manufacturing_yield_detail(analysis_id);
CREATE INDEX idx_dio_mfg_yield_type ON dio_manufacturing_yield_detail(event_type);

-- Manufacturing - QA Hold Detail
CREATE TABLE dio_manufacturing_qa_detail (
    detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID REFERENCES dio_manufacturing_analysis(analysis_id) ON DELETE CASCADE,

    work_order_id VARCHAR(50),
    operation_seq INT,
    qa_hold_start_date TIMESTAMP,
    qa_hold_release_date TIMESTAMP,
    days_on_hold INT,

    quantity_on_hold DECIMAL(12,2),
    unit_wip_cost DECIMAL(12,2),
    wip_value DECIMAL(15,2),

    hold_reason VARCHAR(200),

    carrying_cost DECIMAL(15,2),
    throughput_impact DECIMAL(15,2),
    total_cash_impact DECIMAL(15,2),

    preventable BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dio_mfg_qa_analysis ON dio_manufacturing_qa_detail(analysis_id);

-- ============================================================================
-- 7. HELPER VIEWS
-- ============================================================================

-- View: Company with Classification
CREATE OR REPLACE VIEW companies_with_classification AS
SELECT
    c.*,
    cc.business_model,
    cc.classification_confidence,
    cc.classification_method,
    cc.classification_date
FROM companies c
LEFT JOIN company_classification cc ON c.company_id = cc.company_id;

-- View: DIO Analysis Summary (Combined Distribution + Manufacturing)
CREATE OR REPLACE VIEW dio_analysis_summary AS
SELECT
    c.company_id,
    c.company_name,
    cc.business_model,
    COALESCE(dd.total_cash_impact, 0) as distribution_cash_impact,
    COALESCE(dm.total_cash_impact, 0) as manufacturing_cash_impact,
    COALESCE(dd.total_cash_impact, 0) + COALESCE(dm.total_cash_impact, 0) as total_cash_impact,
    COALESCE(dd.analysis_date, dm.analysis_date) as latest_analysis_date
FROM companies c
LEFT JOIN company_classification cc ON c.company_id = cc.company_id
LEFT JOIN LATERAL (
    SELECT * FROM dio_distribution_analysis
    WHERE company_id = c.company_id
    ORDER BY analysis_date DESC
    LIMIT 1
) dd ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM dio_manufacturing_analysis
    WHERE company_id = c.company_id
    ORDER BY analysis_date DESC
    LIMIT 1
) dm ON TRUE;

-- ============================================================================
-- 8. COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE company_classification IS 'Stores business model classification (Distribution/Manufacturing/Hybrid) with confidence scores and evidence';
COMMENT ON TABLE dio_distribution_analysis IS 'Distribution-specific DIO analysis focusing on inventory velocity, turns, and movement bottlenecks';
COMMENT ON TABLE dio_manufacturing_analysis IS 'Manufacturing-specific DIO analysis focusing on WIP bottlenecks, yield, and throughput';
COMMENT ON COLUMN company_classification.classification_confidence IS 'Confidence score 0.0-1.0, where >0.70 is automatic, <0.70 requires manual review';
COMMENT ON COLUMN company_classification.purchased_cogs_pct IS 'Percentage of COGS from purchased goods (high % = distribution signal)';
COMMENT ON COLUMN company_classification.manufactured_cogs_pct IS 'Percentage of COGS from labor/overhead (high % = manufacturing signal)';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
