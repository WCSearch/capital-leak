"""
Test script for recovery analysis functions
"""

import pandas as pd
from utils.recovery_analysis import calculate_dio_recovery, format_recovery_summary

# Load SAP synthetic data
transactions_df = pd.read_csv('data/synthetic/transactions.csv')

# Calculate recovery
recovery_data = calculate_dio_recovery(transactions_df)

# Print summary
print(format_recovery_summary(recovery_data))

# Print detailed breakdown
print("\nDETAILED BREAKDOWN BY STATUS:")
print("="*80)
for status, data in recovery_data['breakdown_by_status'].items():
    print(f"\n{status} ({data['category']}):")
    print(f"  Count: {data['count']}")
    print(f"  Total Value: ${data['total_value']:,.2f}")
    print(f"  Recovery Potential: ${data['recovery_potential']:,.2f}")
