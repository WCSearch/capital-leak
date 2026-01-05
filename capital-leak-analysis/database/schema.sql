-- Capital Leak Analysis Database Schema
-- PostgreSQL 12+

-- Drop existing tables if they exist
DROP TABLE IF EXISTS analysis_results CASCADE;
DROP TABLE IF EXISTS revenue CASCADE;
DROP TABLE IF EXISTS payables CASCADE;
DROP TABLE IF EXISTS inventory_movements CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS vendors CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- Customers table
CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    customer_type VARCHAR(50),
    credit_limit DECIMAL(15, 2),
    payment_terms_days INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customers_name ON customers(customer_name);

-- Vendors table
CREATE TABLE vendors (
    vendor_id VARCHAR(50) PRIMARY KEY,
    vendor_name VARCHAR(255) NOT NULL,
    vendor_type VARCHAR(50),
    payment_terms_days INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vendors_name ON vendors(vendor_name);

-- Products table
CREATE TABLE products (
    sku VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    unit_cost DECIMAL(15, 2),
    unit_price DECIMAL(15, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_name ON products(product_name);

-- Invoices table (Accounts Receivable)
CREATE TABLE invoices (
    invoice_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    payment_date DATE,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) NOT NULL,
    days_to_payment INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_payment_date ON invoices(payment_date);

-- Inventory movements table
CREATE TABLE inventory_movements (
    movement_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) REFERENCES products(sku),
    movement_date DATE NOT NULL,
    movement_type VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(15, 2),
    total_value DECIMAL(15, 2),
    location VARCHAR(100),
    reference_doc VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_sku ON inventory_movements(sku);
CREATE INDEX idx_inventory_date ON inventory_movements(movement_date);
CREATE INDEX idx_inventory_type ON inventory_movements(movement_type);

-- Payables table (Accounts Payable)
CREATE TABLE payables (
    payable_id VARCHAR(50) PRIMARY KEY,
    vendor_id VARCHAR(50) REFERENCES vendors(vendor_id),
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    payment_date DATE,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) NOT NULL,
    days_to_payment INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payables_vendor ON payables(vendor_id);
CREATE INDEX idx_payables_date ON payables(invoice_date);
CREATE INDEX idx_payables_status ON payables(status);
CREATE INDEX idx_payables_payment_date ON payables(payment_date);

-- Revenue and COGS table
CREATE TABLE revenue (
    period_id SERIAL PRIMARY KEY,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    revenue DECIMAL(15, 2) NOT NULL,
    cogs DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_start, period_end)
);

CREATE INDEX idx_revenue_period ON revenue(period_start, period_end);

-- Analysis results table
CREATE TABLE analysis_results (
    analysis_id SERIAL PRIMARY KEY,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    dso DECIMAL(10, 2),
    dio DECIMAL(10, 2),
    dpo DECIMAL(10, 2),
    ccc DECIMAL(10, 2),
    avg_receivables DECIMAL(15, 2),
    avg_inventory DECIMAL(15, 2),
    avg_payables DECIMAL(15, 2),
    revenue DECIMAL(15, 2),
    cogs DECIMAL(15, 2),
    capital_trapped_receivables DECIMAL(15, 2),
    capital_trapped_inventory DECIMAL(15, 2),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analysis_period ON analysis_results(period_start, period_end);
CREATE INDEX idx_analysis_date ON analysis_results(analysis_date);

-- Views for common queries

-- Current inventory snapshot
CREATE OR REPLACE VIEW v_current_inventory AS
SELECT
    p.sku,
    p.product_name,
    p.category,
    COALESCE(SUM(CASE WHEN im.movement_type IN ('RECEIPT', 'PURCHASE') THEN im.quantity
                      WHEN im.movement_type IN ('SALE', 'ADJUSTMENT_OUT') THEN -im.quantity
                      ELSE 0 END), 0) as current_quantity,
    p.unit_cost,
    COALESCE(SUM(CASE WHEN im.movement_type IN ('RECEIPT', 'PURCHASE') THEN im.quantity
                      WHEN im.movement_type IN ('SALE', 'ADJUSTMENT_OUT') THEN -im.quantity
                      ELSE 0 END), 0) * p.unit_cost as total_value
FROM products p
LEFT JOIN inventory_movements im ON p.sku = im.sku
GROUP BY p.sku, p.product_name, p.category, p.unit_cost;

-- Outstanding invoices
CREATE OR REPLACE VIEW v_outstanding_invoices AS
SELECT
    i.*,
    c.customer_name,
    c.payment_terms_days,
    CURRENT_DATE - i.invoice_date as days_outstanding
FROM invoices i
JOIN customers c ON i.customer_id = c.customer_id
WHERE i.status IN ('OPEN', 'OVERDUE')
  AND i.payment_date IS NULL;

-- Outstanding payables
CREATE OR REPLACE VIEW v_outstanding_payables AS
SELECT
    p.*,
    v.vendor_name,
    v.payment_terms_days,
    CURRENT_DATE - p.invoice_date as days_outstanding
FROM payables p
JOIN vendors v ON p.vendor_id = v.vendor_id
WHERE p.status IN ('OPEN', 'APPROVED')
  AND p.payment_date IS NULL;

-- Functions

-- Calculate DSO (Days Sales Outstanding)
CREATE OR REPLACE FUNCTION calculate_dso(
    p_start_date DATE,
    p_end_date DATE
) RETURNS DECIMAL AS $$
DECLARE
    v_avg_receivables DECIMAL;
    v_revenue DECIMAL;
    v_days INTEGER;
BEGIN
    v_days := p_end_date - p_start_date;

    -- Average receivables during period
    SELECT AVG(amount) INTO v_avg_receivables
    FROM invoices
    WHERE invoice_date BETWEEN p_start_date AND p_end_date
      AND status IN ('OPEN', 'OVERDUE', 'PAID');

    -- Total revenue during period
    SELECT SUM(revenue) INTO v_revenue
    FROM revenue
    WHERE period_start >= p_start_date
      AND period_end <= p_end_date;

    IF v_revenue IS NULL OR v_revenue = 0 THEN
        RETURN NULL;
    END IF;

    RETURN (v_avg_receivables / v_revenue) * v_days;
END;
$$ LANGUAGE plpgsql;

-- Calculate DIO (Days Inventory Outstanding)
CREATE OR REPLACE FUNCTION calculate_dio(
    p_start_date DATE,
    p_end_date DATE
) RETURNS DECIMAL AS $$
DECLARE
    v_avg_inventory DECIMAL;
    v_cogs DECIMAL;
    v_days INTEGER;
BEGIN
    v_days := p_end_date - p_start_date;

    -- Average inventory value during period
    SELECT AVG(total_value) INTO v_avg_inventory
    FROM (
        SELECT SUM(total_value) as total_value
        FROM inventory_movements
        WHERE movement_date BETWEEN p_start_date AND p_end_date
        GROUP BY movement_date
    ) inv;

    -- Total COGS during period
    SELECT SUM(cogs) INTO v_cogs
    FROM revenue
    WHERE period_start >= p_start_date
      AND period_end <= p_end_date;

    IF v_cogs IS NULL OR v_cogs = 0 THEN
        RETURN NULL;
    END IF;

    RETURN (v_avg_inventory / v_cogs) * v_days;
END;
$$ LANGUAGE plpgsql;

-- Calculate DPO (Days Payable Outstanding)
CREATE OR REPLACE FUNCTION calculate_dpo(
    p_start_date DATE,
    p_end_date DATE
) RETURNS DECIMAL AS $$
DECLARE
    v_avg_payables DECIMAL;
    v_cogs DECIMAL;
    v_days INTEGER;
BEGIN
    v_days := p_end_date - p_start_date;

    -- Average payables during period
    SELECT AVG(amount) INTO v_avg_payables
    FROM payables
    WHERE invoice_date BETWEEN p_start_date AND p_end_date
      AND status IN ('OPEN', 'APPROVED', 'PAID');

    -- Total COGS during period
    SELECT SUM(cogs) INTO v_cogs
    FROM revenue
    WHERE period_start >= p_start_date
      AND period_end <= p_end_date;

    IF v_cogs IS NULL OR v_cogs = 0 THEN
        RETURN NULL;
    END IF;

    RETURN (v_avg_payables / v_cogs) * v_days;
END;
$$ LANGUAGE plpgsql;

-- Insert sample data (optional - for testing)
-- Uncomment to populate with sample data

-- INSERT INTO customers VALUES
-- ('C001', 'Acme Corporation', 'Enterprise', 100000.00, 30),
-- ('C002', 'TechStart Inc', 'SMB', 50000.00, 45),
-- ('C003', 'Global Industries', 'Enterprise', 200000.00, 60);

-- INSERT INTO vendors VALUES
-- ('V001', 'Supplier One', 'Raw Materials', 30),
-- ('V002', 'Supplier Two', 'Components', 45);

-- INSERT INTO products VALUES
-- ('SKU001', 'Product A', 'Electronics', 'Gadgets', 50.00, 100.00),
-- ('SKU002', 'Product B', 'Electronics', 'Accessories', 20.00, 40.00);

COMMENT ON TABLE invoices IS 'Accounts receivable - customer invoices';
COMMENT ON TABLE payables IS 'Accounts payable - vendor bills';
COMMENT ON TABLE inventory_movements IS 'All inventory transactions';
COMMENT ON TABLE revenue IS 'Period revenue and COGS data';
COMMENT ON TABLE analysis_results IS 'Stored capital leak analysis results';
