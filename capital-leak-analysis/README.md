# Capital Leak Analysis Platform

Find hidden capital leaks in mid-market companies through ERP event log analysis.

## What This Does
Analyzes ERP data to identify capital trapped in working capital:
- **DSO** (Days Sales Outstanding): Cash trapped in receivables
- **DIO** (Days Inventory Outstanding): Cash trapped in inventory
- **DPO** (Days Payable Outstanding): Cash management in payables

**CCC = DSO + DIO - DPO** (Cash Conversion Cycle)

## Quick Start
```bash
# 1. Clone and setup
git clone <repository-url>
cd capital-leak-analysis
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 3. Setup database
python scripts/setup_database.py

# 4. Run analysis
python app/main.py
```

## Architecture

### Data Flow
```
ERP System → Extractor → Transformer → Loader → PostgreSQL
                                                      ↓
                                              Analysis Engine
                                                      ↓
                                              Capital Leak Report
```

### Key Metrics Calculated
1. **Days Sales Outstanding (DSO)**
   - Formula: (Accounts Receivable / Revenue) × Days
   - Indicates how long it takes to collect payment after a sale

2. **Days Inventory Outstanding (DIO)**
   - Formula: (Inventory / COGS) × Days
   - Shows how long inventory sits before being sold

3. **Days Payable Outstanding (DPO)**
   - Formula: (Accounts Payable / COGS) × Days
   - Measures how long the company takes to pay suppliers

4. **Cash Conversion Cycle (CCC)**
   - Formula: DSO + DIO - DPO
   - Lower is better - indicates faster cash conversion

## Project Structure
```
capital-leak-analysis/
├── config/              # Configuration files
│   ├── database.py      # Database connection settings
│   └── field_mappings.py # ERP field mappings
├── database/            # Database schemas
│   └── schema.sql       # PostgreSQL schema
├── etl/                 # ETL pipeline
│   ├── extractor.py     # Extract from ERP
│   ├── transformer.py   # Transform data
│   └── loader.py        # Load to database
├── app/                 # Main application
│   └── main.py          # Analysis engine
└── scripts/             # Utility scripts
    └── setup_database.py
```

## Requirements
- Python 3.8+
- PostgreSQL 12+
- ERP data export (CSV, JSON, or database access)

## Configuration

### Database Setup
Configure PostgreSQL connection in `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=capital_leak_db
DB_USER=your_user
DB_PASSWORD=your_password
```

### ERP Field Mappings
Edit `config/field_mappings.py` to map your ERP fields to the standard schema.

## Usage

### Basic Analysis
```python
from app.main import CapitalLeakAnalyzer

analyzer = CapitalLeakAnalyzer()
results = analyzer.analyze_period(start_date='2024-01-01', end_date='2024-12-31')
print(results.summary())
```

### Custom Analysis
```python
# Analyze specific categories
results = analyzer.analyze_by_category(
    category='product_line',
    period_days=90
)

# Trend analysis
trends = analyzer.calculate_trends(
    metrics=['DSO', 'DIO', 'DPO'],
    interval='monthly'
)
```

## Data Requirements

### Minimum Required Data
1. **Sales/Invoices**: Date, Amount, Customer, Payment Status
2. **Inventory**: Date, SKU, Quantity, Value, Movement Type
3. **Purchases/Payables**: Date, Amount, Vendor, Payment Date
4. **Revenue/COGS**: Period, Revenue, Cost of Goods Sold

### Supported ERP Systems
- SAP
- Oracle ERP Cloud
- Microsoft Dynamics 365
- NetSuite
- Custom CSV/JSON exports

## Output Reports

The analysis generates:
1. **Executive Summary**: High-level CCC metrics
2. **Detailed Breakdown**: DSO, DIO, DPO by period
3. **Trend Analysis**: Historical trends and forecasts
4. **Recommendations**: Actionable insights to reduce capital leaks

## Example Results
```
Capital Leak Analysis Report
=============================
Period: Q4 2024

Cash Conversion Cycle: 67 days
  Days Sales Outstanding (DSO): 45 days
  Days Inventory Outstanding (DIO): 38 days
  Days Payable Outstanding (DPO): 16 days

Capital Trapped: $2.3M
  In Receivables: $1.5M (65%)
  In Inventory: $0.8M (35%)

Recommendations:
  1. Accelerate collections (target: 35 days DSO)
  2. Optimize inventory turnover (target: 30 days DIO)
  Potential Cash Release: $1.1M
```

## Development

### Running Tests
```bash
pytest tests/
```

### Adding New ERP Connectors
1. Create a new extractor in `etl/extractors/`
2. Implement the `BaseExtractor` interface
3. Add field mappings in `config/field_mappings.py`

## Troubleshooting

### Common Issues
1. **Database Connection Failed**: Check `.env` credentials
2. **Missing Data**: Verify ERP export includes required fields
3. **Incorrect Calculations**: Review field mappings configuration

## Contributing
See `docs/CONTRIBUTING.md` for development guidelines.

## License
MIT License - See LICENSE file for details

## Support
For issues and questions:
- GitHub Issues: <repository-url>/issues
- Documentation: `docs/`
