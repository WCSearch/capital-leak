"""
Data extraction module
Extracts data from various sources (CSV, database, API)
"""
import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataExtractor(ABC):
    """Base class for data extractors"""

    @abstractmethod
    def extract(self, source: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data from source

        Args:
            source: Data source identifier
            **kwargs: Additional extraction parameters

        Returns:
            List of dictionaries containing extracted data
        """
        pass

    def validate_data(self, data: List[Dict[str, Any]], required_fields: List[str]) -> bool:
        """
        Validate that required fields exist in data

        Args:
            data: Extracted data
            required_fields: List of required field names

        Returns:
            True if valid, False otherwise
        """
        if not data:
            logger.warning("No data to validate")
            return False

        for record in data:
            missing_fields = [field for field in required_fields if field not in record]
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                return False

        return True


class CSVExtractor(DataExtractor):
    """Extract data from CSV files"""

    def extract(self, source: str, encoding: str = 'utf-8', **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data from CSV file

        Args:
            source: Path to CSV file
            encoding: File encoding
            **kwargs: Additional pandas read_csv parameters

        Returns:
            List of dictionaries
        """
        try:
            file_path = Path(source)
            if not file_path.exists():
                logger.error(f"CSV file not found: {source}")
                return []

            logger.info(f"Extracting data from CSV: {source}")

            # Use pandas for robust CSV parsing
            df = pd.read_csv(source, encoding=encoding, **kwargs)

            # Convert DataFrame to list of dictionaries
            data = df.to_dict('records')

            logger.info(f"Extracted {len(data)} records from {source}")
            return data

        except Exception as e:
            logger.error(f"Error extracting CSV data: {str(e)}")
            return []

    def extract_batch(self, source: str, batch_size: int = 1000, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data in batches for large files

        Args:
            source: Path to CSV file
            batch_size: Number of records per batch
            **kwargs: Additional parameters

        Yields:
            Batches of records
        """
        try:
            for chunk in pd.read_csv(source, chunksize=batch_size, **kwargs):
                yield chunk.to_dict('records')
        except Exception as e:
            logger.error(f"Error in batch extraction: {str(e)}")
            yield []


class DatabaseExtractor(DataExtractor):
    """Extract data from database"""

    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initialize database extractor

        Args:
            connection_params: Database connection parameters
        """
        self.connection_params = connection_params

    def extract(self, source: str, params: Optional[tuple] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data using SQL query

        Args:
            source: SQL query string
            params: Query parameters
            **kwargs: Additional parameters

        Returns:
            List of dictionaries
        """
        conn = None
        try:
            logger.info(f"Connecting to database...")
            conn = psycopg2.connect(**self.connection_params)

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                logger.info(f"Executing query...")
                cursor.execute(source, params)
                data = cursor.fetchall()

                # Convert to list of regular dicts
                result = [dict(row) for row in data]

                logger.info(f"Extracted {len(result)} records from database")
                return result

        except Exception as e:
            logger.error(f"Database extraction error: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()

    def extract_table(self, table_name: str, columns: Optional[List[str]] = None,
                      where_clause: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract entire table or specific columns

        Args:
            table_name: Name of table
            columns: List of column names (None for all)
            where_clause: Optional WHERE clause

        Returns:
            List of dictionaries
        """
        cols = ', '.join(columns) if columns else '*'
        query = f"SELECT {cols} FROM {table_name}"

        if where_clause:
            query += f" WHERE {where_clause}"

        return self.extract(query)


class JSONExtractor(DataExtractor):
    """Extract data from JSON files"""

    def extract(self, source: str, json_path: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data from JSON file

        Args:
            source: Path to JSON file
            json_path: Optional JSONPath for nested data
            **kwargs: Additional parameters

        Returns:
            List of dictionaries
        """
        try:
            file_path = Path(source)
            if not file_path.exists():
                logger.error(f"JSON file not found: {source}")
                return []

            logger.info(f"Extracting data from JSON: {source}")

            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, list):
                result = data
            elif isinstance(data, dict) and json_path:
                # Navigate to nested data using json_path
                keys = json_path.split('.')
                result = data
                for key in keys:
                    result = result.get(key, [])
            else:
                result = [data]

            logger.info(f"Extracted {len(result)} records from {source}")
            return result

        except Exception as e:
            logger.error(f"Error extracting JSON data: {str(e)}")
            return []


class APIExtractor(DataExtractor):
    """Extract data from REST API"""

    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        """
        Initialize API extractor

        Args:
            base_url: Base URL of API
            auth_token: Optional authentication token
        """
        self.base_url = base_url
        self.auth_token = auth_token

    def extract(self, source: str, method: str = 'GET', **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data from API endpoint

        Args:
            source: API endpoint path
            method: HTTP method
            **kwargs: Additional request parameters

        Returns:
            List of dictionaries
        """
        try:
            import requests

            url = f"{self.base_url}/{source}"
            headers = kwargs.pop('headers', {})

            if self.auth_token:
                headers['Authorization'] = f"Bearer {self.auth_token}"

            logger.info(f"Calling API: {url}")

            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()

            data = response.json()

            # Handle different response structures
            if isinstance(data, list):
                result = data
            elif isinstance(data, dict):
                # Try common pagination patterns
                result = data.get('data', data.get('results', [data]))
            else:
                result = []

            logger.info(f"Extracted {len(result)} records from API")
            return result

        except Exception as e:
            logger.error(f"API extraction error: {str(e)}")
            return []


# Factory function to create appropriate extractor
def get_extractor(source_type: str, **config) -> DataExtractor:
    """
    Factory function to create data extractor

    Args:
        source_type: Type of source (csv, database, json, api)
        **config: Configuration parameters

    Returns:
        DataExtractor instance
    """
    extractors = {
        'csv': CSVExtractor,
        'json': JSONExtractor,
        'database': DatabaseExtractor,
        'api': APIExtractor
    }

    extractor_class = extractors.get(source_type.lower())
    if not extractor_class:
        raise ValueError(f"Unknown source type: {source_type}")

    # Create instance with appropriate parameters
    if source_type.lower() == 'database':
        return extractor_class(config.get('connection_params', {}))
    elif source_type.lower() == 'api':
        return extractor_class(
            config.get('base_url', ''),
            config.get('auth_token')
        )
    else:
        return extractor_class()
