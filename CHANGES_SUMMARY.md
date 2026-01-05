# Debug Code Implementation - Summary of Changes

## Overview
Added comprehensive debugging and error handling to diagnose and fix deployment issues, specifically targeting:
1. The `/mount/admin/install_path` error (Streamlit Cloud system message)
2. `ModuleNotFoundError: No module named 'psycopg2'` errors
3. Database connection issues
4. Environment configuration problems

---

## Files Created

### 1. `config/debug_utils.py` (NEW)
**Purpose:** Comprehensive debugging utilities

**Key Functions:**
- `log_debug()` - Timestamped logging to stderr
- `log_environment_info()` - Logs Python version, paths, environment variables
- `is_streamlit_cloud()` - Detects Streamlit Cloud environment
- `check_database_imports()` - Tests which PostgreSQL drivers are available
- `check_install_path_file()` - Investigates the `/mount/admin/install_path` issue
- `safe_import()` - Import with detailed error logging

**Features:**
- Logs to stderr for visibility in Streamlit Cloud logs
- Masks sensitive data (passwords, keys, URLs)
- Comprehensive environment diagnostics
- Package availability checks

---

### 2. `scripts/diagnose_environment.py` (NEW)
**Purpose:** Standalone diagnostic script

**Usage:**
```bash
python scripts/diagnose_environment.py
```

**What it checks:**
- Python version and environment
- Python path and working directory
- Environment variables (DATABASE_URL, etc.)
- File system paths
- Installed packages (psycopg2, sqlalchemy, streamlit, pandas, plotly)
- Database connectivity
- The `/mount/admin/install_path` file issue

**Output:**
- ✓ = Success
- ✗ = Failure
- Detailed error messages for troubleshooting

---

### 3. `docs/DEBUGGING.md` (NEW)
**Purpose:** Comprehensive debugging guide

**Covers:**
- Common errors and solutions
- `/mount/admin/install_path` explanation (it's harmless!)
- `psycopg2` import errors
- Database configuration
- Step-by-step debugging workflow
- Advanced debugging techniques
- Deployment checklist

---

## Files Modified

### 1. `config/database.py` (MAJOR UPDATE)

#### Critical Bug Fix:
**BEFORE (BROKEN):**
```python
DATABASE_URL = os.getenv('https://vlbvrhotrlipaoedudys.supabase.co')
```

**AFTER (FIXED):**
```python
DATABASE_URL = os.getenv('DATABASE_URL')
```

**Issue:** The URL was being passed as the environment variable NAME instead of reading the actual variable value. This would cause `DATABASE_URL` to always be `None`.

#### New Features:
1. **Comprehensive logging:**
   - Logs every step of module initialization
   - Shows import status for all dependencies
   - Logs database connection attempts

2. **Error handling:**
   - Try-catch blocks around all imports
   - Detailed error messages with traceback
   - Helpful troubleshooting hints

3. **psycopg2 availability check:**
   - Checks for both `psycopg2` and `psycopg2-binary`
   - Logs version information
   - Provides warnings if not found

4. **Fallback configuration:**
   - Tries `DATABASE_URL` first
   - Falls back to `SUPABASE_URL` if needed
   - Lists available database-related env vars on failure

5. **Enhanced test_connection():**
   - More detailed error reporting
   - Tests actual query execution
   - Shows PostgreSQL version
   - Categorizes errors with helpful messages

6. **Debug mode:**
   - Optional connection test on module load
   - Set `TEST_DB_ON_LOAD=true` or `ENVIRONMENT=development`

#### Logging Output:
- All logs go to **stderr** for visibility in Streamlit Cloud logs
- Format: `[LEVEL] message` with timestamps
- Levels: DEBUG, INFO, WARNING, ERROR

---

### 2. `app/main.py` (MAJOR UPDATE)

#### New Features:

1. **Startup diagnostics:**
   ```python
   # Logs Python version, working directory, Python path
   print("STARTING CAPITAL LEAK STREAMLIT APP", file=sys.stderr)
   ```

2. **Import error handling:**
   - Each import wrapped in try-catch
   - Shows error in UI with expandable details
   - Provides troubleshooting steps

3. **Database import protection:**
   ```python
   try:
       from config.database import get_engine, test_connection
   except ImportError as e:
       # Show user-friendly error with troubleshooting steps
       st.error("Database Module Import Error")
       # ... detailed help ...
   ```

4. **Connection testing:**
   - Tests database connection before proceeding
   - Shows spinner while connecting
   - Clear error messages on failure
   - Troubleshooting tips in expandable section

5. **Error handling for data loading:**
   - Try-catch around company loading
   - Try-catch around metrics loading
   - Helpful error messages for missing tables

6. **All errors show:**
   - User-friendly message in UI
   - Technical details in expandable section
   - Full traceback for debugging
   - Suggested solutions

#### User Experience:
- Clear error messages instead of raw Python tracebacks
- Troubleshooting steps embedded in UI
- Links to documentation
- Progressive error handling (fail gracefully)

---

### 3. `.env.example` (UPDATED)

#### Bug Fix:
**BEFORE (INVALID):**
```env
DATABASE_URL=postgresql:https://vlbvrhotrlipaoedudys.supabase.co
```

**AFTER (VALID):**
```env
# For PostgreSQL (standard):
# DATABASE_URL=postgresql://username:password@localhost:5432/database_name
#
# For Supabase:
# DATABASE_URL=postgresql://postgres.[project-ref]:[password]@[project-ref].supabase.co:5432/postgres
DATABASE_URL=postgresql://postgres:your_password@your_host:5432/capital_leak
```

#### Improvements:
- Added comments explaining format
- Shows examples for both standard PostgreSQL and Supabase
- Added optional debug configuration variables
- Proper PostgreSQL URL format

---

## Key Improvements

### 1. Error Visibility
**Before:** Errors were cryptic and hard to debug
**After:** Every error includes:
- What went wrong
- Why it might have happened
- How to fix it
- Full technical details for advanced debugging

### 2. Installation Path Error
**Before:** Confusing error message, unclear if it's a problem
**After:** Documented that it's a harmless Streamlit Cloud system message

### 3. Database Configuration
**Before:** Broken `DATABASE_URL` reading, invalid `.env.example`
**After:** Correct environment variable reading, comprehensive examples

### 4. Import Failures
**Before:** Application crashes with raw Python errors
**After:** Graceful failures with troubleshooting steps in UI

### 5. Debugging Workflow
**Before:** No systematic way to diagnose issues
**After:**
- Run `python scripts/diagnose_environment.py`
- Check Streamlit logs for detailed messages
- Refer to `docs/DEBUGGING.md` for solutions

---

## Testing the Changes

### 1. Test locally:
```bash
# Run diagnostics
python scripts/diagnose_environment.py

# Test database import
python -c "from config.database import get_engine; print('Success!')"

# Run the app
streamlit run app/main.py
```

### 2. Check logs:
- All debug messages go to **stderr**
- Look for `[INFO]`, `[DEBUG]`, `[ERROR]`, `[WARNING]` tags
- Check for ✓ (success) and ✗ (failure) markers

### 3. Verify fixes:
- [ ] `DATABASE_URL` is read correctly
- [ ] `psycopg2-binary` is detected
- [ ] Database connection succeeds
- [ ] App starts without crashes
- [ ] Errors show helpful messages in UI

---

## Deployment Notes

### For Streamlit Cloud:

1. **Update Secrets:**
   ```toml
   DATABASE_URL = "postgresql://your_actual_url_here"
   ```

2. **Verify requirements.txt:**
   ```
   psycopg2-binary==2.9.7  # ← Must be present
   ```

3. **Check logs after deployment:**
   - App menu → Manage app → Logs
   - Look for debug messages starting with `[INFO]`, `[ERROR]`

4. **The install_path error:**
   - This is **normal** and can be ignored
   - It's a Streamlit Cloud system message
   - Only worry if followed by actual application errors

---

## What Each Error Means

### 1. `/mount/admin/install_path: No such file or directory`
- **Severity:** Low (usually harmless)
- **Cause:** Streamlit Cloud system trying to read metadata
- **Action:** Ignore if app works; investigate if followed by failures

### 2. `ModuleNotFoundError: No module named 'psycopg2'`
- **Severity:** Critical (app won't work)
- **Cause:** Missing `psycopg2-binary` in requirements.txt
- **Action:** Add to requirements.txt, redeploy

### 3. `DATABASE_URL not found`
- **Severity:** Critical (app won't work)
- **Cause:** Environment variable not set
- **Action:** Add to `.env` (local) or Secrets (Streamlit Cloud)

### 4. `Failed to create engine`
- **Severity:** Critical (app won't work)
- **Cause:** Invalid DATABASE_URL format or credentials
- **Action:** Check URL format, verify credentials

---

## Quick Reference

### Files to check when debugging:
1. **requirements.txt** - Package dependencies
2. **.env** (local) or Secrets (cloud) - DATABASE_URL
3. **Streamlit logs** - Detailed error messages
4. **docs/DEBUGGING.md** - Troubleshooting guide

### Commands to run:
```bash
# Diagnose environment
python scripts/diagnose_environment.py

# Test database import
python -c "from config.database import test_connection; print(test_connection())"

# Check requirements
cat requirements.txt | grep psycopg2

# Run app
streamlit run app/main.py
```

### What to look for in logs:
- `✓` = Success
- `✗` = Failure
- `[ERROR]` = Critical issue
- `[WARNING]` = Potential issue
- `[INFO]` = Informational
- `[DEBUG]` = Detailed debugging info

---

## Summary

These changes transform the application from having cryptic errors to providing:
- **Comprehensive diagnostics** - Know exactly what's wrong
- **Clear error messages** - Understand the issue immediately
- **Troubleshooting steps** - Fix problems without guessing
- **Logging infrastructure** - Track what's happening
- **Bug fixes** - Correct DATABASE_URL reading and configuration

The debug code will help identify exactly what's causing issues in deployment and provide clear paths to resolution.
