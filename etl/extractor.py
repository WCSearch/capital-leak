"""Extract data from ERP systems"""
import pandas as pd

class ERPExtractor:
    def __init__(self, erp_system: str):
        self.erp_system = erp_system

    def extract_from_csv(self, file_path: str) -> pd.DataFrame:
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except:
            return pd.read_csv(file_path, encoding='latin-1')

    def extract_gl_transactions(self, source: str) -> pd.DataFrame:
        return self.extract_from_csv(source)

    def extract_event_logs(self, source: str) -> pd.DataFrame:
        return self.extract_from_csv(source)
