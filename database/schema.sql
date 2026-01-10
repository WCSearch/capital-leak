CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE companies (
    company_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    company_type VARCHAR(20) CHECK (company_type IN ('DISTRIBUTION', 'MANUFACTURING')) DEFAULT 'DISTRIBUTION',
    industry VARCHAR(255),
    erp_system VARCHAR(100) NOT NULL,
    analysis_date DATE NOT NULL,
    revenue_annual DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ccc_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    ccc_value DECIMAL(10,2) NOT NULL,
    dso_value DECIMAL(10,2) NOT NULL,
    dio_value DECIMAL(10,2) NOT NULL,
    dpo_value DECIMAL(10,2) NOT NULL,
    calculation_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE component_details (
    detail_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    component_type VARCHAR(10) CHECK (component_type IN ('DSO', 'DIO', 'DPO')),
    functional_area VARCHAR(100),
    gl_account VARCHAR(50),
    gl_account_name VARCHAR(255),
    amount DECIMAL(15,2),
    days_contribution DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    component_type VARCHAR(10),
    transaction_number VARCHAR(100),
    transaction_date DATE,
    due_date DATE,
    amount DECIMAL(15,2),
    outstanding_amount DECIMAL(15,2),
    days_outstanding INTEGER,
    gl_account VARCHAR(50),
    customer_vendor VARCHAR(255),
    status VARCHAR(50),
    erp_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trans_company ON transactions(company_id);
CREATE INDEX idx_trans_date ON transactions(transaction_date);

CREATE TABLE event_logs (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id),
    transaction_id UUID REFERENCES transactions(transaction_id),
    event_type VARCHAR(100),
    event_timestamp TIMESTAMP,
    user_id VARCHAR(100),
    event_description TEXT,
    module VARCHAR(100),
    event_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cross_module_links (
    link_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id),
    source_component VARCHAR(10),
    target_component VARCHAR(10),
    link_type VARCHAR(100),
    impact_amount DECIMAL(15,2),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trapped_cash_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,

    -- Totals
    total_trapped_cash DECIMAL(15,2),
    total_expected_recovery DECIMAL(15,2),

    -- DSO
    dso_trapped_cash DECIMAL(15,2),
    dso_excess_days DECIMAL(10,2),
    dso_expected_recovery DECIMAL(15,2),
    dso_priority VARCHAR(10),
    dso_priority_score DECIMAL(15,2),

    -- DIO
    dio_trapped_cash DECIMAL(15,2),
    dio_excess_days DECIMAL(10,2),
    dio_expected_recovery DECIMAL(15,2),
    dio_priority VARCHAR(10),
    dio_priority_score DECIMAL(15,2),

    -- DPO
    dpo_trapped_cash DECIMAL(15,2),
    dpo_deficit_days DECIMAL(10,2),
    dpo_expected_recovery DECIMAL(15,2),
    dpo_priority VARCHAR(10),
    dpo_priority_score DECIMAL(15,2),

    -- Benchmarks used
    benchmark_dso DECIMAL(10,2),
    benchmark_dio DECIMAL(10,2),
    benchmark_dpo DECIMAL(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trapped_cash_company ON trapped_cash_analysis(company_id);
CREATE INDEX idx_trapped_cash_date ON trapped_cash_analysis(analysis_date);

-- ============================================================================
-- MANUFACTURING-SPECIFIC TABLES (for BOM analysis and component tracking)
-- ============================================================================

-- BOM (Bill of Materials) structure for manufactured products
CREATE TABLE bom_structure (
    bom_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    parent_item VARCHAR(100) NOT NULL,
    parent_item_description VARCHAR(255),
    assembly_time_days INTEGER DEFAULT 0,
    expected_cycle_time INTEGER, -- calculated from critical path
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- BOM components (child items in the BOM)
CREATE TABLE bom_components (
    component_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bom_id UUID REFERENCES bom_structure(bom_id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    component_item VARCHAR(100) NOT NULL,
    component_description VARCHAR(255),
    quantity_required DECIMAL(10,4) NOT NULL,
    unit_cost DECIMAL(15,2),
    lead_time_days INTEGER NOT NULL,
    is_critical_path BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Work orders for manufacturing
CREATE TABLE work_orders (
    work_order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    work_order_number VARCHAR(100) NOT NULL,
    product_item VARCHAR(100) NOT NULL,
    bom_id UUID REFERENCES bom_structure(bom_id),
    release_date DATE NOT NULL,
    planned_completion_date DATE,
    actual_completion_date DATE,
    quantity_ordered DECIMAL(10,4),
    quantity_completed DECIMAL(10,4) DEFAULT 0,
    status VARCHAR(50), -- RELEASED, IN_PROGRESS, COMPLETED, ON_HOLD
    total_cost DECIMAL(15,2),
    days_outstanding INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Component availability snapshots (track component inventory at WO release)
CREATE TABLE component_availability_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    work_order_id UUID REFERENCES work_orders(work_order_id) ON DELETE CASCADE,
    component_item VARCHAR(100) NOT NULL,
    snapshot_date DATE NOT NULL,
    required_quantity DECIMAL(10,4),
    available_quantity DECIMAL(10,4),
    shortage_quantity DECIMAL(10,4),
    lead_time_days INTEGER,
    is_bottleneck BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Component shortages (historical record of supply issues)
CREATE TABLE component_shortages (
    shortage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    component_item VARCHAR(100) NOT NULL,
    shortage_start_date DATE NOT NULL,
    shortage_end_date DATE, -- NULL if ongoing
    normal_lead_time_days INTEGER,
    extended_lead_time_days INTEGER,
    work_orders_affected INTEGER DEFAULT 0,
    total_value_trapped DECIMAL(15,2),
    reason VARCHAR(500),
    status VARCHAR(50), -- ACTIVE, RESOLVED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory snapshots (for point-in-time availability checks)
CREATE TABLE inventory_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    item_number VARCHAR(100) NOT NULL,
    snapshot_date DATE NOT NULL,
    on_hand_quantity DECIMAL(10,4),
    reserved_quantity DECIMAL(10,4),
    available_quantity DECIMAL(10,4),
    unit_cost DECIMAL(15,2),
    total_value DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Subcontract items (items sent to outside processors)
CREATE TABLE subcontract_items (
    subcontract_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    po_number VARCHAR(100),
    item_number VARCHAR(100) NOT NULL,
    supplier_name VARCHAR(255),
    sent_date DATE,
    expected_return_date DATE,
    actual_return_date DATE,
    quantity DECIMAL(10,4),
    total_value DECIMAL(15,2),
    days_at_supplier INTEGER,
    status VARCHAR(50), -- AT_SUPPLIER, RETURNED, OVERDUE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quality holds / quarantine items
CREATE TABLE quarantine_items (
    quarantine_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(company_id) ON DELETE CASCADE,
    item_number VARCHAR(100) NOT NULL,
    lot_number VARCHAR(100),
    quarantine_date DATE,
    inspection_type VARCHAR(100), -- ROUTINE, COMPLEX, MRB_REQUIRED
    quantity DECIMAL(10,4),
    total_value DECIMAL(15,2),
    days_in_quarantine INTEGER,
    expected_pass_rate DECIMAL(5,4), -- 0.70 = 70%
    disposition VARCHAR(50), -- PENDING, PASSED, FAILED, REWORK
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bom_company ON bom_structure(company_id);
CREATE INDEX idx_bom_parent ON bom_structure(parent_item);
CREATE INDEX idx_bom_components_bom ON bom_components(bom_id);
CREATE INDEX idx_work_orders_company ON work_orders(company_id);
CREATE INDEX idx_work_orders_product ON work_orders(product_item);
CREATE INDEX idx_component_snapshots_wo ON component_availability_snapshots(work_order_id);
CREATE INDEX idx_inventory_snapshots_item ON inventory_snapshots(item_number, snapshot_date);
CREATE INDEX idx_subcontract_company ON subcontract_items(company_id);
CREATE INDEX idx_quarantine_company ON quarantine_items(company_id);
