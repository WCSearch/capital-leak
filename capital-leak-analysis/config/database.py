"""
Database configuration and connection management
"""
import os
from dataclasses import dataclass
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', '5432'))
    database: str = os.getenv('DB_NAME', 'capital_leak_db')
    user: str = os.getenv('DB_USER', 'postgres')
    password: str = os.getenv('DB_PASSWORD', '')

    def get_connection_string(self) -> str:
        """Generate SQLAlchemy connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_psycopg2_params(self) -> dict:
        """Get connection parameters for psycopg2"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }


class DatabaseConnection:
    """Singleton database connection manager"""
    _instance: Optional['DatabaseConnection'] = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._engine is None:
            config = DatabaseConfig()
            self._engine = create_engine(
                config.get_connection_string(),
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True
            )
            self._session_factory = sessionmaker(bind=self._engine)

    def get_engine(self):
        """Get SQLAlchemy engine"""
        return self._engine

    def get_session(self):
        """Get new database session"""
        return self._session_factory()

    def get_raw_connection(self):
        """Get raw psycopg2 connection"""
        config = DatabaseConfig()
        return psycopg2.connect(**config.get_psycopg2_params())


def get_db_connection():
    """
    Get database connection

    Returns:
        Database connection object
    """
    return DatabaseConnection().get_raw_connection()


def get_db_session():
    """
    Get SQLAlchemy session

    Returns:
        SQLAlchemy session object
    """
    return DatabaseConnection().get_session()


def execute_query(query: str, params: tuple = None, fetch: bool = True):
    """
    Execute a database query

    Args:
        query: SQL query to execute
        params: Query parameters
        fetch: Whether to fetch results

    Returns:
        Query results if fetch=True, otherwise None
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()
    finally:
        conn.close()


def execute_many(query: str, data: list):
    """
    Execute batch insert/update

    Args:
        query: SQL query to execute
        data: List of parameter tuples
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(query, data)
            conn.commit()
    finally:
        conn.close()
