"""
Data transformation module
Transforms raw ERP data to standardized schema
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import logging
from config.field_mappings import FieldMappings, ERPSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataTransformer:
    """Transform raw ERP data to standard schema"""

    def __init__(self, erp_system: ERPSystem = ERPSystem.CUSTOM):
        """
        Initialize transformer

        Args:
            erp_system: Type of ERP system
        """
        self.erp_system = erp_system
        self.field_mappings = FieldMappings()

    def transform_invoices(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform invoice data

        Args:
            raw_data: Raw invoice data

        Returns:
            Transformed invoice data
        """
        transformed = []
        logger.info(f"Transforming {len(raw_data)} invoice records")

        for record in raw_data:
            try:
                # Map fields to standard schema
                mapped = self.field_mappings.map_data(self.erp_system, 'invoice', record)

                # Transform data types and calculate derived fields
                transformed_record = {
                    'invoice_id': str(mapped.get('invoice_id', '')),
                    'customer_id': str(mapped.get('customer_id', '')),
                    'customer_name': str(mapped.get('customer_name', '')),
                    'invoice_date': self._parse_date(mapped.get('invoice_date')),
                    'due_date': self._parse_date(mapped.get('due_date')),
                    'payment_date': self._parse_date(mapped.get('payment_date')),
                    'amount': self._parse_decimal(mapped.get('amount', 0)),
                    'currency': mapped.get('currency', 'USD'),
                    'status': self._normalize_status(mapped.get('status', 'UNKNOWN'))
                }

                # Calculate days to payment if paid
                if transformed_record['payment_date'] and transformed_record['invoice_date']:
                    transformed_record['days_to_payment'] = (
                        transformed_record['payment_date'] - transformed_record['invoice_date']
                    ).days

                transformed.append(transformed_record)

            except Exception as e:
                logger.warning(f"Error transforming invoice record: {str(e)}")
                continue

        logger.info(f"Successfully transformed {len(transformed)} invoice records")
        return transformed

    def transform_inventory(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform inventory data

        Args:
            raw_data: Raw inventory data

        Returns:
            Transformed inventory data
        """
        transformed = []
        logger.info(f"Transforming {len(raw_data)} inventory records")

        for record in raw_data:
            try:
                mapped = self.field_mappings.map_data(self.erp_system, 'inventory', record)

                transformed_record = {
                    'sku': str(mapped.get('sku', '')),
                    'product_name': str(mapped.get('product_name', '')),
                    'category': mapped.get('category', 'UNCATEGORIZED'),
                    'quantity': self._parse_int(mapped.get('quantity', 0)),
                    'unit_cost': self._parse_decimal(mapped.get('unit_cost', 0)),
                    'total_value': self._parse_decimal(mapped.get('total_value', 0)),
                    'location': mapped.get('location', 'UNKNOWN'),
                    'movement_date': self._parse_date(mapped.get('movement_date')),
                    'movement_type': self._normalize_movement_type(mapped.get('movement_type', ''))
                }

                # Calculate total value if not provided
                if not transformed_record['total_value'] and transformed_record['quantity']:
                    transformed_record['total_value'] = (
                        transformed_record['quantity'] * transformed_record['unit_cost']
                    )

                transformed.append(transformed_record)

            except Exception as e:
                logger.warning(f"Error transforming inventory record: {str(e)}")
                continue

        logger.info(f"Successfully transformed {len(transformed)} inventory records")
        return transformed

    def transform_payables(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform payables data

        Args:
            raw_data: Raw payables data

        Returns:
            Transformed payables data
        """
        transformed = []
        logger.info(f"Transforming {len(raw_data)} payable records")

        for record in raw_data:
            try:
                mapped = self.field_mappings.map_data(self.erp_system, 'payable', record)

                transformed_record = {
                    'payable_id': str(mapped.get('payable_id', '')),
                    'vendor_id': str(mapped.get('vendor_id', '')),
                    'vendor_name': str(mapped.get('vendor_name', '')),
                    'invoice_date': self._parse_date(mapped.get('invoice_date')),
                    'due_date': self._parse_date(mapped.get('due_date')),
                    'payment_date': self._parse_date(mapped.get('payment_date')),
                    'amount': self._parse_decimal(mapped.get('amount', 0)),
                    'currency': mapped.get('currency', 'USD'),
                    'status': self._normalize_status(mapped.get('status', 'UNKNOWN'))
                }

                # Calculate days to payment if paid
                if transformed_record['payment_date'] and transformed_record['invoice_date']:
                    transformed_record['days_to_payment'] = (
                        transformed_record['payment_date'] - transformed_record['invoice_date']
                    ).days

                transformed.append(transformed_record)

            except Exception as e:
                logger.warning(f"Error transforming payable record: {str(e)}")
                continue

        logger.info(f"Successfully transformed {len(transformed)} payable records")
        return transformed

    def transform_revenue(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform revenue/COGS data

        Args:
            raw_data: Raw revenue data

        Returns:
            Transformed revenue data
        """
        transformed = []
        logger.info(f"Transforming {len(raw_data)} revenue records")

        for record in raw_data:
            try:
                mapped = self.field_mappings.map_data(self.erp_system, 'revenue', record)

                transformed_record = {
                    'period_start': self._parse_date(mapped.get('period_start')),
                    'period_end': self._parse_date(mapped.get('period_end')),
                    'revenue': self._parse_decimal(mapped.get('revenue', 0)),
                    'cogs': self._parse_decimal(mapped.get('cogs', 0)),
                    'currency': mapped.get('currency', 'USD')
                }

                transformed.append(transformed_record)

            except Exception as e:
                logger.warning(f"Error transforming revenue record: {str(e)}")
                continue

        logger.info(f"Successfully transformed {len(transformed)} revenue records")
        return transformed

    # Helper methods for data type conversion

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse date from various formats"""
        if value is None or value == '':
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            # Try common date formats
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y%m%d',
                '%d-%m-%Y',
                '%m-%d-%Y'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

        logger.warning(f"Could not parse date: {value}")
        return None

    def _parse_decimal(self, value: Any) -> float:
        """Parse decimal/float from various formats"""
        if value is None or value == '':
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # Remove common formatting characters
            cleaned = value.replace(',', '').replace('$', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                logger.warning(f"Could not parse decimal: {value}")
                return 0.0

        return 0.0

    def _parse_int(self, value: Any) -> int:
        """Parse integer from various formats"""
        if value is None or value == '':
            return 0

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            cleaned = value.replace(',', '').strip()
            try:
                return int(float(cleaned))
            except ValueError:
                logger.warning(f"Could not parse integer: {value}")
                return 0

        return 0

    def _normalize_status(self, status: str) -> str:
        """Normalize status values"""
        if not status:
            return 'UNKNOWN'

        status = str(status).upper().strip()

        # Map various status values to standard ones
        status_map = {
            'OPEN': 'OPEN',
            'PENDING': 'OPEN',
            'UNPAID': 'OPEN',
            'PAID': 'PAID',
            'COMPLETED': 'PAID',
            'CLOSED': 'PAID',
            'OVERDUE': 'OVERDUE',
            'LATE': 'OVERDUE',
            'CANCELLED': 'CANCELLED',
            'CANCELED': 'CANCELLED',
            'VOID': 'CANCELLED',
            'APPROVED': 'APPROVED'
        }

        return status_map.get(status, 'UNKNOWN')

    def _normalize_movement_type(self, movement_type: str) -> str:
        """Normalize inventory movement types"""
        if not movement_type:
            return 'UNKNOWN'

        movement_type = str(movement_type).upper().strip()

        # Map various movement types to standard ones
        type_map = {
            'RECEIPT': 'RECEIPT',
            'RECEIVE': 'RECEIPT',
            'IN': 'RECEIPT',
            'PURCHASE': 'PURCHASE',
            'BUY': 'PURCHASE',
            'SALE': 'SALE',
            'SELL': 'SALE',
            'OUT': 'SALE',
            'SHIP': 'SALE',
            'ADJUSTMENT': 'ADJUSTMENT',
            'ADJUSTMENT_IN': 'ADJUSTMENT_IN',
            'ADJUSTMENT_OUT': 'ADJUSTMENT_OUT',
            'TRANSFER': 'TRANSFER',
            'RETURN': 'RETURN'
        }

        return type_map.get(movement_type, 'UNKNOWN')

    def validate_transformed_data(self, data: List[Dict[str, Any]], entity_type: str) -> bool:
        """
        Validate transformed data

        Args:
            data: Transformed data
            entity_type: Type of entity (invoice, inventory, payable, revenue)

        Returns:
            True if valid, False otherwise
        """
        if not data:
            logger.warning("No data to validate")
            return False

        # Get required fields for entity type
        required_fields_map = {
            'invoice': ['invoice_id', 'customer_id', 'invoice_date', 'amount'],
            'inventory': ['sku', 'movement_date', 'quantity'],
            'payable': ['payable_id', 'vendor_id', 'invoice_date', 'amount'],
            'revenue': ['period_start', 'period_end', 'revenue', 'cogs']
        }

        required_fields = required_fields_map.get(entity_type, [])

        for record in data:
            missing = [field for field in required_fields if not record.get(field)]
            if missing:
                logger.warning(f"Missing required fields in {entity_type}: {missing}")
                return False

        return True
