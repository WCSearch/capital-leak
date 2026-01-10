"""
Unified DIO Trapped Capital Calculator

Intelligently routes to appropriate methodology based on company type:
- DISTRIBUTION → Velocity-based time benchmarks
- MANUFACTURING → BOM critical path analysis

This is the main entry point for all DIO trapped capital calculations.

Author: Capital Leak Analysis Team
Date: 2025-01-10
"""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from config.database import get_supabase_client
from utils.company_type_detector import CompanyTypeDetector, detect_company_type
from utils.dio_distribution import DistributionDIOCalculator
from utils.dio_manufacturing import ManufacturingDIOCalculator


class DIOTrappedCapitalCalculator:
    """
    Unified DIO calculator that adapts to company type

    Routes to appropriate methodology:
    - Distribution companies: Velocity benchmarks (hours/days)
    - Manufacturing companies: BOM critical path analysis
    """

    def __init__(self, company_id: str, analysis_date: Optional[datetime] = None):
        """
        Initialize unified calculator

        Args:
            company_id: UUID of the company
            analysis_date: Date of analysis (defaults to today)
        """
        self.company_id = company_id
        self.analysis_date = analysis_date or datetime.now()
        self.supabase = get_supabase_client()

        # Detect company type
        self.detector = CompanyTypeDetector(company_id)
        self.company_type = self.detector.get_company_type()

        # Initialize appropriate calculator
        if self.company_type == 'DISTRIBUTION':
            self.calculator = DistributionDIOCalculator(company_id, self.analysis_date)
        else:  # MANUFACTURING
            self.calculator = ManufacturingDIOCalculator(company_id, self.analysis_date)

        self.company_data = None
        self.transactions = []
        self.results = None

    def load_company_data(self) -> None:
        """Load company information"""
        try:
            response = self.supabase.table('companies').select('*').eq(
                'company_id', self.company_id
            ).execute()

            if response.data and len(response.data) > 0:
                self.company_data = response.data[0]
        except Exception as e:
            print(f"Warning: Could not load company data: {e}")
            self.company_data = {}

    def load_transactions(self) -> None:
        """Load DIO transactions for the company"""
        try:
            response = self.supabase.table('transactions').select('*').eq(
                'company_id', self.company_id
            ).eq('component_type', 'DIO').execute()

            self.transactions = response.data if response.data else []

        except Exception as e:
            print(f"Error loading transactions: {e}")
            self.transactions = []

    def calculate_trapped_capital(self) -> Dict:
        """
        Main calculation entry point - routes to appropriate methodology

        Returns:
            Comprehensive trapped capital analysis adapted to company type
        """
        # Load data
        if not self.company_data:
            self.load_company_data()

        # Route to appropriate calculator
        if self.company_type == 'DISTRIBUTION':
            return self._calculate_distribution()
        else:  # MANUFACTURING
            return self._calculate_manufacturing()

    def _calculate_distribution(self) -> Dict:
        """Calculate for distribution company using velocity benchmarks"""
        # Load transactions
        if not self.transactions:
            self.load_transactions()

        # Pass to distribution calculator
        self.calculator.load_transactions(self.transactions)
        result = self.calculator.calculate_trapped_capital()

        # Add company metadata
        result['company_name'] = self.company_data.get('company_name', 'Unknown')
        result['industry'] = self.company_data.get('industry', 'Distribution')
        result['erp_system'] = self.company_data.get('erp_system', 'Unknown')
        result['detection_details'] = self.detector.get_detection_details()

        self.results = result
        return result

    def _calculate_manufacturing(self) -> Dict:
        """Calculate for manufacturing company using BOM analysis"""
        # Load manufacturing-specific data
        self.calculator.load_data()
        result = self.calculator.calculate_trapped_capital()

        # Add company metadata
        result['company_name'] = self.company_data.get('company_name', 'Unknown')
        result['industry'] = self.company_data.get('industry', 'Manufacturing')
        result['erp_system'] = self.company_data.get('erp_system', 'Unknown')
        result['detection_details'] = self.detector.get_detection_details()

        self.results = result
        return result

    def get_summary(self) -> Dict:
        """
        Get executive summary of trapped capital analysis

        Returns:
            High-level summary with key metrics
        """
        if not self.results:
            self.results = self.calculate_trapped_capital()

        return {
            'company_id': self.company_id,
            'company_name': self.results.get('company_name', 'Unknown'),
            'company_type': self.company_type,
            'methodology': self.results.get('methodology', 'Unknown'),
            'analysis_date': self.analysis_date.isoformat(),

            # Key metrics
            'total_dio_value': self.results.get('total_dio_value', 0),
            'trapped_capital': self.results.get('trapped_capital', 0),
            'recognized_losses': self.results.get('recognized_losses', 0),
            'net_recovery': self.results.get('net_recovery', 0),
            'recovery_rate': self.results.get('recovery_rate', 0),

            # Breakdown
            'issues_count': len(self.results.get('issues_breakdown', {})),
            'top_issues': self._get_top_issues(3)
        }

    def _get_top_issues(self, limit: int = 3) -> List[Dict]:
        """Get top issues by trapped capital amount"""
        if not self.results or 'issues_breakdown' not in self.results:
            return []

        issues_breakdown = self.results['issues_breakdown']

        # Sort by trapped capital
        sorted_issues = sorted(
            issues_breakdown.items(),
            key=lambda x: x[1].get('trapped_capital', 0),
            reverse=True
        )

        top_issues = []
        for issue_type, data in sorted_issues[:limit]:
            top_issues.append({
                'issue_type': issue_type,
                'description': data.get('description', ''),
                'trapped_capital': data.get('trapped_capital', 0),
                'item_count': data.get('trapped_count', 0)
            })

        return top_issues

    def get_detailed_breakdown(self) -> pd.DataFrame:
        """
        Get detailed breakdown of all issues as DataFrame

        Returns:
            DataFrame with one row per issue type
        """
        if not self.results:
            self.results = self.calculate_trapped_capital()

        issues_breakdown = self.results.get('issues_breakdown', {})

        rows = []
        for issue_type, data in issues_breakdown.items():
            rows.append({
                'issue_type': issue_type,
                'description': data.get('description', ''),
                'recovery_type': data.get('recovery_type', ''),
                'trapped_capital': data.get('trapped_capital', 0),
                'recognized_losses': data.get('recognized_losses', 0),
                'partial_recovery_gross': data.get('partial_recovery_gross', 0),
                'partial_recovery_net': data.get('partial_recovery_net', 0),
                'normal_operations': data.get('normal_operations', 0) or data.get('normal_wip', 0),
                'trapped_count': data.get('trapped_count', 0),
                'loss_count': data.get('loss_count', 0),
                'normal_count': data.get('normal_count', 0)
            })

        return pd.DataFrame(rows)

    def export_to_dict(self) -> Dict:
        """Export full results as dictionary (for JSON serialization)"""
        if not self.results:
            self.results = self.calculate_trapped_capital()

        return self.results


def calculate_dio_trapped_capital(
    company_id: str,
    analysis_date: Optional[datetime] = None
) -> Dict:
    """
    Convenience function to calculate DIO trapped capital

    Args:
        company_id: UUID of the company
        analysis_date: Optional analysis date (defaults to today)

    Returns:
        Comprehensive trapped capital analysis
    """
    calculator = DIOTrappedCapitalCalculator(company_id, analysis_date)
    return calculator.calculate_trapped_capital()


def get_dio_summary(company_id: str) -> Dict:
    """
    Convenience function to get DIO trapped capital summary

    Args:
        company_id: UUID of the company

    Returns:
        Executive summary of trapped capital
    """
    calculator = DIOTrappedCapitalCalculator(company_id)
    return calculator.get_summary()


def compare_companies(company_ids: List[str]) -> pd.DataFrame:
    """
    Compare DIO trapped capital across multiple companies

    Args:
        company_ids: List of company UUIDs

    Returns:
        DataFrame with comparison metrics
    """
    results = []

    for company_id in company_ids:
        try:
            summary = get_dio_summary(company_id)
            results.append(summary)
        except Exception as e:
            print(f"Error processing company {company_id}: {e}")
            continue

    return pd.DataFrame(results)


# Example usage and testing
if __name__ == '__main__':
    """
    Example usage of the unified DIO calculator
    """

    # Example company IDs (replace with actual UUIDs)
    EXAMPLE_DISTRIBUTION = 'distribution-company-uuid'
    EXAMPLE_MANUFACTURING = 'manufacturing-company-uuid'

    print("=== DIO Trapped Capital Calculator ===\n")

    # Example 1: Calculate for distribution company
    print("Example 1: Distribution Company")
    print("-" * 50)
    try:
        dist_calc = DIOTrappedCapitalCalculator(EXAMPLE_DISTRIBUTION)
        dist_results = dist_calc.calculate_trapped_capital()

        print(f"Company: {dist_results['company_name']}")
        print(f"Type: {dist_results['company_type']}")
        print(f"Methodology: {dist_results['methodology']}")
        print(f"Total DIO Value: ${dist_results['total_dio_value']:,.0f}")
        print(f"Trapped Capital: ${dist_results['trapped_capital']:,.0f}")
        print(f"Net Recovery: ${dist_results['net_recovery']:,.0f}")
        print(f"Recovery Rate: {dist_results['recovery_rate']:.1%}")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Example 2: Calculate for manufacturing company
    print("Example 2: Manufacturing Company")
    print("-" * 50)
    try:
        mfg_calc = DIOTrappedCapitalCalculator(EXAMPLE_MANUFACTURING)
        mfg_results = mfg_calc.calculate_trapped_capital()

        print(f"Company: {mfg_results['company_name']}")
        print(f"Type: {mfg_results['company_type']}")
        print(f"Methodology: {mfg_results['methodology']}")
        print(f"Total DIO Value: ${mfg_results['total_dio_value']:,.0f}")
        print(f"Trapped Capital: ${mfg_results['trapped_capital']:,.0f}")
        print(f"Net Recovery: ${mfg_results['net_recovery']:,.0f}")
        print(f"Recovery Rate: {mfg_results['recovery_rate']:.1%}")

        if 'component_cascade_analysis' in mfg_results:
            print("\nComponent Shortages:")
            for comp, data in mfg_results['component_cascade_analysis'].items():
                print(f"  - {comp}: {len(data['work_orders_affected'])} WOs, "
                      f"${data['total_trapped']:,.0f} trapped")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    # Example 3: Compare multiple companies
    print("Example 3: Multi-Company Comparison")
    print("-" * 50)
    try:
        comparison = compare_companies([EXAMPLE_DISTRIBUTION, EXAMPLE_MANUFACTURING])
        print(comparison.to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")
