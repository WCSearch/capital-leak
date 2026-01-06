"""
Test script for trapped cash calculations
Tests with sample data from Acme Industrial Supply
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.trapped_cash import calculate_trapped_cash, format_currency, format_percentage

# Test data: Acme Industrial Supply
test_data = {
    'revenue_annual': 50_000_000,  # $50M
    'actual_dso': 73.2,  # days
    'actual_dio': 55.8,  # days
    'actual_dpo': 40.5   # days
}

print("=" * 70)
print("TRAPPED CASH ANALYSIS TEST")
print("=" * 70)
print(f"\nTest Company: Acme Industrial Supply")
print(f"Annual Revenue: {format_currency(test_data['revenue_annual'])}")
print(f"DSO: {test_data['actual_dso']:.1f} days")
print(f"DIO: {test_data['actual_dio']:.1f} days")
print(f"DPO: {test_data['actual_dpo']:.1f} days")
print()

# Run calculation
result = calculate_trapped_cash(
    revenue_annual=test_data['revenue_annual'],
    actual_dso=test_data['actual_dso'],
    actual_dio=test_data['actual_dio'],
    actual_dpo=test_data['actual_dpo']
)

# Display results
print("=" * 70)
print("CALCULATION RESULTS")
print("=" * 70)
print(f"\nTotal Trapped Cash: {format_currency(result['total_trapped_cash'])}")
print(f"Total Expected Recovery: {format_currency(result['total_expected_recovery'])}")
print()

print("BENCHMARKS USED:")
print(f"  DSO Benchmark: {result['benchmarks']['dso']:.1f} days")
print(f"  DIO Benchmark: {result['benchmarks']['dio']:.1f} days")
print(f"  DPO Benchmark: {result['benchmarks']['dpo']:.1f} days")
print()

print("=" * 70)
print("PRIORITY TARGETS (Sorted by Impact)")
print("=" * 70)

for i, target in enumerate(result['targets'], 1):
    print(f"\n{i}. {target['priority']} PRIORITY: {target['component']}")
    print(f"   Trapped Cash: {format_currency(target['trapped'])}")
    print(f"   Excess Days: {target['excess_days']:.1f} days")
    print(f"   Recovery Rate: {format_percentage(target['recovery_rate'])}")
    print(f"   Expected Recovery: {format_currency(target['expected_recovery'])}")
    print(f"   Priority Score: {target['priority_score']:,.2f}")

print()
print("=" * 70)
print("VALIDATION")
print("=" * 70)

# Expected values from requirements
expected_total = 6_400_000  # ~$6.4M
expected_dso = 3_900_000    # ~$3.9M
expected_dio = 1_600_000    # ~$1.6M
expected_dpo = 900_000      # ~$0.9M

# Calculate tolerances (within 20% is acceptable)
def check_value(actual, expected, label):
    diff_pct = abs(actual - expected) / expected * 100
    status = "✓" if diff_pct < 20 else "✗"
    print(f"{status} {label}:")
    print(f"   Expected: {format_currency(expected)}")
    print(f"   Actual: {format_currency(actual)}")
    print(f"   Difference: {diff_pct:.1f}%")
    return diff_pct < 20

all_passed = True
all_passed &= check_value(result['total_trapped_cash'], expected_total, "Total Trapped Cash")
print()

dso_target = next(t for t in result['targets'] if t['component'] == 'DSO')
all_passed &= check_value(dso_target['trapped'], expected_dso, "DSO Trapped Cash")
print()

dio_target = next(t for t in result['targets'] if t['component'] == 'DIO')
all_passed &= check_value(dio_target['trapped'], expected_dio, "DIO Trapped Cash")
print()

dpo_target = next(t for t in result['targets'] if t['component'] == 'DPO')
all_passed &= check_value(dpo_target['trapped'], expected_dpo, "DPO Trapped Cash")
print()

# Check priority order
print("=" * 70)
print("PRIORITY ORDER VALIDATION")
print("=" * 70)
print(f"Expected: DSO (HIGH), DIO (MEDIUM), DPO (LOW)")
print(f"Actual: {result['targets'][0]['component']} ({result['targets'][0]['priority']}), " +
      f"{result['targets'][1]['component']} ({result['targets'][1]['priority']}), " +
      f"{result['targets'][2]['component']} ({result['targets'][2]['priority']})")

priority_correct = (
    result['targets'][0]['component'] == 'DSO' and result['targets'][0]['priority'] == 'HIGH' and
    result['targets'][1]['component'] == 'DIO' and result['targets'][1]['priority'] == 'MEDIUM' and
    result['targets'][2]['component'] == 'DPO' and result['targets'][2]['priority'] == 'LOW'
)

if priority_correct:
    print("✓ Priority order is CORRECT")
else:
    print("✗ Priority order is INCORRECT")

print()
print("=" * 70)
if all_passed and priority_correct:
    print("✓ ALL TESTS PASSED!")
else:
    print("✗ SOME TESTS FAILED - Please review calculations")
print("=" * 70)
