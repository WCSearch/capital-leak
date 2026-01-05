# Debugging Guide for Capital Leak Analysis Platform

## Overview

This guide helps you debug deployment and runtime issues with the Capital Leak Analysis Platform.

## Quick Diagnosis

### Run the Diagnostic Script

```bash
python scripts/diagnose_environment.py
```

This script will check:
- Python environment and version
- Installed packages
- Database drivers (psycopg2)
- Environment variables
- File system paths
- Database connectivity

## Common Errors and Solutions

### 1. `/mount/admin/install_path: No such file or directory`

**What it means:**
- This is a Streamlit Cloud system message during deployment
- It appears when Streamlit Cloud tries to read installation metadata

**Is it a problem?**
- Usually **NO** - this is a harmless warning
- The file is part of Streamlit Cloud's internal deployment process
- You can safely ignore this if your app works otherwise

**When it IS a problem:**
- If it's followed by actual application errors (like import failures)
- In that case, the real issue is likely the error that follows

---

### 2. `ModuleNotFoundError: No module named 'psycopg2'`

**What it means:**
- The PostgreSQL database driver is not installed
- SQLAlchemy needs psycopg2 to connect to PostgreSQL databases

**Solutions:**

#### For Streamlit Cloud:
1. Check `requirements.txt` includes:
   ```
   psycopg2-binary==2.9.7
   ```
   (Note: Use `psycopg2-binary`, NOT just `psycopg2`)

2. Redeploy your app after updating requirements.txt

#### For Local Development:
```bash
pip install psycopg2-binary==2.9.7
```

**Why psycopg2-binary?**
- `psycopg2-binary` is a standalone package that includes compiled binaries
- `psycopg2` requires PostgreSQL development headers and compilation
- Streamlit Cloud and most platforms need the binary version

---

### 3. `DATABASE_URL not found`

**What it means:**
- The application can't find the database connection string

**Solutions:**

#### For Streamlit Cloud:
1. Go to your app settings
2. Click "Secrets"
3. Add your DATABASE_URL:
   ```toml
   DATABASE_URL = "postgresql://username:password@host:port/database"
   ```

#### For Local Development:
1. Create a `.env` file in the project root:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/capital_leak
   ```

2. Use `.env.example` as a template

**For Supabase Users:**
Your DATABASE_URL should look like:
```
postgresql://postgres.[project-ref]:[password]@[project-ref].supabase.co:5432/postgres
```

Find this in:
- Supabase Dashboard → Project Settings → Database → Connection String

---

### 4. Database Connection Failures

**Check these:**

1. **Credentials are correct**
   ```bash
   python scripts/diagnose_environment.py
   ```
   Look for connection test results

2. **Network access**
   - For Supabase: Check if the database allows connections from Streamlit Cloud IPs
   - Go to Supabase → Project Settings → Database → Connection Pooling
   - Use the "Connection Pooling" URL for better reliability

3. **Database exists**
   - Verify the database and tables are created
   - Run the schema initialization scripts in `database/`

---

## Debug Features in the Code

### 1. Environment Logging

The `config/database.py` module now includes extensive logging:

```python
# Logs are written to stderr and visible in Streamlit Cloud logs
```

**To view logs:**
- **Streamlit Cloud:** App menu → "Manage app" → "Logs"
- **Local:** Check your terminal output (stderr)

### 2. Debug Utilities

Located in `config/debug_utils.py`:

```python
from config.debug_utils import log_debug, log_environment_info

# Log environment details
log_environment_info()

# Check database drivers
check_database_imports()

# Check for install_path issue
check_install_path_file()
```

### 3. Error Details in UI

The updated `app/main.py` shows detailed errors in the Streamlit interface:
- Import errors with full tracebacks
- Database connection failures with troubleshooting tips
- Expandable sections for technical details

---

## Debugging Workflow

### Step 1: Check Logs

**Streamlit Cloud:**
1. Open your app
2. Click hamburger menu → "Manage app"
3. Click "Logs"
4. Look for error messages starting with `[ERROR]` or `✗`

**Local:**
1. Run the app: `streamlit run app/main.py`
2. Check terminal output for error messages

### Step 2: Run Diagnostics

```bash
python scripts/diagnose_environment.py
```

Look for:
- ✓ (checkmarks) = working
- ✗ (crosses) = issues to fix

### Step 3: Verify Configuration

**Check requirements.txt:**
```bash
cat requirements.txt | grep psycopg2
# Should show: psycopg2-binary==2.9.7
```

**Check environment variables:**
```bash
# Local
cat .env | grep DATABASE_URL

# Streamlit Cloud
# Check app settings → Secrets
```

### Step 4: Test Database Connection

```python
from config.database import test_connection

success, message = test_connection()
print(f"Success: {success}")
print(f"Message: {message}")
```

---

## Important Fixes Made

### Bug Fix: DATABASE_URL Environment Variable

**Previous code (BROKEN):**
```python
DATABASE_URL = os.getenv('https://vlbvrhotrlipaoedudys.supabase.co')
```

**Fixed code:**
```python
DATABASE_URL = os.getenv('DATABASE_URL')
```

**What was wrong:**
The URL was being passed as the environment variable NAME instead of reading the actual `DATABASE_URL` variable.

---

## Understanding the Error Flow

When you see multiple errors, read them in order:

1. **First error** = Usually the root cause
2. **Subsequent errors** = Often consequences of the first error

Example:
```
cat: /mount/admin/install_path: No such file or directory  ← Harmless warning
ModuleNotFoundError: No module named 'psycopg2'           ← Real issue
```

The real problem is the missing psycopg2, not the install_path file.

---

## Advanced Debugging

### Enable Detailed SQL Logging

In `config/database.py`, change:
```python
engine = create_engine(DATABASE_URL, echo=True)  # Shows all SQL queries
```

### Check Installed Packages

```bash
pip list | grep -E "(psycopg2|sqlalchemy|streamlit)"
```

### Test Import Chain

```bash
python -c "from config.database import get_engine; print('Success!')"
```

### Environment Variables Check

```bash
python -c "import os; print(os.getenv('DATABASE_URL', 'NOT SET'))"
```

---

## Getting Help

If you're still stuck:

1. **Collect information:**
   - Run `python scripts/diagnose_environment.py > diagnostics.txt`
   - Copy relevant error messages from logs
   - Note your Python version and platform

2. **Check these files:**
   - `requirements.txt` - Are all dependencies listed?
   - `.env` or Streamlit Secrets - Is DATABASE_URL set?
   - Streamlit Cloud logs - What's the full error?

3. **Common solutions:**
   - Redeploy after changing requirements.txt
   - Clear Streamlit cache (Settings → Clear cache)
   - Check database is accessible from your network

---

## Checklist for Deployment

- [ ] `requirements.txt` includes `psycopg2-binary==2.9.7`
- [ ] `DATABASE_URL` is set in Streamlit Cloud Secrets
- [ ] Database is accessible from Streamlit Cloud
- [ ] Database schema is initialized
- [ ] App runs successfully locally
- [ ] No syntax errors in Python files
- [ ] `.env` is in `.gitignore` (don't commit secrets!)

---

## Key Files Reference

- **Debug utilities:** `config/debug_utils.py`
- **Database config:** `config/database.py`
- **Main app:** `app/main.py`
- **Diagnostic script:** `scripts/diagnose_environment.py`
- **Requirements:** `requirements.txt`
- **Environment template:** `.env.example`
