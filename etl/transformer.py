"""Transform ERP data to canonical schema"""
import pandas as pd
from datetime import datetime
import uuid
from config.field_mappings import FIELD_MAPPINGS, DATA_TRANSFORMATIONS

class DataTransformer:
    def __init__(self, erp_system: str, company_id: str):
        self.erp_system = erp_system
        self.company_id = company_id
        self.field_map = FIELD_MAPPINGS.get(erp_system.upper(), {})

    def transform_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        mapping = self.field_map.get('transactions', {})
        canonical_df = pd.DataFrame()

        for canonical_field, erp_field in mapping.items():
            if erp_field in df.columns:
                canonical_df[canonical_field] = df[erp_field]

        canonical_df['company_id'] = self.company_id
        canonical_df['transaction_id'] = [str(uuid.uuid4()) for _ in range(len(df))]
        canonical_df['created_at'] = datetime.now()

        return self._clean_data(canonical_df)

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        for field in DATA_TRANSFORMATIONS['date_fields']:
            if field in df.columns:
                df[field] = pd.to_datetime(df[field], errors='coerce')
        for field in DATA_TRANSFORMATIONS['decimal_fields']:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
        return df
