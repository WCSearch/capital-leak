"""
Capital Leak Analysis - Main Application
Analyzes working capital metrics and identifies capital leaks
"""
import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import execute_query, get_db_connection
from etl import CSVExtractor, DataTransformer, DataLoader
from config.field_mappings import ERPSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CapitalLeakMetrics:
    """Container for capital leak analysis metrics"""
    period_start: date
    period_end: date
    dso: float  # Days Sales Outstanding
    dio: float  # Days Inventory Outstanding
    dpo: float  # Days Payable Outstanding
    ccc: float  # Cash Conversion Cycle
    avg_receivables: float
    avg_inventory: float
    avg_payables: float
    revenue: float
    cogs: float
    capital_trapped_receivables: float
    capital_trapped_inventory: float

    def __str__(self):
        return f"""
Capital Leak Analysis Report
{'=' * 50}
Period: {self.period_start} to {self.period_end}

Cash Conversion Cycle: {self.ccc:.1f} days
  Days Sales Outstanding (DSO): {self.dso:.1f} days
  Days Inventory Outstanding (DIO): {self.dio:.1f} days
  Days Payable Outstanding (DPO): {self.dpo:.1f} days

Financial Metrics:
  Average Receivables: ${self.avg_receivables:,.2f}
  Average Inventory: ${self.avg_inventory:,.2f}
  Average Payables: ${self.avg_payables:,.2f}
  Revenue: ${self.revenue:,.2f}
  COGS: ${self.cogs:,.2f}

Capital Trapped:
  In Receivables: ${self.capital_trapped_receivables:,.2f}
  In Inventory: ${self.capital_trapped_inventory:,.2f}
  Total: ${self.capital_trapped_receivables + self.capital_trapped_inventory:,.2f}
{'=' * 50}
        """


class CapitalLeakAnalyzer:
    """Main analyzer for capital leaks"""

    def __init__(self):
        """Initialize the analyzer"""
        self.data_loader = DataLoader()
        logger.info("Capital Leak Analyzer initialized")

    def analyze_period(self, start_date: str, end_date: str) -> CapitalLeakMetrics:
        """
        Analyze capital leaks for a given period

        Args:
            start_date: Period start date (YYYY-MM-DD)
            end_date: Period end date (YYYY-MM-DD)

        Returns:
            CapitalLeakMetrics object
        """
        logger.info(f"Analyzing period: {start_date} to {end_date}")

        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        days = (end - start).days

        # Calculate metrics
        dso = self._calculate_dso(start, end, days)
        dio = self._calculate_dio(start, end, days)
        dpo = self._calculate_dpo(start, end, days)
        ccc = dso + dio - dpo

        # Get financial data
        avg_receivables = self._get_avg_receivables(start, end)
        avg_inventory = self._get_avg_inventory(start, end)
        avg_payables = self._get_avg_payables(start, end)
        revenue, cogs = self._get_revenue_cogs(start, end)

        # Calculate trapped capital
        if revenue > 0:
            daily_revenue = revenue / days
            capital_trapped_receivables = dso * daily_revenue
        else:
            capital_trapped_receivables = 0

        if cogs > 0:
            daily_cogs = cogs / days
            capital_trapped_inventory = dio * daily_cogs
        else:
            capital_trapped_inventory = 0

        metrics = CapitalLeakMetrics(
            period_start=start,
            period_end=end,
            dso=dso,
            dio=dio,
            dpo=dpo,
            ccc=ccc,
            avg_receivables=avg_receivables,
            avg_inventory=avg_inventory,
            avg_payables=avg_payables,
            revenue=revenue,
            cogs=cogs,
            capital_trapped_receivables=capital_trapped_receivables,
            capital_trapped_inventory=capital_trapped_inventory
        )

        # Save results to database
        self._save_analysis_results(metrics)

        return metrics

    def _calculate_dso(self, start_date: date, end_date: date, days: int) -> float:
        """Calculate Days Sales Outstanding"""
        query = """
            SELECT AVG(amount) as avg_receivables
            FROM invoices
            WHERE invoice_date BETWEEN %s AND %s
              AND status IN ('OPEN', 'OVERDUE', 'PAID')
        """
        result = execute_query(query, (start_date, end_date))
        avg_receivables = result[0]['avg_receivables'] if result and result[0]['avg_receivables'] else 0

        # Get revenue
        revenue, _ = self._get_revenue_cogs(start_date, end_date)

        if revenue > 0:
            dso = (avg_receivables / revenue) * days
        else:
            dso = 0

        logger.info(f"DSO: {dso:.2f} days")
        return dso

    def _calculate_dio(self, start_date: date, end_date: date, days: int) -> float:
        """Calculate Days Inventory Outstanding"""
        query = """
            SELECT AVG(daily_value) as avg_inventory
            FROM (
                SELECT
                    movement_date,
                    SUM(total_value) as daily_value
                FROM inventory_movements
                WHERE movement_date BETWEEN %s AND %s
                GROUP BY movement_date
            ) daily_inv
        """
        result = execute_query(query, (start_date, end_date))
        avg_inventory = result[0]['avg_inventory'] if result and result[0]['avg_inventory'] else 0

        # Get COGS
        _, cogs = self._get_revenue_cogs(start_date, end_date)

        if cogs > 0:
            dio = (avg_inventory / cogs) * days
        else:
            dio = 0

        logger.info(f"DIO: {dio:.2f} days")
        return dio

    def _calculate_dpo(self, start_date: date, end_date: date, days: int) -> float:
        """Calculate Days Payable Outstanding"""
        query = """
            SELECT AVG(amount) as avg_payables
            FROM payables
            WHERE invoice_date BETWEEN %s AND %s
              AND status IN ('OPEN', 'APPROVED', 'PAID')
        """
        result = execute_query(query, (start_date, end_date))
        avg_payables = result[0]['avg_payables'] if result and result[0]['avg_payables'] else 0

        # Get COGS
        _, cogs = self._get_revenue_cogs(start_date, end_date)

        if cogs > 0:
            dpo = (avg_payables / cogs) * days
        else:
            dpo = 0

        logger.info(f"DPO: {dpo:.2f} days")
        return dpo

    def _get_avg_receivables(self, start_date: date, end_date: date) -> float:
        """Get average receivables for period"""
        query = """
            SELECT AVG(amount) as avg_receivables
            FROM invoices
            WHERE invoice_date BETWEEN %s AND %s
        """
        result = execute_query(query, (start_date, end_date))
        return result[0]['avg_receivables'] if result and result[0]['avg_receivables'] else 0

    def _get_avg_inventory(self, start_date: date, end_date: date) -> float:
        """Get average inventory value for period"""
        query = """
            SELECT AVG(daily_value) as avg_inventory
            FROM (
                SELECT
                    movement_date,
                    SUM(total_value) as daily_value
                FROM inventory_movements
                WHERE movement_date BETWEEN %s AND %s
                GROUP BY movement_date
            ) daily_inv
        """
        result = execute_query(query, (start_date, end_date))
        return result[0]['avg_inventory'] if result and result[0]['avg_inventory'] else 0

    def _get_avg_payables(self, start_date: date, end_date: date) -> float:
        """Get average payables for period"""
        query = """
            SELECT AVG(amount) as avg_payables
            FROM payables
            WHERE invoice_date BETWEEN %s AND %s
        """
        result = execute_query(query, (start_date, end_date))
        return result[0]['avg_payables'] if result and result[0]['avg_payables'] else 0

    def _get_revenue_cogs(self, start_date: date, end_date: date) -> Tuple[float, float]:
        """Get revenue and COGS for period"""
        query = """
            SELECT
                COALESCE(SUM(revenue), 0) as total_revenue,
                COALESCE(SUM(cogs), 0) as total_cogs
            FROM revenue
            WHERE period_start >= %s AND period_end <= %s
        """
        result = execute_query(query, (start_date, end_date))

        if result:
            return (
                float(result[0]['total_revenue'] or 0),
                float(result[0]['total_cogs'] or 0)
            )
        return 0.0, 0.0

    def _save_analysis_results(self, metrics: CapitalLeakMetrics):
        """Save analysis results to database"""
        query = """
            INSERT INTO analysis_results (
                period_start, period_end, dso, dio, dpo, ccc,
                avg_receivables, avg_inventory, avg_payables,
                revenue, cogs, capital_trapped_receivables, capital_trapped_inventory
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    metrics.period_start,
                    metrics.period_end,
                    metrics.dso,
                    metrics.dio,
                    metrics.dpo,
                    metrics.ccc,
                    metrics.avg_receivables,
                    metrics.avg_inventory,
                    metrics.avg_payables,
                    metrics.revenue,
                    metrics.cogs,
                    metrics.capital_trapped_receivables,
                    metrics.capital_trapped_inventory
                ))
                conn.commit()
                logger.info("Analysis results saved to database")
        finally:
            conn.close()

    def get_trends(self, months: int = 12, interval: str = 'monthly') -> List[CapitalLeakMetrics]:
        """
        Get historical trends

        Args:
            months: Number of months to look back
            interval: 'monthly' or 'quarterly'

        Returns:
            List of CapitalLeakMetrics for each period
        """
        trends = []
        end_date = date.today()

        if interval == 'monthly':
            period_days = 30
            periods = months
        else:  # quarterly
            period_days = 90
            periods = months // 3

        for i in range(periods):
            period_end = end_date - timedelta(days=i * period_days)
            period_start = period_end - timedelta(days=period_days)

            try:
                metrics = self.analyze_period(
                    period_start.strftime('%Y-%m-%d'),
                    period_end.strftime('%Y-%m-%d')
                )
                trends.append(metrics)
            except Exception as e:
                logger.warning(f"Could not analyze period {period_start} to {period_end}: {e}")

        return trends

    def load_data_from_csv(self, entity_type: str, file_path: str, erp_system: ERPSystem = ERPSystem.CUSTOM):
        """
        Load data from CSV file

        Args:
            entity_type: Type of data (invoice, inventory, payable, revenue)
            file_path: Path to CSV file
            erp_system: ERP system type for field mapping
        """
        logger.info(f"Loading {entity_type} data from {file_path}")

        # Extract data
        extractor = CSVExtractor()
        raw_data = extractor.extract(file_path)

        if not raw_data:
            logger.error("No data extracted")
            return

        # Transform data
        transformer = DataTransformer(erp_system)
        transform_methods = {
            'invoice': transformer.transform_invoices,
            'inventory': transformer.transform_inventory,
            'payable': transformer.transform_payables,
            'revenue': transformer.transform_revenue
        }

        transform_method = transform_methods.get(entity_type)
        if not transform_method:
            logger.error(f"Unknown entity type: {entity_type}")
            return

        transformed_data = transform_method(raw_data)

        # Load data
        load_methods = {
            'invoice': self.data_loader.load_invoices,
            'inventory': self.data_loader.load_inventory,
            'payable': self.data_loader.load_payables,
            'revenue': self.data_loader.load_revenue
        }

        load_method = load_methods.get(entity_type)
        if load_method:
            loaded = load_method(transformed_data)
            logger.info(f"Successfully loaded {loaded} {entity_type} records")


def main():
    """Main entry point"""
    print("Capital Leak Analysis Platform")
    print("=" * 50)

    analyzer = CapitalLeakAnalyzer()

    # Example usage
    print("\nAnalyzing current quarter...")

    # Calculate current quarter dates
    today = date.today()
    quarter_start = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)

    try:
        # Run analysis
        metrics = analyzer.analyze_period(
            quarter_start.strftime('%Y-%m-%d'),
            today.strftime('%Y-%m-%d')
        )

        print(metrics)

        # Generate recommendations
        print("\nRecommendations:")
        print("-" * 50)

        if metrics.dso > 45:
            print(f"⚠ DSO is high at {metrics.dso:.1f} days. Target: 35-40 days")
            print("  → Improve collection processes")
            print("  → Offer early payment discounts")

        if metrics.dio > 60:
            print(f"⚠ DIO is high at {metrics.dio:.1f} days. Target: 45-50 days")
            print("  → Optimize inventory management")
            print("  → Implement just-in-time inventory")

        if metrics.dpo < 30:
            print(f"⚠ DPO is low at {metrics.dpo:.1f} days. Target: 40-45 days")
            print("  → Negotiate better payment terms")
            print("  → Optimize payment timing")

        potential_improvement = max(0, metrics.ccc - 30)  # Target CCC of 30 days
        if potential_improvement > 0:
            daily_revenue = metrics.revenue / ((metrics.period_end - metrics.period_start).days)
            potential_cash_release = potential_improvement * daily_revenue
            print(f"\n💰 Potential Cash Release: ${potential_cash_release:,.2f}")
            print(f"   By reducing CCC from {metrics.ccc:.1f} to 30 days")

    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        print(f"\n❌ Analysis failed: {str(e)}")
        print("\nPlease ensure:")
        print("1. Database is set up (run scripts/setup_database.py)")
        print("2. Data has been loaded")
        print("3. .env file is configured correctly")


if __name__ == "__main__":
    main()
