"""
ETL Metadata Enhancement Script

Adds business model classification fields to existing transaction extraction.

USAGE:
1. Update your ERP extractors (SAP/Oracle/NetSuite) to include new fields
2. Re-run ETL for recent transactions (last 3-6 months recommended)
3. Test classification on sample companies
4. Roll out to all companies

INCREMENTAL APPROACH:
- Phase 1: Basic classification fields (item_id, location_code, etc.)
- Phase 2: Distribution fields (abc_class, movement_class, margin)
- Phase 3: Manufacturing fields (work_order, operation_seq, qa_status)
"""

# ============================================================================
# PHASE 1: BASIC CLASSIFICATION (Required for all)
# ============================================================================

def extract_basic_classification_metadata_sap(row):
    """
    Extract basic classification metadata from SAP.

    SAP Tables:
    - MSEG: Material document (goods movements)
    - MARA: Material master
    - T001W: Plants/facilities
    """
    return {
        # Existing fields (keep these)
        "material_type": row.get('MTART'),  # Material type
        "quantity": float(row.get('MENGE', 0)),
        "unit_price": float(row.get('DMBTR', 0)) / float(row.get('MENGE', 1)),

        # NEW - Phase 1: Basic classification (7 fields)
        "item_id": row.get('MATNR'),  # Material number
        "location_code": f"{row.get('LGORT', '')}-{row.get('LGPLA', '')}",  # Storage loc + bin
        "plant_code": row.get('WERKS'),  # Plant
        "movement_type": row.get('BWART'),  # Movement type (311=WT, 101=GR, etc.)
        "special_stock": row.get('SOBKZ'),  # Special stock indicator
        "valuation_type": row.get('BWTAR'),  # Valuation type
        "stock_type": row.get('INSMK') or 'UNRESTRICTED',  # Stock type
    }


def extract_basic_classification_metadata_oracle(row):
    """
    Extract basic classification metadata from Oracle EBS.

    Oracle Tables:
    - MTL_MATERIAL_TRANSACTIONS: Material transactions
    - MTL_SYSTEM_ITEMS_B: Item master
    - MTL_ITEM_LOCATIONS: Locations
    """
    return {
        # Existing fields
        "material_type": row.get('ITEM_TYPE'),
        "quantity": float(row.get('TRANSACTION_QUANTITY', 0)),
        "unit_price": float(row.get('ACTUAL_COST', 0)),

        # NEW - Phase 1: Basic classification
        "item_id": row.get('INVENTORY_ITEM_ID'),
        "location_code": row.get('LOCATOR_ID'),  # or concatenated LOCATOR_SEGMENT1-2-3
        "plant_code": row.get('ORGANIZATION_ID'),
        "movement_type": row.get('TRANSACTION_TYPE_ID'),  # 62=WT, 18=GR, etc.
        "special_stock": row.get('RESERVATION_ID'),  # If reserved
        "valuation_type": row.get('COST_GROUP_ID'),
        "stock_type": row.get('STATUS_ID'),  # 1=Active, 2=QI, 3=Blocked
    }


# ============================================================================
# PHASE 2: DISTRIBUTION FIELDS (If distribution company)
# ============================================================================

def extract_distribution_metadata_sap(row):
    """
    Add distribution-specific fields for velocity/turns analysis.

    Additional SAP Tables:
    - MARC: Plant data for material
    - MBEW: Material valuation
    """
    basic = extract_basic_classification_metadata_sap(row)

    # Add distribution fields
    basic.update({
        # ABC classification (calculate from consumption/value)
        "abc_classification": calculate_abc_class(
            row.get('MATNR'),
            row.get('WERKS')
        ),

        # Movement class based on turnover
        "movement_class": calculate_movement_class(
            row.get('MATNR'),
            row.get('WERKS')
        ),

        # Gross margin % (from pricing or standard)
        "gross_margin_pct": get_gross_margin_pct(
            row.get('MATNR'),
            row.get('WERKS')
        ),

        # Average monthly demand (calculate from history)
        "avg_monthly_demand": get_avg_monthly_demand(
            row.get('MATNR'),
            row.get('WERKS'),
            months=6
        ),

        # Transfer order number (if warehouse transfer)
        "transfer_order": row.get('TBNUM') if row.get('BWART') in ['311', '313', '314'] else None,
    })

    return basic


def calculate_abc_class(material, plant):
    """
    Calculate ABC classification based on value × consumption.

    Query consumption history and value, then classify:
    - A class: Top 20% of value (80% of total value)
    - B class: Next 30% of items (15% of total value)
    - C class: Remaining 50% of items (5% of total value)
    """
    # TODO: Implement based on your data warehouse
    # For now, return None or default
    return None


def calculate_movement_class(material, plant):
    """
    Calculate movement class based on turnover rate.

    Turnover = Annual consumption / Average inventory
    - FAST: >12 turns/year (monthly turns)
    - MEDIUM: 4-12 turns/year (quarterly turns)
    - SLOW: <4 turns/year
    """
    # TODO: Implement based on your data warehouse
    return None


def get_gross_margin_pct(material, plant):
    """
    Get gross margin % from pricing or standard cost vs selling price.

    Margin % = (Selling Price - Cost) / Selling Price × 100
    """
    # TODO: Query from pricing master or calculate from sales history
    return None


def get_avg_monthly_demand(material, plant, months=6):
    """
    Calculate average monthly demand from consumption history.

    Query last N months of consumption and average.
    """
    # TODO: Query from consumption history
    return None


# ============================================================================
# PHASE 3: MANUFACTURING FIELDS (If manufacturing company)
# ============================================================================

def extract_manufacturing_metadata_sap(row):
    """
    Add manufacturing-specific fields for WIP/bottleneck analysis.

    Additional SAP Tables:
    - AFKO: Order header data
    - AFPO: Order item
    - AFRU: Order confirmations
    - QMEL: Quality notifications
    """
    basic = extract_basic_classification_metadata_sap(row)

    # Add manufacturing fields
    basic.update({
        # Work order number
        "work_order": row.get('AUFNR'),  # Production order

        # Operation sequence (if applicable)
        "operation_seq": row.get('VORNR'),  # Operation number

        # Work center
        "work_center": row.get('ARBPL'),  # Work center

        # Queue quantity (calculate from order confirmations)
        "quantity_in_queue": get_queue_quantity(
            row.get('AUFNR'),
            row.get('VORNR')
        ),

        # QA status (from quality master)
        "qa_status": get_qa_status(row.get('AUFNR')),

        # WIP cost (accumulated costs on order)
        "wip_cost": get_wip_cost(row.get('AUFNR')),
    })

    return basic


def extract_manufacturing_metadata_oracle(row):
    """
    Add manufacturing-specific fields for Oracle EBS.

    Oracle Tables:
    - WIP_DISCRETE_JOBS: Work orders
    - WIP_OPERATIONS: Operations
    - WIP_REQUIREMENT_OPERATIONS: Material requirements
    - BOM_RESOURCES: Work centers
    """
    basic = extract_basic_classification_metadata_oracle(row)

    basic.update({
        # Work order number
        "work_order": row.get('WIP_ENTITY_ID') or row.get('WIP_ENTITY_NAME'),

        # Operation sequence
        "operation_seq": row.get('OPERATION_SEQ_NUM'),

        # Work center/department
        "work_center": row.get('DEPARTMENT_CODE'),

        # Queue quantity
        "quantity_in_queue": row.get('QUANTITY_IN_QUEUE'),

        # QA status
        "qa_status": row.get('QUALITY_STATUS_ID'),  # Map: 1=Released, 2=Hold, etc.

        # WIP cost
        "wip_cost": row.get('APPLIED_MATL_VALUE') or calculate_wip_cost(row.get('WIP_ENTITY_ID')),
    })

    return basic


def get_queue_quantity(order, operation):
    """Get quantity waiting in queue at work center."""
    # TODO: Query from confirmations or shop floor data
    return None


def get_qa_status(order):
    """Get QA status from quality notifications."""
    # TODO: Query from quality management tables
    return None


def get_wip_cost(order):
    """Get accumulated WIP cost for order."""
    # TODO: Query from order costing/settlement
    return None


def calculate_wip_cost(wip_entity_id):
    """Calculate WIP cost from Oracle costing tables."""
    # TODO: Query WIP value from Oracle
    return None


# ============================================================================
# INTEGRATION WITH EXISTING ETL
# ============================================================================

def enhanced_extract_transactions(company_id, erp_system, start_date, end_date):
    """
    Enhanced extraction with business model metadata.

    Updates your existing extract_transactions() function.
    """
    from etl.extractor import extract_transactions  # Your existing function

    # Get raw transactions (your existing logic)
    transactions = extract_transactions(company_id, erp_system, start_date, end_date)

    # Enhance with business model metadata
    for txn in transactions:
        if erp_system == 'SAP':
            # Phase 1: Basic classification
            basic_metadata = extract_basic_classification_metadata_sap(txn)
            txn['erp_metadata'].update(basic_metadata)

            # Phase 2: Detect if distribution (check for warehouse transfers)
            if txn.get('movement_type') in ['311', '313', '314', '315']:
                dist_metadata = extract_distribution_metadata_sap(txn)
                txn['erp_metadata'].update(dist_metadata)

            # Phase 3: Detect if manufacturing (check for work orders)
            if txn.get('work_order'):
                mfg_metadata = extract_manufacturing_metadata_sap(txn)
                txn['erp_metadata'].update(mfg_metadata)

        elif erp_system == 'ORACLE':
            basic_metadata = extract_basic_classification_metadata_oracle(txn)
            txn['erp_metadata'].update(basic_metadata)

            # Similar logic for Oracle distribution/manufacturing detection

    return transactions


# ============================================================================
# TESTING / VALIDATION
# ============================================================================

def validate_metadata_coverage(company_id):
    """
    Test metadata coverage for a company.

    Returns report showing which fields are populated.
    """
    from config.database import get_supabase_client

    db = get_supabase_client()

    # Get sample transactions
    response = db.table('transactions').select(
        'erp_metadata'
    ).eq('company_id', company_id).eq('component_type', 'DIO').limit(100).execute()

    if not response.data:
        return "No DIO transactions found"

    # Count field coverage
    field_counts = {}
    total = len(response.data)

    for txn in response.data:
        metadata = txn.get('erp_metadata', {})
        for key in metadata.keys():
            field_counts[key] = field_counts.get(key, 0) + 1

    # Report
    print(f"\n=== Metadata Coverage for Company {company_id} ===")
    print(f"Total DIO transactions: {total}\n")

    print("PHASE 1 - Basic Classification:")
    phase1_fields = ['item_id', 'location_code', 'plant_code', 'movement_type',
                     'special_stock', 'valuation_type', 'stock_type']
    for field in phase1_fields:
        count = field_counts.get(field, 0)
        pct = (count / total * 100) if total > 0 else 0
        status = "✅" if pct > 80 else "⚠️" if pct > 50 else "❌"
        print(f"  {status} {field}: {count}/{total} ({pct:.0f}%)")

    print("\nPHASE 2 - Distribution:")
    phase2_fields = ['abc_classification', 'movement_class', 'gross_margin_pct',
                     'avg_monthly_demand', 'transfer_order']
    for field in phase2_fields:
        count = field_counts.get(field, 0)
        pct = (count / total * 100) if total > 0 else 0
        status = "✅" if pct > 80 else "⚠️" if pct > 50 else "❌"
        print(f"  {status} {field}: {count}/{total} ({pct:.0f}%)")

    print("\nPHASE 3 - Manufacturing:")
    phase3_fields = ['work_order', 'operation_seq', 'work_center',
                     'quantity_in_queue', 'qa_status', 'wip_cost']
    for field in phase3_fields:
        count = field_counts.get(field, 0)
        pct = (count / total * 100) if total > 0 else 0
        status = "✅" if pct > 80 else "⚠️" if pct > 50 else "❌"
        print(f"  {status} {field}: {count}/{total} ({pct:.0f}%)")

    # Classification prediction
    print("\n=== Classification Prediction ===")
    has_transfers = field_counts.get('transfer_order', 0) > total * 0.1
    has_work_orders = field_counts.get('work_order', 0) > total * 0.1

    if has_transfers and not has_work_orders:
        print("Likely: DISTRIBUTION")
    elif has_work_orders and not has_transfers:
        print("Likely: MANUFACTURING")
    elif has_transfers and has_work_orders:
        print("Likely: HYBRID")
    else:
        print("Unknown: Need Phase 1 fields to classify")


if __name__ == "__main__":
    # Test metadata coverage for a company
    validate_metadata_coverage('your-company-id-here')
