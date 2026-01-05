"""Load data into Supabase using API"""
import pandas as pd
from supabase import Client

class DataLoader:
    def __init__(self, supabase_client: Client):
        """Initialize DataLoader with Supabase client

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    def load_transactions(self, df: pd.DataFrame):
        """Load transactions data to Supabase

        Args:
            df: DataFrame containing transaction data
        """
        # Convert DataFrame to list of dictionaries
        records = df.to_dict('records')

        # Insert in batches of 1000 (Supabase API limit)
        batch_size = 1000
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            self.supabase.table('transactions').insert(batch).execute()
