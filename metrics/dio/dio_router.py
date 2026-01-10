"""
DIO Analysis Router

Routes DIO analysis to the appropriate business model-specific module:
- Distribution: Velocity/turns, movement bottlenecks
- Manufacturing: WIP bottlenecks, QA delays, throughput
- Unknown/HYBRID: Falls back to generic time-state analysis

This module acts as the main entry point for all DIO analysis.
"""

from typing import Dict, Optional
import logging

# Import business model detector
from classification.business_model_detector import BusinessModelDetector

# Import distribution modules
from metrics.dio.distribution import (
    VelocityAnalyzer,
    MovementBottleneckAnalyzer,
    DistributionCashImpact
)

# Import manufacturing modules
from metrics.dio.manufacturing import (
    WIPBottleneckAnalyzer,
    QADelayAnalyzer,
    ManufacturingCashImpact
)

logger = logging.getLogger(__name__)


class DIOAnalysisRouter:
    """
    Routes DIO analysis to appropriate business model-specific logic.

    Workflow:
    1. Check if company has business model classification
    2. If not classified, auto-classify using BusinessModelDetector
    3. Route to distribution or manufacturing analysis based on classification
    4. Fall back to generic time-state analysis if classification confidence is low
    """

    def __init__(self, db_client):
        """
        Initialize router with database client.

        Args:
            db_client: Supabase client
        """
        self.db = db_client
        self.detector = BusinessModelDetector(db_client)

    def analyze(
        self,
        company_id: str,
        force_reclassify: bool = False,
        fallback_to_generic: bool = True
    ) -> Dict:
        """
        Main analysis entry point.

        Args:
            company_id: UUID of company to analyze
            force_reclassify: If True, reclassify even if classification exists
            fallback_to_generic: If True, fall back to generic analysis for low confidence

        Returns:
            dict with:
            - business_model: Detected business model
            - classification_confidence: Confidence score
            - analysis_type: 'DISTRIBUTION', 'MANUFACTURING', or 'GENERIC'
            - results: Analysis results specific to business model
            - cash_impact: Total cash impact summary
        """
        logger.info(f"Starting DIO analysis for company {company_id}")

        # Step 1: Get or create business model classification
        classification = self._get_or_create_classification(
            company_id,
            force_reclassify
        )

        business_model = classification['business_model']
        confidence = classification['confidence']

        logger.info(
            f"Company {company_id} classified as {business_model} "
            f"(confidence: {confidence:.2f})"
        )

        # Step 2: Route to appropriate analysis based on classification
        if business_model == 'DISTRIBUTION' and confidence >= 0.70:
            results = self._analyze_distribution(company_id)
            analysis_type = 'DISTRIBUTION'

        elif business_model == 'MANUFACTURING' and confidence >= 0.70:
            results = self._analyze_manufacturing(company_id)
            analysis_type = 'MANUFACTURING'

        elif fallback_to_generic:
            logger.warning(
                f"Low confidence ({confidence:.2f}) or HYBRID/UNKNOWN classification. "
                f"Falling back to generic time-state analysis."
            )
            results = self._analyze_generic(company_id)
            analysis_type = 'GENERIC'

        else:
            raise ValueError(
                f"Cannot analyze company {company_id}: "
                f"Business model {business_model} with confidence {confidence:.2f} "
                f"is below threshold and fallback is disabled"
            )

        # Step 3: Format response
        return {
            'company_id': company_id,
            'business_model': business_model,
            'classification_confidence': confidence,
            'analysis_type': analysis_type,
            'classification_evidence': classification.get('evidence'),
            'results': results,
            'cash_impact': results.get('cash_impact', {}),
            'methodology_note': self._get_methodology_note(analysis_type)
        }

    def _get_or_create_classification(
        self,
        company_id: str,
        force_reclassify: bool = False
    ) -> Dict:
        """
        Get existing classification or create new one.

        Args:
            company_id: UUID of company
            force_reclassify: If True, reclassify even if exists

        Returns:
            dict with business_model, confidence, evidence
        """
        # Check if classification already exists
        if not force_reclassify:
            existing = self.detector.get_classification(company_id)
            if existing:
                return {
                    'business_model': existing['business_model'],
                    'confidence': existing['classification_confidence'],
                    'evidence': None  # Not stored in simplified format
                }

        # Classify company
        business_model, confidence, evidence = self.detector.classify(company_id)

        # Save classification to database
        self.detector.save_classification(
            company_id,
            business_model,
            confidence,
            evidence,
            method='AUTOMATIC'
        )

        return {
            'business_model': business_model,
            'confidence': confidence,
            'evidence': evidence
        }

    def _analyze_distribution(self, company_id: str) -> Dict:
        """
        Run distribution-specific DIO analysis.

        Focus on:
        - Inventory velocity and turns
        - Movement bottlenecks (cross-dock, WT, putaway)
        - Cash impact = Lost turns × Inventory value × Gross margin %
        """
        logger.info(f"Running DISTRIBUTION analysis for {company_id}")

        # Initialize analyzers
        velocity_analyzer = VelocityAnalyzer(self.db)
        movement_analyzer = MovementBottleneckAnalyzer(self.db)
        cash_calculator = DistributionCashImpact(self.db)

        # Run analyses
        velocity_results = velocity_analyzer.analyze(company_id)
        movement_results = movement_analyzer.analyze(company_id)

        # Calculate total cash impact
        cash_impact = cash_calculator.calculate_total_impact(
            company_id,
            velocity_results,
            movement_results
        )

        # Save to database
        # Create main analysis record
        analysis_data = {
            'company_id': company_id,
            'velocity_issues_count': velocity_results['summary']['total_issues'],
            'velocity_inventory_value': velocity_results['summary']['total_inventory_value'],
            'velocity_lost_turns': velocity_results['summary']['total_lost_turns'],
            'velocity_cash_impact': velocity_results['summary']['total_cash_impact_annual']
        }

        response = self.db.table('dio_distribution_analysis').insert(
            analysis_data
        ).execute()

        if response.data:
            analysis_id = response.data[0]['analysis_id']

            # Save velocity details
            velocity_analyzer.save_to_database(
                company_id,
                velocity_results['issues'],
                velocity_results['summary']
            )

            # Save cash impact
            cash_calculator.save_to_database(company_id, analysis_id, cash_impact)

        return {
            'velocity': velocity_results,
            'movement': movement_results,
            'cash_impact': cash_impact
        }

    def _analyze_manufacturing(self, company_id: str) -> Dict:
        """
        Run manufacturing-specific DIO analysis.

        Focus on:
        - WIP bottlenecks (queue delays, capacity constraints)
        - QA delays (quality hold impact)
        - Cash impact = Carrying costs + Throughput delays
        """
        logger.info(f"Running MANUFACTURING analysis for {company_id}")

        # Initialize analyzers
        wip_analyzer = WIPBottleneckAnalyzer(self.db)
        qa_analyzer = QADelayAnalyzer(self.db)
        cash_calculator = ManufacturingCashImpact(self.db)

        # Run analyses
        wip_results = wip_analyzer.analyze(company_id)
        qa_results = qa_analyzer.analyze(company_id)

        # Calculate total cash impact
        cash_impact = cash_calculator.calculate_total_impact(
            company_id,
            wip_results,
            qa_results
        )

        # Save to database
        # Create main analysis record
        analysis_data = {
            'company_id': company_id,
            'bottleneck_operations_count': wip_results['summary']['total_bottlenecks'],
            'bottleneck_wip_value': wip_results['summary']['total_wip_value'],
            'bottleneck_avg_queue_days': wip_results['summary']['avg_queue_days'],
            'bottleneck_carrying_cost': wip_results['summary']['total_carrying_cost'],
            'bottleneck_throughput_impact': wip_results['summary']['total_throughput_impact']
        }

        response = self.db.table('dio_manufacturing_analysis').insert(
            analysis_data
        ).execute()

        if response.data:
            analysis_id = response.data[0]['analysis_id']

            # Save cash impact
            cash_calculator.save_to_database(company_id, analysis_id, cash_impact)

        return {
            'wip_bottlenecks': wip_results,
            'qa_delays': qa_results,
            'cash_impact': cash_impact
        }

    def _analyze_generic(self, company_id: str) -> Dict:
        """
        Fall back to generic time-state analysis.

        Uses existing DIO time-state classification from utils/dio_analysis.py
        """
        logger.info(f"Running GENERIC time-state analysis for {company_id}")

        # Import existing time-state analysis
        from utils.dio_analysis import analyze_dio_time_states

        # Run time-state analysis
        time_state_results = analyze_dio_time_states(company_id, self.db)

        return {
            'time_states': time_state_results,
            'cash_impact': {
                'total_cash_impact': sum(
                    state.get('total_amount', 0)
                    for state in time_state_results.values()
                ),
                'methodology': 'GENERIC',
                'calculation_note': 'Generic time-state analysis used due to low classification confidence'
            }
        }

    def _get_methodology_note(self, analysis_type: str) -> str:
        """Get methodology explanation for analysis type"""
        notes = {
            'DISTRIBUTION': (
                'Distribution analysis focuses on inventory velocity and turn opportunities. '
                'Cash impact = Lost turns × Inventory value × Gross margin %. '
                'Every day inventory sits idle is a lost opportunity to turn that inventory into margin.'
            ),
            'MANUFACTURING': (
                'Manufacturing analysis focuses on WIP carrying costs and throughput delays. '
                'Cash impact = Carrying costs (WIP × Days × WACC/365) + Throughput impact. '
                'WIP sitting in queues or on QA hold incurs carrying costs and delays revenue.'
            ),
            'GENERIC': (
                'Generic time-state analysis used due to insufficient business model classification confidence. '
                'Classifies inventory into 6 time states based on status and event logs.'
            )
        }
        return notes.get(analysis_type, '')
