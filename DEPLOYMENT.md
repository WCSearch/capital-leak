# Streamlit Cloud Deployment Guide

## Configuration Requirements

### 1. Streamlit Cloud Dashboard Settings

When deploying to Streamlit Cloud, ensure these settings are correct:

**Main file path:** `app/main.py`
(NOT `capital-leak-analysis/app/main.py`)

### 2. Environment Variables

Add the following secret in Streamlit Cloud dashboard (Settings → Secrets):

```toml
DATABASE_URL = "postgresql://user:password@host:5432/dbname"
```

Replace with your actual PostgreSQL connection string.

### 3. Required Files

The following files are required for deployment and are already configured:

- ✅ `requirements.txt` - Python dependencies (including psycopg2-binary)
- ✅ `packages.txt` - System dependencies (libpq-dev for PostgreSQL)
- ✅ `.streamlit/config.toml` - Streamlit configuration

### 4. Python Version

This app is compatible with Python 3.9 - 3.13

### Troubleshooting

#### ModuleNotFoundError: No module named 'psycopg2'

This error indicates one of the following issues:

1. **Path Configuration Issue**: The "Main file path" in Streamlit Cloud settings is incorrect
   - Should be: `app/main.py`
   - NOT: `capital-leak-analysis/app/main.py`

2. **Missing DATABASE_URL Secret**: Add DATABASE_URL to Streamlit Cloud secrets

3. **Deployment Not Updated**: Reboot the app in Streamlit Cloud to pick up latest changes

#### Connection Issues

1. Verify DATABASE_URL is set correctly in Streamlit Cloud secrets
2. Check that your database allows connections from Streamlit Cloud IP addresses
3. Test the connection string format: `postgresql://user:password@host:port/database`

## Quick Deploy Checklist

- [ ] Fork/clone repository
- [ ] Create Streamlit Cloud app
- [ ] Set Main file path to `app/main.py`
- [ ] Add DATABASE_URL to secrets
- [ ] Deploy and verify
