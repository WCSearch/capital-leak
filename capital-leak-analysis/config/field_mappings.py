"""
ERP field mapping configurations
Maps ERP-specific field names to standardized schema
"""
from enum import Enum
from typing import Dict, List
from dataclasses import dataclass, field


class ERPSystem(Enum):
    """Supported ERP systems"""
    SAP = "SAP"
    ORACLE = "Oracle ERP Cloud"
    DYNAMICS365 = "Microsoft Dynamics 365"
    NETSUITE = "NetSuite"
    CUSTOM = "Custom"


@dataclass
class EntityMapping:
    """Field mapping for a specific entity"""
    entity_name: str
    field_mappings: Dict[str, str] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)

    def map_field(self, erp_field: str) -> str:
        """Map ERP field to standard field"""
        return self.field_mappings.get(erp_field, erp_field)

    def validate_fields(self, data: dict) -> bool:
        """Validate that all required fields are present"""
        return all(field in data for field in self.required_fields)


class FieldMappings:
    """Central field mapping configuration"""

    # Standard schema field names
    STANDARD_FIELDS = {
        'invoice': [
            'invoice_id', 'invoice_date', 'due_date', 'customer_id',
            'customer_name', 'amount', 'currency', 'status', 'payment_date'
        ],
        'inventory': [
            'sku', 'product_name', 'category', 'quantity', 'unit_cost',
            'total_value', 'location', 'movement_date', 'movement_type'
        ],
        'payable': [
            'payable_id', 'vendor_id', 'vendor_name', 'invoice_date',
            'due_date', 'payment_date', 'amount', 'currency', 'status'
        ],
        'revenue': [
            'period_start', 'period_end', 'revenue', 'cogs', 'currency'
        ]
    }

    # SAP field mappings
    SAP_MAPPINGS = {
        'invoice': EntityMapping(
            entity_name='invoice',
            field_mappings={
                'VBELN': 'invoice_id',
                'FKDAT': 'invoice_date',
                'ZFBDT': 'due_date',
                'KUNAG': 'customer_id',
                'NAME1': 'customer_name',
                'NETWR': 'amount',
                'WAERS': 'currency',
                'FKSTO': 'status',
                'AUGDT': 'payment_date'
            },
            required_fields=['VBELN', 'FKDAT', 'KUNAG', 'NETWR']
        ),
        'inventory': EntityMapping(
            entity_name='inventory',
            field_mappings={
                'MATNR': 'sku',
                'MAKTX': 'product_name',
                'MATKL': 'category',
                'LABST': 'quantity',
                'SALK3': 'total_value',
                'LGORT': 'location',
                'BUDAT': 'movement_date',
                'BWART': 'movement_type'
            },
            required_fields=['MATNR', 'LABST', 'BUDAT']
        ),
        'payable': EntityMapping(
            entity_name='payable',
            field_mappings={
                'BELNR': 'payable_id',
                'LIFNR': 'vendor_id',
                'NAME1': 'vendor_name',
                'BLDAT': 'invoice_date',
                'ZFBDT': 'due_date',
                'AUGDT': 'payment_date',
                'DMBTR': 'amount',
                'WAERS': 'currency',
                'AUGBL': 'status'
            },
            required_fields=['BELNR', 'LIFNR', 'BLDAT', 'DMBTR']
        )
    }

    # Oracle ERP field mappings
    ORACLE_MAPPINGS = {
        'invoice': EntityMapping(
            entity_name='invoice',
            field_mappings={
                'CUSTOMER_TRX_ID': 'invoice_id',
                'TRX_DATE': 'invoice_date',
                'DUE_DATE': 'due_date',
                'CUSTOMER_ID': 'customer_id',
                'CUSTOMER_NAME': 'customer_name',
                'AMOUNT_DUE_ORIGINAL': 'amount',
                'INVOICE_CURRENCY_CODE': 'currency',
                'STATUS': 'status',
                'GL_DATE': 'payment_date'
            },
            required_fields=['CUSTOMER_TRX_ID', 'TRX_DATE', 'CUSTOMER_ID', 'AMOUNT_DUE_ORIGINAL']
        ),
        'inventory': EntityMapping(
            entity_name='inventory',
            field_mappings={
                'INVENTORY_ITEM_ID': 'sku',
                'ITEM_DESCRIPTION': 'product_name',
                'ITEM_CATEGORY': 'category',
                'ONHAND_QUANTITY': 'quantity',
                'ITEM_COST': 'unit_cost',
                'TOTAL_VALUE': 'total_value',
                'SUBINVENTORY_CODE': 'location',
                'TRANSACTION_DATE': 'movement_date',
                'TRANSACTION_TYPE': 'movement_type'
            },
            required_fields=['INVENTORY_ITEM_ID', 'ONHAND_QUANTITY', 'TRANSACTION_DATE']
        )
    }

    # Dynamics 365 field mappings
    DYNAMICS365_MAPPINGS = {
        'invoice': EntityMapping(
            entity_name='invoice',
            field_mappings={
                'invoiceid': 'invoice_id',
                'invoicedate': 'invoice_date',
                'duedate': 'due_date',
                'customerid': 'customer_id',
                'customername': 'customer_name',
                'totalamount': 'amount',
                'transactioncurrencyid': 'currency',
                'statuscode': 'status',
                'datepaid': 'payment_date'
            },
            required_fields=['invoiceid', 'invoicedate', 'customerid', 'totalamount']
        )
    }

    # NetSuite field mappings
    NETSUITE_MAPPINGS = {
        'invoice': EntityMapping(
            entity_name='invoice',
            field_mappings={
                'tranid': 'invoice_id',
                'trandate': 'invoice_date',
                'duedate': 'due_date',
                'entity': 'customer_id',
                'entityname': 'customer_name',
                'total': 'amount',
                'currency': 'currency',
                'status': 'status',
                'closedate': 'payment_date'
            },
            required_fields=['tranid', 'trandate', 'entity', 'total']
        )
    }

    @classmethod
    def get_mapping(cls, erp_system: ERPSystem, entity: str) -> EntityMapping:
        """
        Get field mapping for specific ERP system and entity

        Args:
            erp_system: ERP system type
            entity: Entity name (invoice, inventory, payable, revenue)

        Returns:
            EntityMapping object
        """
        mapping_dict = {
            ERPSystem.SAP: cls.SAP_MAPPINGS,
            ERPSystem.ORACLE: cls.ORACLE_MAPPINGS,
            ERPSystem.DYNAMICS365: cls.DYNAMICS365_MAPPINGS,
            ERPSystem.NETSUITE: cls.NETSUITE_MAPPINGS
        }

        mappings = mapping_dict.get(erp_system, {})
        return mappings.get(entity, EntityMapping(entity_name=entity))

    @classmethod
    def map_data(cls, erp_system: ERPSystem, entity: str, data: dict) -> dict:
        """
        Transform ERP data to standard schema

        Args:
            erp_system: ERP system type
            entity: Entity name
            data: Raw ERP data

        Returns:
            Transformed data with standard field names
        """
        mapping = cls.get_mapping(erp_system, entity)
        transformed = {}

        for erp_field, value in data.items():
            standard_field = mapping.map_field(erp_field)
            transformed[standard_field] = value

        return transformed

    @classmethod
    def get_standard_fields(cls, entity: str) -> List[str]:
        """Get list of standard fields for an entity"""
        return cls.STANDARD_FIELDS.get(entity, [])
