CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE companies (
    company_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
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
