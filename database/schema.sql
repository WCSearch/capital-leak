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
