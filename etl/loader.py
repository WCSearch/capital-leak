"""Load data into Supabase"""
import pandas as pd
from supabase import Client

class DataLoader:
    def __init__(self, supabase_client: Client):
        self.client = supabase_client

    def load_transactions(self, df: pd.DataFrame):
        """Load transactions in batches to Supabase"""
        # Convert DataFrame to list of dicts
        records = df.to_dict('records')

        # Supabase has a limit on batch inserts, so chunk it
        chunk_size = 1000
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            self.client.table('transactions').insert(chunk).execute()
