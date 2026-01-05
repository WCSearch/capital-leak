"""
Data loader module
Loads transformed data into database
"""
from typing import List, Dict, Any
import logging
from config.database import get_db_connection, execute_many
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """Load transformed data into database"""

    def __init__(self):
        """Initialize data loader"""
        self.connection = None

    def load_customers(self, data: List[Dict[str, Any]]) -> int:
        """
        Load customer data

        Args:
            data: List of customer dictionaries

        Returns:
            Number of records loaded
        """
        if not data:
            logger.warning("No customer data to load")
            return 0

        query = """
            INSERT INTO customers (customer_id, customer_name, customer_type, credit_limit, payment_terms_days)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (customer_id) DO UPDATE SET
                customer_name = EXCLUDED.customer_name,
                customer_type = EXCLUDED.customer_type,
                credit_limit = EXCLUDED.credit_limit,
                payment_terms_days = EXCLUDED.payment_terms_days,
                updated_at = CURRENT_TIMESTAMP
        """

        records = [
            (
                rec.get('customer_id'),
                rec.get('customer_name'),
                rec.get('customer_type'),
                rec.get('credit_limit'),
                rec.get('payment_terms_days', 30)
            )
            for rec in data
        ]

        try:
            execute_many(query, records)
            logger.info(f"Loaded {len(records)} customer records")
            return len(records)
        except Exception as e:
            logger.error(f"Error loading customers: {str(e)}")
            return 0

    def load_vendors(self, data: List[Dict[str, Any]]) -> int:
        """
        Load vendor data

        Args:
            data: List of vendor dictionaries

        Returns:
            Number of records loaded
        """
        if not data:
            logger.warning("No vendor data to load")
            return 0

        query = """
            INSERT INTO vendors (vendor_id, vendor_name, vendor_type, payment_terms_days)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (vendor_id) DO UPDATE SET
                vendor_name = EXCLUDED.vendor_name,
                vendor_type = EXCLUDED.vendor_type,
                payment_terms_days = EXCLUDED.payment_terms_days,
                updated_at = CURRENT_TIMESTAMP
        """

        records = [
            (
                rec.get('vendor_id'),
                rec.get('vendor_name'),
                rec.get('vendor_type'),
                rec.get('payment_terms_days', 30)
            )
            for rec in data
        ]

        try:
            execute_many(query, records)
            logger.info(f"Loaded {len(records)} vendor records")
            return len(records)
        except Exception as e:
            logger.error(f"Error loading vendors: {str(e)}")
            return 0

    def load_products(self, data: List[Dict[str, Any]]) -> int:
        """
        Load product data

        Args:
            data: List of product dictionaries

        Returns:
            Number of records loaded
        """
        if not data:
            logger.warning("No product data to load")
            return 0

        query = """
            INSERT INTO products (sku, product_name, category, subcategory, unit_cost, unit_price)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (sku) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                subcategory = EXCLUDED.subcategory,
                unit_cost = EXCLUDED.unit_cost,
                unit_price = EXCLUDED.unit_price,
                updated_at = CURRENT_TIMESTAMP
        """

        records = [
            (
                rec.get('sku'),
                rec.get('product_name'),
                rec.get('category'),
                rec.get('subcategory'),
                rec.get('unit_cost'),
                rec.get('unit_price')
            )
            for rec in data
        ]

        try:
            execute_many(query, records)
            logger.info(f"Loaded {len(records)} product records")
            return len(records)
        except Exception as e:
            logger.error(f"Error loading products: {str(e)}")
            return 0

    def load_invoices(self, data: List[Dict[str, Any]]) -> int:
        """
        Load invoice data

        Args:
            data: List of invoice dictionaries

        Returns:
            Number of records loaded
        """
        if not data:
            logger.warning("No invoice data to load")
            return 0

        # First, extract and load unique customers
        customers = [
            {
                'customer_id': rec.get('customer_id'),
                'customer_name': rec.get('customer_name', 'Unknown')
            }
            for rec in data
            if rec.get('customer_id')
        ]
        unique_customers = {c['customer_id']: c for c in customers}.values()
        if unique_customers:
            self.load_customers(list(unique_customers))

        # Load invoices
        query = """
            INSERT INTO invoices (invoice_id, customer_id, invoice_date, due_date, payment_date,
                                amount, currency, status, days_to_payment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (invoice_id) DO UPDATE SET
                customer_id = EXCLUDED.customer_id,
                invoice_date = EXCLUDED.invoice_date,
                due_date = EXCLUDED.due_date,
                payment_date = EXCLUDED.payment_date,
                amount = EXCLUDED.amount,
                currency = EXCLUDED.currency,
                status = EXCLUDED.status,
                days_to_payment = EXCLUDED.days_to_payment,
                updated_at = CURRENT_TIMESTAMP
        """

        records = [
            (
                rec.get('invoice_id'),
                rec.get('customer_id'),
                rec.get('invoice_date'),
                rec.get('due_date'),
                rec.get('payment_date'),
                rec.get('amount'),
                rec.get('currency', 'USD'),
                rec.get('status'),
                rec.get('days_to_payment')
            )
            for rec in data
        ]

        try:
            execute_many(query, records)
            logger.info(f"Loaded {len(records)} invoice records")
            return len(records)
        except Exception as e:
            logger.error(f"Error loading invoices: {str(e)}")
            return 0

    def load_inventory(self, data: List[Dict[str, Any]]) -> int:
        """
        Load inventory movement data

        Args:
            data: List of inventory dictionaries

        Returns:
            Number of records loaded
        """
        if not data:
            logger.warning("No inventory data to load")
            return 0

        # Extract and load unique products
        products = [
            {
                'sku': rec.get('sku'),
                'product_name': rec.get('product_name', 'Unknown'),
                'category': rec.get('category', 'UNCATEGORIZED'),
                'unit_cost': rec.get('unit_cost', 0)
            }
            for rec in data
            if rec.get('sku')
        ]
        unique_products = {p['sku']: p for p in products}.values()
        if unique_products:
            self.load_products(list(unique_products))

        # Load inventory movements
        query = """
            INSERT INTO inventory_movements (sku, movement_date, movement_type, quantity,
                                            unit_cost, total_value, location, reference_doc)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        records = [
            (
                rec.get('sku'),
                rec.get('movement_date'),
                rec.get('movement_type'),
                rec.get('quantity'),
                rec.get('unit_cost'),
                rec.get('total_value'),
                rec.get('location'),
                rec.get('reference_doc')
            )
            for rec in data
        ]

        try:
            execute_many(query, records)
            logger.info(f"Loaded {len(records)} inventory movement records")
            return len(records)
        except Exception as e:
            logger.error(f"Error loading inventory: {str(e)}")
            return 0

    def load_payables(self, data: List[Dict[str, Any]]) -> int:
        """
        Load payables data

        Args:
            data: List of payable dictionaries

        Returns:
            Number of records loaded
        """
        if not data:
            logger.warning("No payable data to load")
            return 0

        # Extract and load unique vendors
        vendors = [
            {
                'vendor_id': rec.get('vendor_id'),
                'vendor_name': rec.get('vendor_name', 'Unknown')
            }
            for rec in data
            if rec.get('vendor_id')
        ]
        unique_vendors = {v['vendor_id']: v for v in vendors}.values()
        if unique_vendors:
            self.load_vendors(list(unique_vendors))

        # Load payables
        query = """
            INSERT INTO payables (payable_id, vendor_id, invoice_date, due_date, payment_date,
                                amount, currency, status, days_to_payment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (payable_id) DO UPDATE SET
                vendor_id = EXCLUDED.vendor_id,
                invoice_date = EXCLUDED.invoice_date,
                due_date = EXCLUDED.due_date,
                payment_date = EXCLUDED.payment_date,
                amount = EXCLUDED.amount,
                currency = EXCLUDED.currency,
                status = EXCLUDED.status,
                days_to_payment = EXCLUDED.days_to_payment,
                updated_at = CURRENT_TIMESTAMP
        """

        records = [
            (
                rec.get('payable_id'),
                rec.get('vendor_id'),
                rec.get('invoice_date'),
                rec.get('due_date'),
                rec.get('payment_date'),
                rec.get('amount'),
                rec.get('currency', 'USD'),
                rec.get('status'),
                rec.get('days_to_payment')
            )
            for rec in data
        ]

        try:
            execute_many(query, records)
            logger.info(f"Loaded {len(records)} payable records")
            return len(records)
        except Exception as e:
            logger.error(f"Error loading payables: {str(e)}")
            return 0

    def load_revenue(self, data: List[Dict[str, Any]]) -> int:
        """
        Load revenue/COGS data

        Args:
            data: List of revenue dictionaries

        Returns:
            Number of records loaded
        """
        if not data:
            logger.warning("No revenue data to load")
            return 0

        query = """
            INSERT INTO revenue (period_start, period_end, revenue, cogs, currency)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (period_start, period_end) DO UPDATE SET
                revenue = EXCLUDED.revenue,
                cogs = EXCLUDED.cogs,
                currency = EXCLUDED.currency
        """

        records = [
            (
                rec.get('period_start'),
                rec.get('period_end'),
                rec.get('revenue'),
                rec.get('cogs'),
                rec.get('currency', 'USD')
            )
            for rec in data
        ]

        try:
            execute_many(query, records)
            logger.info(f"Loaded {len(records)} revenue records")
            return len(records)
        except Exception as e:
            logger.error(f"Error loading revenue: {str(e)}")
            return 0

    def load_batch(self, entity_type: str, data: List[Dict[str, Any]], batch_size: int = 1000) -> int:
        """
        Load data in batches

        Args:
            entity_type: Type of entity (invoice, inventory, payable, revenue)
            data: Data to load
            batch_size: Number of records per batch

        Returns:
            Total number of records loaded
        """
        total_loaded = 0

        # Get appropriate loader method
        loaders = {
            'invoice': self.load_invoices,
            'inventory': self.load_inventory,
            'payable': self.load_payables,
            'revenue': self.load_revenue,
            'customer': self.load_customers,
            'vendor': self.load_vendors,
            'product': self.load_products
        }

        loader = loaders.get(entity_type)
        if not loader:
            logger.error(f"Unknown entity type: {entity_type}")
            return 0

        # Process in batches
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            loaded = loader(batch)
            total_loaded += loaded
            logger.info(f"Batch {i // batch_size + 1}: Loaded {loaded} records")

        return total_loaded
