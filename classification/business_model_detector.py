"""
Business model classification logic.

Auto-detects whether a company is Distribution, Manufacturing, or Hybrid
based on GL account patterns, transaction types, and ERP data signatures.
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ClassificationEvidence:
    """Stores evidence scores and flags for classification"""
    distribution_score: int = 0
    manufacturing_score: int = 0

    # Evidence flags - Distribution signals
    has_cross_dock: bool = False
    has_warehouse_transfers: bool = False
    cross_dock_transaction_count: int = 0
    warehouse_transfer_volume: int = 0

    # Evidence flags - Manufacturing signals
    has_work_orders: bool = False
    has_wip_accounts: bool = False
    has_routing_operations: bool = False
    has_manufacturing_variances: bool = False
    production_order_volume: int = 0

    # COGS composition
    purchased_cogs_pct: float = 0.0
    manufactured_cogs_pct: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        return asdict(self)


class BusinessModelDetector:
    """
    Detects whether company is Distribution or Manufacturing.

    Scoring methodology:
    - Distribution indicators: Cross-dock locations, high WT volume,
      COGS primarily from purchases (GL 5000-5999), minimal mfg expense accounts
    - Manufacturing indicators: WIP accounts, production orders, routing operations,
      COGS from labor/overhead (GL 6000-6999), variance accounts

    Confidence threshold: >70% confidence required for automatic classification
    """

    def __init__(self, db_client):
        """
        Initialize detector with database client.

        Args:
            db_client: Supabase client or database connection
        """
        self.db = db_client
        self.evidence = ClassificationEvidence()

    def classify(self, company_id: str) -> Tuple[str, float, ClassificationEvidence]:
        """
        Main classification method.

        Args:
            company_id: UUID of company to classify

        Returns:
            Tuple of (business_model, confidence, evidence)
            business_model: 'DISTRIBUTION', 'MANUFACTURING', 'HYBRID', or 'UNKNOWN'
            confidence: 0.0 to 1.0
            evidence: ClassificationEvidence object with all scores
        """
        # Reset evidence
        self.evidence = ClassificationEvidence()

        logger.info(f"Starting business model classification for company {company_id}")

        # Run all detection checks
        self._check_gl_account_patterns(company_id)
        self._check_transaction_patterns(company_id)
        self._check_erp_metadata_signals(company_id)

        # Calculate final scores and confidence
        result = self._calculate_classification()

        logger.info(
            f"Classification complete for {company_id}: "
            f"{result[0]} (confidence: {result[1]:.2f})"
        )

        return result

    def _check_gl_account_patterns(self, company_id: str):
        """
        Analyze GL account structure to identify business model.

        Distribution signals:
        - COGS accounts in 5000-5999 range (purchased inventory)
        - Minimal labor/overhead expense accounts

        Manufacturing signals:
        - COGS accounts in 6000-6999 range (labor, overhead, variances)
        - WIP inventory accounts (1400-1499 typical)
        - Variance accounts (material, labor, overhead)
        """
        try:
            # Query component_details for GL account patterns
            response = self.db.table('component_details').select(
                'gl_account, gl_account_name, amount'
            ).eq('company_id', company_id).execute()

            if not response.data:
                logger.warning(f"No GL account data found for company {company_id}")
                return

            # Analyze COGS composition
            purchased_cogs = 0.0
            manufactured_cogs = 0.0
            has_wip = False
            has_variance = False

            for record in response.data:
                gl_account = record.get('gl_account', '')
                gl_name = (record.get('gl_account_name') or '').lower()
                amount = abs(float(record.get('amount', 0)))

                # Check for purchased COGS (5000-5999)
                if gl_account.startswith('5') and len(gl_account) == 4:
                    purchased_cogs += amount

                # Check for manufactured COGS (6000-6999)
                elif gl_account.startswith('6') and len(gl_account) == 4:
                    manufactured_cogs += amount

                # Check for WIP accounts (1400-1499)
                elif gl_account.startswith('14') and len(gl_account) == 4:
                    has_wip = True
                    self.evidence.has_wip_accounts = True
                    self.evidence.manufacturing_score += 3

                # Check for variance accounts
                elif any(keyword in gl_name for keyword in ['variance', 'var ', 'mfg var']):
                    has_variance = True
                    self.evidence.has_manufacturing_variances = True
                    self.evidence.manufacturing_score += 2

            # Calculate COGS composition percentages
            total_cogs = purchased_cogs + manufactured_cogs
            if total_cogs > 0:
                self.evidence.purchased_cogs_pct = (purchased_cogs / total_cogs) * 100
                self.evidence.manufactured_cogs_pct = (manufactured_cogs / total_cogs) * 100

                # Score based on COGS composition
                if self.evidence.purchased_cogs_pct > 80:
                    self.evidence.distribution_score += 3
                elif self.evidence.purchased_cogs_pct > 60:
                    self.evidence.distribution_score += 2

                if self.evidence.manufactured_cogs_pct > 40:
                    self.evidence.manufacturing_score += 3
                elif self.evidence.manufactured_cogs_pct > 20:
                    self.evidence.manufacturing_score += 2

                logger.debug(
                    f"COGS composition - Purchased: {self.evidence.purchased_cogs_pct:.1f}%, "
                    f"Manufactured: {self.evidence.manufactured_cogs_pct:.1f}%"
                )

        except Exception as e:
            logger.error(f"Error analyzing GL account patterns: {e}")

    def _check_transaction_patterns(self, company_id: str):
        """
        Analyze transaction volume patterns via ERP metadata.

        High warehouse transfer volume → Distribution
        High production order volume → Manufacturing
        """
        try:
            # Query transactions for ERP metadata patterns
            response = self.db.table('transactions').select(
                'erp_metadata, component_type'
            ).eq('company_id', company_id).limit(1000).execute()

            if not response.data:
                logger.warning(f"No transaction data found for company {company_id}")
                return

            warehouse_transfer_count = 0
            production_order_count = 0
            cross_dock_count = 0

            for record in response.data:
                metadata = record.get('erp_metadata', {})
                if not metadata:
                    continue

                # Check for warehouse transfer indicators
                if any(key in metadata for key in [
                    'transfer_order', 'warehouse_transfer', 'wt_number',
                    'from_warehouse', 'to_warehouse'
                ]):
                    warehouse_transfer_count += 1

                # Check for production order indicators
                if any(key in metadata for key in [
                    'work_order', 'production_order', 'job_number',
                    'manufacturing_order', 'shop_order'
                ]):
                    production_order_count += 1

                # Check for cross-dock indicators
                if any(key in metadata for key in [
                    'cross_dock', 'xdock', 'staging_location'
                ]):
                    cross_dock_count += 1
                    self.evidence.has_cross_dock = True

                # Check location codes in metadata
                location = metadata.get('location_code', '').upper()
                if 'XDOCK' in location or 'CROSS' in location:
                    cross_dock_count += 1
                    self.evidence.has_cross_dock = True

            # Update evidence
            self.evidence.warehouse_transfer_volume = warehouse_transfer_count
            self.evidence.production_order_volume = production_order_count
            self.evidence.cross_dock_transaction_count = cross_dock_count

            # Score based on transaction volumes
            if warehouse_transfer_count > 100:
                self.evidence.has_warehouse_transfers = True
                self.evidence.distribution_score += 2
            elif warehouse_transfer_count > 30:
                self.evidence.has_warehouse_transfers = True
                self.evidence.distribution_score += 1

            if production_order_count > 50:
                self.evidence.has_work_orders = True
                self.evidence.manufacturing_score += 3
            elif production_order_count > 10:
                self.evidence.has_work_orders = True
                self.evidence.manufacturing_score += 2

            if cross_dock_count > 20:
                self.evidence.distribution_score += 2

            logger.debug(
                f"Transaction patterns - WT: {warehouse_transfer_count}, "
                f"PO: {production_order_count}, XD: {cross_dock_count}"
            )

        except Exception as e:
            logger.error(f"Error analyzing transaction patterns: {e}")

    def _check_erp_metadata_signals(self, company_id: str):
        """
        Check ERP-specific metadata for business model signals.

        Manufacturing signals:
        - Routing operations
        - Work center codes
        - Operation sequences
        - BOM references

        Distribution signals:
        - Cross-dock staging
        - Transfer orders
        - Multi-warehouse references
        """
        try:
            # Query event logs for ERP-specific signals
            response = self.db.table('event_logs').select(
                'event_type, event_data, module'
            ).eq('company_id', company_id).limit(500).execute()

            if not response.data:
                logger.warning(f"No event log data found for company {company_id}")
                return

            routing_operations = 0
            work_center_refs = 0

            for record in response.data:
                event_type = (record.get('event_type') or '').upper()
                module = (record.get('module') or '').upper()
                event_data = record.get('event_data', {})

                # Manufacturing signals
                if any(keyword in event_type for keyword in [
                    'ROUTING', 'OPERATION', 'WORK_CENTER', 'BOM'
                ]):
                    routing_operations += 1

                if any(keyword in module for keyword in [
                    'PRODUCTION', 'MANUFACTURING', 'WIP', 'SHOP_FLOOR'
                ]):
                    self.evidence.manufacturing_score += 1

                # Check event data for work center references
                if event_data:
                    if any(key in event_data for key in [
                        'work_center', 'operation_seq', 'routing_seq'
                    ]):
                        work_center_refs += 1

                # Distribution signals
                if any(keyword in module for keyword in [
                    'WAREHOUSE', 'DISTRIBUTION', 'LOGISTICS'
                ]):
                    self.evidence.distribution_score += 1

            # Score based on manufacturing signals
            if routing_operations > 10 or work_center_refs > 10:
                self.evidence.has_routing_operations = True
                self.evidence.manufacturing_score += 2

            logger.debug(
                f"ERP metadata - Routing ops: {routing_operations}, "
                f"Work center refs: {work_center_refs}"
            )

        except Exception as e:
            logger.error(f"Error analyzing ERP metadata: {e}")

    def _calculate_classification(self) -> Tuple[str, float, ClassificationEvidence]:
        """
        Calculate final classification and confidence score.

        Confidence calculation:
        - If one score is 2x the other → High confidence (0.80-0.95)
        - If one score is 1.5x the other → Medium confidence (0.70-0.80)
        - If scores are close → Low confidence (0.50-0.70)
        - Require minimum score of 3 for any classification
        """
        dist_score = self.evidence.distribution_score
        mfg_score = self.evidence.manufacturing_score
        total_score = dist_score + mfg_score

        logger.debug(
            f"Final scores - Distribution: {dist_score}, "
            f"Manufacturing: {mfg_score}, Total: {total_score}"
        )

        # Need minimum evidence
        if total_score < 3:
            logger.warning("Insufficient evidence for classification")
            return ('UNKNOWN', 0.0, self.evidence)

        # Calculate score ratio
        if mfg_score == 0:
            ratio = float('inf')
        else:
            ratio = dist_score / mfg_score

        # Determine classification
        if ratio > 1.5:  # Distribution dominant
            business_model = 'DISTRIBUTION'
            if ratio > 2.0:
                confidence = min(0.95, 0.70 + (ratio - 2.0) * 0.1)
            else:
                confidence = 0.70 + (ratio - 1.5) * 0.2
        elif ratio < 0.67:  # Manufacturing dominant (1/1.5)
            business_model = 'MANUFACTURING'
            inv_ratio = mfg_score / dist_score if dist_score > 0 else mfg_score
            if inv_ratio > 2.0:
                confidence = min(0.95, 0.70 + (inv_ratio - 2.0) * 0.1)
            else:
                confidence = 0.70 + (inv_ratio - 1.5) * 0.2
        else:  # Close scores → Hybrid
            business_model = 'HYBRID'
            confidence = 0.60  # Lower confidence for hybrid classification

        return (business_model, confidence, self.evidence)

    def save_classification(
        self,
        company_id: str,
        business_model: str,
        confidence: float,
        evidence: ClassificationEvidence,
        method: str = 'AUTOMATIC',
        notes: Optional[str] = None
    ) -> bool:
        """
        Save classification results to database.

        Args:
            company_id: UUID of company
            business_model: Classification result
            confidence: Confidence score
            evidence: ClassificationEvidence object
            method: 'AUTOMATIC' or 'MANUAL_OVERRIDE'
            notes: Optional notes

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            data = {
                'company_id': company_id,
                'business_model': business_model,
                'classification_confidence': confidence,
                'classification_method': method,
                'distribution_score': evidence.distribution_score,
                'manufacturing_score': evidence.manufacturing_score,
                'has_cross_dock': evidence.has_cross_dock,
                'has_warehouse_transfers': evidence.has_warehouse_transfers,
                'cross_dock_transaction_count': evidence.cross_dock_transaction_count,
                'warehouse_transfer_volume': evidence.warehouse_transfer_volume,
                'has_work_orders': evidence.has_work_orders,
                'has_wip_accounts': evidence.has_wip_accounts,
                'has_routing_operations': evidence.has_routing_operations,
                'has_manufacturing_variances': evidence.has_manufacturing_variances,
                'production_order_volume': evidence.production_order_volume,
                'purchased_cogs_pct': evidence.purchased_cogs_pct,
                'manufactured_cogs_pct': evidence.manufactured_cogs_pct,
                'notes': notes
            }

            # Upsert classification (insert or update if exists)
            response = self.db.table('company_classification').upsert(
                data,
                on_conflict='company_id'
            ).execute()

            logger.info(f"Classification saved for company {company_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving classification: {e}")
            return False

    def get_classification(self, company_id: str) -> Optional[Dict]:
        """
        Retrieve existing classification from database.

        Args:
            company_id: UUID of company

        Returns:
            Classification dict or None if not found
        """
        try:
            response = self.db.table('company_classification').select(
                '*'
            ).eq('company_id', company_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error retrieving classification: {e}")
            return None
