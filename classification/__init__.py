"""
Business model classification module.

Automatically detects whether a company is Distribution, Manufacturing, or Hybrid
based on GL account patterns, transaction types, and ERP data signatures.
"""

from .business_model_detector import BusinessModelDetector, ClassificationEvidence

__all__ = ['BusinessModelDetector', 'ClassificationEvidence']
