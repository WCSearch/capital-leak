"""
Company Type Detection Module

Automatically detects whether a company is DISTRIBUTION or MANUFACTURING
based on data patterns, ERP system, and explicit configuration.

This is critical for DIO analysis because:
- DISTRIBUTION companies use velocity-based benchmarks (hours/days)
- MANUFACTURING companies use BOM critical path analysis

Author: Capital Leak Analysis Team
Date: 2025-01-10
"""

from typing import Dict, Optional, Literal
import pandas as pd
from config.database import get_supabase_client

CompanyType = Literal['DISTRIBUTION', 'MANUFACTURING']

# ERP system hints for company type
ERP_TYPE_MAPPING = {
    'SAP ECC': 'MANUFACTURING',
    'SAP S/4HANA': 'MANUFACTURING',
    'Oracle E-Business Suite': 'MANUFACTURING',
    'Oracle EBS R12.2': 'MANUFACTURING',
    'Oracle EBS': 'MANUFACTURING',
    'Infor CloudSuite Distribution': 'DISTRIBUTION',
    'Infor CloudSuite Industrial': 'MANUFACTURING',
    'Infor M3': 'MANUFACTURING',
    'NetSuite': 'BOTH',  # Generic ERP, check data
    'Microsoft Dynamics 365 Supply Chain': 'MANUFACTURING',
    'Microsoft Dynamics 365 Commerce': 'DISTRIBUTION',
    'Epicor ERP': 'MANUFACTURING',
    'QAD': 'MANUFACTURING',
    'IFS': 'MANUFACTURING'
}


class CompanyTypeDetector:
    """Detects and manages company type classification"""

    def __init__(self, company_id: str):
        """Initialize detector for a specific company"""
        self.company_id = company_id
        self.supabase = get_supabase_client()
        self._company_data = None
        self._detected_type = None

    def get_company_type(self) -> CompanyType:
        """
        Get company type using the following priority:
        1. Explicit configuration in companies table
        2. Auto-detection from data patterns
        3. ERP system hint
        4. Default to DISTRIBUTION

        Returns:
            'DISTRIBUTION' or 'MANUFACTURING'
        """
        # Load company data
        if self._company_data is None:
            self._load_company_data()

        # Method 1: Explicit configuration
        if self._company_data and 'company_type' in self._company_data:
            explicit_type = self._company_data.get('company_type')
            if explicit_type in ['DISTRIBUTION', 'MANUFACTURING']:
                return explicit_type

        # Method 2: Auto-detect from data
        detected_type = self._auto_detect_from_data()
        if detected_type:
            return detected_type

        # Method 3: ERP system hint
        erp_hint = self._detect_from_erp_system()
        if erp_hint and erp_hint != 'BOTH':
            return erp_hint

        # Method 4: Default to DISTRIBUTION
        return 'DISTRIBUTION'

    def _load_company_data(self):
        """Load company record from database"""
        try:
            response = self.supabase.table('companies').select('*').eq(
                'company_id', self.company_id
            ).execute()

            if response.data and len(response.data) > 0:
                self._company_data = response.data[0]
        except Exception as e:
            print(f"Warning: Could not load company data: {e}")
            self._company_data = {}

    def _auto_detect_from_data(self) -> Optional[CompanyType]:
        """
        Auto-detect company type from transaction patterns

        Manufacturing indicators:
        - Work orders exist
        - BOM structure exists
        - WIP transactions present
        - Lower transaction volume, higher avg value

        Distribution indicators:
        - Cross-dock/staging statuses
        - High transaction volume
        - Lower average transaction value
        - Cycle count variance transactions
        """
        try:
            # Check for manufacturing indicators
            has_work_orders = self._check_table_exists('work_orders')
            has_bom_data = self._check_table_exists('bom_structure')
            has_wip_transactions = self._check_transaction_types('WIP')
            has_subcontract = self._check_table_exists('subcontract_items')
            has_quarantine = self._check_table_exists('quarantine_items')

            # Check for distribution indicators
            has_cross_dock = self._check_transaction_statuses('STAGED_CROSSDOCK')
            has_cycle_count = self._check_transaction_statuses('CYCLE_COUNT_VARIANCE')

            # Get transaction patterns
            tx_stats = self._get_transaction_statistics()

            # Decision logic
            manufacturing_score = 0
            distribution_score = 0

            # Strong manufacturing indicators
            if has_work_orders:
                manufacturing_score += 3
            if has_bom_data:
                manufacturing_score += 3
            if has_wip_transactions:
                manufacturing_score += 2
            if has_subcontract:
                manufacturing_score += 2
            if has_quarantine:
                manufacturing_score += 1

            # Strong distribution indicators
            if has_cross_dock:
                distribution_score += 3
            if has_cycle_count:
                distribution_score += 2

            # Transaction pattern indicators
            if tx_stats:
                if tx_stats['count'] > 2500:
                    distribution_score += 2  # High volume
                if tx_stats['avg_value'] < 100000:
                    distribution_score += 1  # Lower avg value
                if tx_stats['avg_value'] > 200000:
                    manufacturing_score += 1  # Higher avg value

            # Make decision
            if manufacturing_score > distribution_score:
                return 'MANUFACTURING'
            elif distribution_score > manufacturing_score:
                return 'DISTRIBUTION'
            else:
                return None  # Ambiguous, fall through to next method

        except Exception as e:
            print(f"Warning: Auto-detection failed: {e}")
            return None

    def _check_table_exists(self, table_name: str) -> bool:
        """Check if a table has data for this company"""
        try:
            response = self.supabase.table(table_name).select(
                'company_id', count='exact'
            ).eq('company_id', self.company_id).limit(1).execute()

            return response.count > 0 if hasattr(response, 'count') else False
        except:
            return False

    def _check_transaction_types(self, type_keyword: str) -> bool:
        """Check if transactions contain specific type keyword"""
        try:
            response = self.supabase.table('transactions').select(
                'transaction_id', count='exact'
            ).eq('company_id', self.company_id).ilike(
                'status', f'%{type_keyword}%'
            ).limit(1).execute()

            return response.count > 0 if hasattr(response, 'count') else False
        except:
            return False

    def _check_transaction_statuses(self, status_value: str) -> bool:
        """Check if transactions have specific status"""
        try:
            response = self.supabase.table('transactions').select(
                'transaction_id', count='exact'
            ).eq('company_id', self.company_id).eq(
                'status', status_value
            ).limit(1).execute()

            return response.count > 0 if hasattr(response, 'count') else False
        except:
            return False

    def _get_transaction_statistics(self) -> Optional[Dict]:
        """Get transaction count and average value for pattern analysis"""
        try:
            response = self.supabase.table('transactions').select(
                'amount'
            ).eq('company_id', self.company_id).eq(
                'component_type', 'DIO'
            ).execute()

            if response.data:
                df = pd.DataFrame(response.data)
                return {
                    'count': len(df),
                    'avg_value': df['amount'].mean() if 'amount' in df.columns else 0,
                    'total_value': df['amount'].sum() if 'amount' in df.columns else 0
                }
            return None
        except:
            return None

    def _detect_from_erp_system(self) -> Optional[CompanyType]:
        """Detect company type based on ERP system"""
        if not self._company_data:
            return None

        erp_system = self._company_data.get('erp_system', '')

        # Look for exact match
        if erp_system in ERP_TYPE_MAPPING:
            return ERP_TYPE_MAPPING[erp_system]

        # Look for partial match
        for erp_key, company_type in ERP_TYPE_MAPPING.items():
            if erp_key.lower() in erp_system.lower():
                return company_type

        return None

    def get_detection_details(self) -> Dict:
        """
        Get detailed information about how company type was detected
        Useful for debugging and transparency
        """
        if self._company_data is None:
            self._load_company_data()

        explicit_type = self._company_data.get('company_type') if self._company_data else None
        auto_detected = self._auto_detect_from_data()
        erp_hint = self._detect_from_erp_system()
        final_type = self.get_company_type()

        # Get scores
        has_work_orders = self._check_table_exists('work_orders')
        has_bom_data = self._check_table_exists('bom_structure')
        has_cross_dock = self._check_transaction_statuses('STAGED_CROSSDOCK')
        tx_stats = self._get_transaction_statistics()

        return {
            'company_id': self.company_id,
            'company_name': self._company_data.get('company_name') if self._company_data else 'Unknown',
            'final_type': final_type,
            'detection_method': self._get_detection_method(),
            'explicit_type': explicit_type,
            'auto_detected': auto_detected,
            'erp_hint': erp_hint,
            'erp_system': self._company_data.get('erp_system') if self._company_data else None,
            'indicators': {
                'has_work_orders': has_work_orders,
                'has_bom_data': has_bom_data,
                'has_cross_dock': has_cross_dock,
                'transaction_count': tx_stats['count'] if tx_stats else 0,
                'avg_transaction_value': tx_stats['avg_value'] if tx_stats else 0
            }
        }

    def _get_detection_method(self) -> str:
        """Determine which method was used for final detection"""
        if self._company_data and self._company_data.get('company_type'):
            return 'EXPLICIT_CONFIG'

        auto_detected = self._auto_detect_from_data()
        if auto_detected:
            return 'AUTO_DETECT_DATA'

        erp_hint = self._detect_from_erp_system()
        if erp_hint and erp_hint != 'BOTH':
            return 'ERP_SYSTEM_HINT'

        return 'DEFAULT'


def detect_company_type(company_id: str) -> CompanyType:
    """
    Convenience function to detect company type

    Args:
        company_id: UUID of the company

    Returns:
        'DISTRIBUTION' or 'MANUFACTURING'
    """
    detector = CompanyTypeDetector(company_id)
    return detector.get_company_type()


def get_company_type_details(company_id: str) -> Dict:
    """
    Get detailed information about company type detection

    Args:
        company_id: UUID of the company

    Returns:
        Dictionary with detection details
    """
    detector = CompanyTypeDetector(company_id)
    return detector.get_detection_details()
