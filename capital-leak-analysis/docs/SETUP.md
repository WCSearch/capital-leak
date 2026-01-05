# Capital Leak Analysis - Setup Guide

This guide will help you set up the Capital Leak Analysis Platform on your system.

## Prerequisites

### Required Software
- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)
- git

### System Requirements
- 4GB RAM minimum
- 10GB disk space for database
- Operating System: Linux, macOS, or Windows

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd capital-leak-analysis
```

### 2. Create Virtual Environment

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install PostgreSQL

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**On macOS (using Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**On Windows:**
Download and install from: https://www.postgresql.org/download/windows/

### 5. Create Database User

```bash
# Access PostgreSQL
sudo -u postgres psql

# Create user and grant permissions
CREATE USER capital_leak_user WITH PASSWORD 'your_secure_password';
ALTER USER capital_leak_user CREATEDB;
\q
```

### 6. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

Update the following in `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=capital_leak_db
DB_USER=capital_leak_user
DB_PASSWORD=your_secure_password
```

### 7. Setup Database

```bash
python scripts/setup_database.py
```

This will:
- Create the database
- Create all tables and views
- Create analysis functions
- Optionally insert sample data

### 8. Verify Installation

```bash
# Test database connection
python -c "from config.database import get_db_connection; conn = get_db_connection(); print('✓ Database connection successful'); conn.close()"

# Run a test analysis (requires data)
python app/main.py
```

## Data Loading

### Option 1: Load from CSV Files

```python
from app.main import CapitalLeakAnalyzer
from config.field_mappings import ERPSystem

analyzer = CapitalLeakAnalyzer()

# Load invoices
analyzer.load_data_from_csv(
    entity_type='invoice',
    file_path='data/invoices.csv',
    erp_system=ERPSystem.CUSTOM
)

# Load inventory
analyzer.load_data_from_csv(
    entity_type='inventory',
    file_path='data/inventory.csv',
    erp_system=ERPSystem.CUSTOM
)

# Load payables
analyzer.load_data_from_csv(
    entity_type='payable',
    file_path='data/payables.csv',
    erp_system=ERPSystem.CUSTOM
)

# Load revenue data
analyzer.load_data_from_csv(
    entity_type='revenue',
    file_path='data/revenue.csv',
    erp_system=ERPSystem.CUSTOM
)
```

### Option 2: Custom ETL Script

```python
from etl import CSVExtractor, DataTransformer, DataLoader
from config.field_mappings import ERPSystem

# Extract
extractor = CSVExtractor()
raw_data = extractor.extract('data/your_file.csv')

# Transform
transformer = DataTransformer(ERPSystem.SAP)
transformed = transformer.transform_invoices(raw_data)

# Load
loader = DataLoader()
loader.load_invoices(transformed)
```

### Option 3: Database Connection

For direct database connections, update `.env`:
```
ERP_DB_HOST=erp-server.company.com
ERP_DB_PORT=5432
ERP_DB_NAME=erp_database
ERP_DB_USER=read_only_user
ERP_DB_PASSWORD=password
```

Then use DatabaseExtractor:
```python
from etl import DatabaseExtractor

extractor = DatabaseExtractor({
    'host': 'erp-server.company.com',
    'port': 5432,
    'database': 'erp_database',
    'user': 'read_only_user',
    'password': 'password'
})

data = extractor.extract("SELECT * FROM invoices WHERE date > '2024-01-01'")
```

## ERP System Configuration

### Mapping ERP Fields

Edit `config/field_mappings.py` to add mappings for your specific ERP system.

Example for custom ERP:
```python
CUSTOM_MAPPINGS = {
    'invoice': EntityMapping(
        entity_name='invoice',
        field_mappings={
            'inv_num': 'invoice_id',
            'inv_date': 'invoice_date',
            'cust_id': 'customer_id',
            'total_amt': 'amount'
        },
        required_fields=['inv_num', 'inv_date', 'cust_id', 'total_amt']
    )
}
```

### Supported ERP Systems

Pre-configured mappings exist for:
- SAP
- Oracle ERP Cloud
- Microsoft Dynamics 365
- NetSuite

## Running Analysis

### Basic Analysis

```bash
python app/main.py
```

### Custom Analysis

```python
from app.main import CapitalLeakAnalyzer

analyzer = CapitalLeakAnalyzer()

# Analyze specific period
metrics = analyzer.analyze_period(
    start_date='2024-01-01',
    end_date='2024-12-31'
)

print(metrics)

# Get trends
trends = analyzer.get_trends(months=12, interval='monthly')
for metric in trends:
    print(f"{metric.period_start}: CCC = {metric.ccc:.1f} days")
```

## Troubleshooting

### Database Connection Issues

**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solutions:**
1. Verify PostgreSQL is running:
   ```bash
   sudo systemctl status postgresql  # Linux
   brew services list  # macOS
   ```

2. Check `.env` credentials
3. Verify PostgreSQL is accepting connections:
   ```bash
   psql -h localhost -U capital_leak_user -d capital_leak_db
   ```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'config'`

**Solution:**
Ensure you're running from the project root directory:
```bash
cd capital-leak-analysis
python app/main.py
```

### Data Loading Errors

**Problem:** `Missing required fields`

**Solution:**
1. Verify CSV column names match field mappings
2. Check `config/field_mappings.py` for your ERP system
3. Add custom mappings if needed

### No Data in Analysis

**Problem:** Analysis returns zero values

**Solution:**
1. Verify data was loaded:
   ```sql
   SELECT COUNT(*) FROM invoices;
   SELECT COUNT(*) FROM inventory_movements;
   SELECT COUNT(*) FROM payables;
   SELECT COUNT(*) FROM revenue;
   ```

2. Check date ranges match your data
3. Verify revenue/COGS data exists for the period

## Performance Tuning

### For Large Datasets

1. **Use batch loading:**
   ```python
   loader.load_batch('invoice', large_dataset, batch_size=5000)
   ```

2. **Add database indexes:**
   ```sql
   CREATE INDEX idx_custom ON invoices(your_field);
   ```

3. **Increase connection pool:**
   Edit `config/database.py`:
   ```python
   engine = create_engine(
       connection_string,
       pool_size=20,
       max_overflow=40
   )
   ```

## Next Steps

1. **Customize Field Mappings:** Adjust mappings for your ERP system
2. **Load Your Data:** Import production or test data
3. **Run Analysis:** Generate capital leak reports
4. **Schedule Regular Analysis:** Set up cron jobs or scheduled tasks
5. **Integrate with BI Tools:** Export results to Tableau, Power BI, etc.

## Getting Help

- Check the main README.md for common use cases
- Review code documentation in each module
- See data/sample/README.md for sample data formats
- Open an issue on GitHub

## Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use read-only database users** for ERP connections
3. **Encrypt database backups**
4. **Restrict network access** to PostgreSQL port
5. **Regularly update dependencies:**
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

## Backup and Recovery

### Backup Database

```bash
pg_dump -U capital_leak_user -d capital_leak_db > backup.sql
```

### Restore Database

```bash
psql -U capital_leak_user -d capital_leak_db < backup.sql
```

### Export Analysis Results

```python
# Export to CSV
import pandas as pd
from config.database import execute_query

results = execute_query("SELECT * FROM analysis_results")
df = pd.DataFrame(results)
df.to_csv('analysis_export.csv', index=False)
```
