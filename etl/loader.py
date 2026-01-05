"""Load data into PostgreSQL"""
import pandas as pd
from sqlalchemy import create_engine

class DataLoader:
    def __init__(self, db_connection_string: str):
        self.engine = create_engine(db_connection_string)

    def load_transactions(self, df: pd.DataFrame):
        df.to_sql('transactions', self.engine, if_exists='append',
                  index=False, method='multi', chunksize=10000)
