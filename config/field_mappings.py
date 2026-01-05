"""ERP Field Mapping Configurations"""

FIELD_MAPPINGS = {
    'SAP': {
        'transactions': {
            'transaction_number': 'BELNR',
            'transaction_date': 'BUDAT',
            'due_date': 'ZFBDT',
            'amount': 'DMBTR',
            'gl_account': 'HKONT',
            'customer_vendor': 'KUNNR',
            'status': 'AUGBL',
        },
        'event_logs': {
            'event_timestamp': 'CPUDT',
            'user_id': 'USNAM',
            'event_type': 'TCODE',
        }
    },
    'ORACLE': {
        'transactions': {
            'transaction_number': 'TRX_NUMBER',
            'transaction_date': 'TRX_DATE',
            'due_date': 'DUE_DATE',
            'amount': 'AMOUNT',
            'gl_account': 'CODE_COMBINATION_ID',
            'customer_vendor': 'CUSTOMER_ID',
            'status': 'STATUS',
        }
    },
    'NETSUITE': {
        'transactions': {
            'transaction_number': 'tranid',
            'transaction_date': 'trandate',
            'due_date': 'duedate',
            'amount': 'amount',
            'gl_account': 'account',
            'customer_vendor': 'entity',
            'status': 'status',
        }
    }
}

DATA_TRANSFORMATIONS = {
    'date_fields': ['transaction_date', 'due_date', 'event_timestamp'],
    'decimal_fields': ['amount', 'outstanding_amount'],
    'integer_fields': ['days_outstanding'],
    'string_fields': ['transaction_number', 'gl_account', 'customer_vendor']
}

def get_mapping(erp_system: str, data_type: str = 'transactions') -> dict:
    erp_upper = erp_system.upper()
    if erp_upper not in FIELD_MAPPINGS:
        raise ValueError(f"Unsupported ERP: {erp_system}")
    return FIELD_MAPPINGS[erp_upper].get(data_type, {})
