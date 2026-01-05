"""Supabase client connection and configuration"""
import streamlit as st
import logging
from supabase import create_client, Client

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """
    Initialize and return Supabase client using Streamlit secrets.

    Returns:
        Client: Initialized Supabase client

    Raises:
        ValueError: If required secrets are not configured
    """
    try:
        # Get credentials from Streamlit secrets
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]

        logger.info(f"✓ Initializing Supabase client for URL: {supabase_url}")

        # Create and return Supabase client
        client = create_client(supabase_url, supabase_key)
        logger.info("✓ Supabase client initialized successfully")

        return client

    except KeyError as e:
        error_msg = f"Missing Supabase configuration in secrets: {e}"
        logger.error(f"✗ {error_msg}")
        raise ValueError(error_msg) from e
    except Exception as e:
        logger.error(f"✗ Failed to initialize Supabase client: {e}")
        raise

def test_connection(client: Client) -> tuple[bool, str]:
    """
    Test the Supabase connection by attempting a simple query.

    Args:
        client: Supabase client instance

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Simple test query - just check if we can connect
        response = client.table('companies').select('company_id').limit(1).execute()
        return True, "Connected successfully"
    except Exception as e:
        return False, str(e)
