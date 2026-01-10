# WCSearch Business Model Refactoring Guide

## Overview

This document describes the business model classification refactoring implemented on 2026-01-10. The system now distinguishes between **Distribution** and **Manufacturing** business models, with separate calculation logic and cash impact methodologies for each.

## Problem Statement

The original system incorrectly applied uniform calculations across all business types, leading to misleading cash recovery estimates:

- **Distribution reality**: $7.7M inventory delayed 7 days → Lost turns → $6.9M annual margin opportunity
- **Manufacturing reality**: $7.7M WIP delayed 7 days → Carrying cost + delayed revenue → $60K + revenue delay impact
- **Wrong approach**: Treating both the same = lost credibility with clients

## Business Model Differences

### DISTRIBUTION
- **Business model**: Buy → Move → Sell (velocity is everything)
- **Thin margins**: 8-15% gross margin typical
- **Success metric**: Inventory turns (12-24x annually)
- **Cash trap**: MOVEMENT delays kill margins
- **Recovery calculation**: Lost turns × Inventory value × Margin %

### MANUFACTURING
- **Business model**: Buy → Transform → Sell (value creation on shop floor)
- **Better margins**: 25-40% gross margin typical
- **Success metric**: Production efficiency, yield, throughput
- **Cash trap**: TRANSFORMATION delays, WIP bottlenecks, scrap/rework
- **Recovery calculation**: Carrying costs + throughput delays + variance costs

---

## Architecture Changes

### 1. Database Schema

Run the migration to add new tables:

```bash
psql -U postgres -d wcsearch -f database/migrations/001_add_business_model_classification.sql
```

**New Tables:**
- `company_classification` - Business model classification with evidence scores
- `dio_distribution_analysis` - Distribution-specific DIO metrics
- `dio_manufacturing_analysis` - Manufacturing-specific DIO metrics
- Detail tables for drill-down (velocity, movement, bottlenecks, QA, etc.)

**Modified Tables:**
- Added `business_model` column to `component_details`, `trapped_cash_analysis`, `transactions`

### 2. Module Structure

```
wcsearch/
├── classification/
│   ├── __init__.py
│   └── business_model_detector.py      # Auto-detect Distribution vs Manufacturing
│
├── metrics/
│   ├── __init__.py
│   └── dio/
│       ├── __init__.py
│       ├── dio_router.py               # Main entry point - routes by business model
│       │
│       ├── distribution/
│       │   ├── __init__.py
│       │   ├── velocity_analysis.py         # Inventory turns analysis
│       │   ├── movement_bottlenecks.py      # Cross-dock, WT, putaway delays
│       │   └── cash_impact.py               # Lost turns × margin calculation
│       │
│       └── manufacturing/
│           ├── __init__.py
│           ├── wip_bottleneck_analysis.py   # Work center queue analysis
│           ├── qa_delay_analysis.py         # QA hold impact
│           └── cash_impact.py               # Carrying cost + throughput
```

---

## Usage Guide

### Step 1: Classify a Company

```python
from classification import BusinessModelDetector
from config.database import get_supabase_client

# Initialize
db = get_supabase_client()
detector = BusinessModelDetector(db)

# Classify company
business_model, confidence, evidence = detector.classify(company_id)

print(f"Business Model: {business_model}")
print(f"Confidence: {confidence:.2f}")
print(f"Distribution Score: {evidence.distribution_score}")
print(f"Manufacturing Score: {evidence.manufacturing_score}")

# Save classification
detector.save_classification(
    company_id,
    business_model,
    confidence,
    evidence,
    method='AUTOMATIC'
)
```

### Step 2: Run DIO Analysis (Automatic Routing)

```python
from metrics.dio.dio_router import DIOAnalysisRouter

# Initialize router
router = DIOAnalysisRouter(db)

# Run analysis (automatically routes based on business model)
results = router.analyze(company_id)

print(f"Analysis Type: {results['analysis_type']}")
print(f"Total Cash Impact: ${results['cash_impact']['total_cash_impact']:,.0f}")

# Access business model-specific results
if results['analysis_type'] == 'DISTRIBUTION':
    velocity = results['results']['velocity']
    print(f"Velocity Issues: {velocity['summary']['total_issues']}")
    print(f"Lost Turns: {velocity['summary']['total_lost_turns']:.1f}")

elif results['analysis_type'] == 'MANUFACTURING':
    wip = results['results']['wip_bottlenecks']
    print(f"WIP Bottlenecks: {wip['summary']['total_bottlenecks']}")
    print(f"Carrying Cost: ${wip['summary']['total_carrying_cost']:,.0f}")
```

### Step 3: Force Reclassification

```python
# Force reclassification (useful after data changes)
results = router.analyze(company_id, force_reclassify=True)
```

### Step 4: Manual Override

```python
# Override automatic classification
detector.save_classification(
    company_id,
    business_model='MANUFACTURING',
    confidence=1.0,
    evidence=None,
    method='MANUAL_OVERRIDE',
    notes='PE firm confirmed this is a contract manufacturer'
)
```

---

## Classification Logic

### Automatic Detection

The `BusinessModelDetector` uses multiple signals:

**Distribution Signals (+points):**
- COGS from purchased goods (GL 5000-5999)
- High warehouse transfer volume (>100 in 3 months)
- Cross-dock staging locations
- Multi-warehouse operations

**Manufacturing Signals (+points):**
- COGS from labor/overhead (GL 6000-6999)
- WIP inventory accounts (GL 1400-1499)
- Production orders / work orders
- Manufacturing variance accounts
- Routing operations

**Confidence Thresholds:**
- ≥0.70: Automatic classification accepted
- <0.70: Falls back to generic time-state analysis (or manual review recommended)

### Classification Criteria

```
If Distribution Score / Manufacturing Score > 1.5:
    → DISTRIBUTION (confidence based on ratio)

If Manufacturing Score / Distribution Score > 1.5:
    → MANUFACTURING (confidence based on ratio)

Else:
    → HYBRID (confidence = 0.60)
```

---

## Cash Impact Methodologies

### Distribution Cash Impact

**Formula:**
```
Lost Turns × Inventory Value × Gross Margin %
```

**Components:**
1. **Velocity Issues**: Items turning slower than expected
   - Expected: 12x/year (30 days)
   - Actual: 8x/year (45 days)
   - Lost turns: 4x/year
   - Impact: $100K × 4 turns × 12% = $48K/year

2. **Movement Bottlenecks**: Cross-dock, WT, putaway delays
   - Expected: <4 hours in cross-dock
   - Actual: 7 days in cross-dock
   - Lost turns: 0.19x
   - Impact: $50K × 0.19 turns × 12% = $1.1K

3. **Excess Inventory**: Carrying costs only
   - Impact: $200K × 20% carrying cost = $40K/year

### Manufacturing Cash Impact

**Formula:**
```
Carrying Costs + Throughput Impact
```

**Components:**
1. **WIP Bottlenecks**: Queue delays
   - WIP value: $500K
   - Days delayed: 10 days
   - Carrying cost: $500K × 10 × (12%/365) = $1,644
   - Throughput impact: $500K × 20% = $100K
   - Total: $101,644

2. **QA Delays**: Quality hold
   - WIP value: $200K
   - Days on hold: 5 days
   - Carrying cost: $200K × 5 × (12%/365) = $329
   - Throughput impact: $200K × 15% = $30K
   - Total: $30,329

3. **Yield Losses**: Scrap and rework (direct costs)

4. **Variances**: Material, labor, overhead unfavorable variances

---

## Testing

### Test with Synthetic Data

```python
# Generate test company data
from scripts.generate_synthetic_data import generate_distribution_company, generate_manufacturing_company

# Generate distribution company
dist_company_id = generate_distribution_company(
    db,
    warehouse_transfer_count=500,
    cross_dock_transactions=200
)

# Generate manufacturing company
mfg_company_id = generate_manufacturing_company(
    db,
    work_order_count=300,
    wip_value=2000000
)

# Test classification
dist_result = detector.classify(dist_company_id)
print(f"Distribution: {dist_result}")  # Should be DISTRIBUTION with high confidence

mfg_result = detector.classify(mfg_company_id)
print(f"Manufacturing: {mfg_result}")  # Should be MANUFACTURING with high confidence
```

### Validate Results

```python
# Run analysis on both
dist_analysis = router.analyze(dist_company_id)
mfg_analysis = router.analyze(mfg_company_id)

# Check that methodology differs
assert dist_analysis['cash_impact']['methodology'] == 'DISTRIBUTION'
assert mfg_analysis['cash_impact']['methodology'] == 'MANUFACTURING'

# Check calculation notes
print(dist_analysis['methodology_note'])  # Should mention "lost turns"
print(mfg_analysis['methodology_note'])   # Should mention "carrying costs"
```

---

## Migration Checklist

For existing deployments:

- [ ] Run database migration script
- [ ] Classify all existing companies (`detector.classify(company_id)` for each)
- [ ] Review low-confidence classifications (<0.70) for manual override
- [ ] Re-run DIO analysis for all companies using `router.analyze()`
- [ ] Update dashboard to show business model-specific results
- [ ] Update PDF reports to use correct framing ("lost turns" vs "carrying costs")
- [ ] Train team on new terminology and methodologies

---

## Dashboard Integration

Update `app/main.py` to use the new router:

```python
from metrics.dio.dio_router import DIOAnalysisRouter

# In DIO analysis section
router = DIOAnalysisRouter(st.session_state.supabase)
results = router.analyze(company_id)

# Display business model classification
st.info(f"Business Model: {results['business_model']} (confidence: {results['classification_confidence']:.0%})")

# Show appropriate visualizations based on analysis type
if results['analysis_type'] == 'DISTRIBUTION':
    # Show velocity charts, turns analysis
    display_distribution_dashboard(results['results'])

elif results['analysis_type'] == 'MANUFACTURING':
    # Show WIP queues, throughput charts
    display_manufacturing_dashboard(results['results'])
```

---

## Troubleshooting

### Low Classification Confidence

If confidence < 0.70:

1. **Check data completeness**: Ensure GL accounts, transactions, event logs are populated
2. **Review metadata**: Check that erp_metadata includes relevant fields
3. **Manual override**: If you know the business model, use manual classification
4. **Use generic analysis**: Falls back automatically if `fallback_to_generic=True`

### Incorrect Classification

If auto-classification is wrong:

```python
# Manual override
detector.save_classification(
    company_id,
    business_model='DISTRIBUTION',  # or 'MANUFACTURING'
    confidence=1.0,
    evidence=None,
    method='MANUAL_OVERRIDE',
    notes='Confirmed with client - distribution business'
)
```

### Missing Data

Distribution analysis requires:
- Inventory transactions with `days_outstanding`
- ERP metadata with location codes, item classifications
- Optional: Warehouse transfer records, cross-dock indicators

Manufacturing analysis requires:
- Inventory transactions with work order indicators
- ERP metadata with operation sequences, work centers
- Optional: QA status, material status, routing data

---

## Performance Considerations

- **Classification caching**: Classifications are cached in `company_classification` table
- **Batch analysis**: For multiple companies, use batch operations
- **Incremental updates**: Only reclassify if data has changed significantly

---

## Future Enhancements

Potential improvements:

1. **Hybrid business models**: Better handling of companies with both distribution and manufacturing
2. **Industry-specific benchmarks**: Pharma, electronics, apparel have different profiles
3. **Time-series classification**: Detect business model changes over time
4. **Machine learning**: Train classifier on labeled dataset
5. **Stockout analysis**: Add stockout detection for distribution (mentioned in spec but not implemented)
6. **Yield analysis**: Detailed scrap/rework tracking for manufacturing (mentioned in spec but simplified)

---

## Support

For questions or issues:

1. Check logs: `logger.info` statements throughout the code
2. Review classification evidence: `detector.get_classification(company_id)`
3. Test with synthetic data first
4. File issues on GitHub

---

## References

- Original prompt: See comprehensive requirements in project documentation
- Database schema: `database/migrations/001_add_business_model_classification.sql`
- Code modules: `classification/`, `metrics/dio/distribution/`, `metrics/dio/manufacturing/`
