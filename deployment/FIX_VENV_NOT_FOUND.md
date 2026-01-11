# Fix: Virtual Environment Not Found

## Error Message
```
✗ Virtual environment not found: /var/www/jalsarovar_demo/venv
```

## What This Means

The deployment script hasn't created the Python virtual environment yet. This happens when:
1. **Deployment was interrupted** before Step 5
2. **Python 3.11 is not installed** on the server
3. **Insufficient permissions** to create the venv directory

---

## Quick Fix

### Option 1: Let the Deployment Script Create It

The `remote_setup.sh` script creates the venv automatically in **Step 5**. If deployment was interrupted, just **re-run the deployment script**:

```bash
# On remote server
cd /tmp/jalsarovar_deploy_20251223_012304
sudo bash deployment/scripts/remote_setup.sh
```

The script will:
- Skip steps that are already complete
- Create the virtual environment
- Install all dependencies
- Continue with remaining steps

---

### Option 2: Create Virtual Environment Manually

If the deployment script keeps failing, create the venv manually:

#### Step 1: Check Python 3.11 is installed

```bash
python3.11 --version
```

**Expected**: `Python 3.11.x`

**If not found**, install it:
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
```

#### Step 2: Create the virtual environment

```bash
# Create as the demo user
sudo -u jalsarovar-demo python3.11 -m venv /var/www/jalsarovar_demo/venv
```

**Expected output**: (silent, no errors)

#### Step 3: Verify venv was created

```bash
ls -la /var/www/jalsarovar_demo/venv/
```

**Expected**: Directory containing `bin/`, `lib/`, `include/`

#### Step 4: Upgrade pip

```bash
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/pip install --upgrade pip
```

#### Step 5: Install dependencies

```bash
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/pip install -r /var/www/jalsarovar_demo/jalsarovar/requirements.txt
```

**This will take 5-10 minutes** and install all packages including xgboost.

---

## Common Issues and Solutions

### Issue 1: Permission Denied

**Error**: `Permission denied: '/var/www/jalsarovar_demo/venv'`

**Fix**:
```bash
# Ensure directory exists and has correct ownership
sudo mkdir -p /var/www/jalsarovar_demo
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo

# Then create venv
sudo -u jalsarovar-demo python3.11 -m venv /var/www/jalsarovar_demo/venv
```

### Issue 2: Python 3.11 Not Found

**Error**: `python3.11: command not found`

**Fix**:
```bash
# Install Python 3.11
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# Verify installation
python3.11 --version
```

### Issue 3: User 'jalsarovar-demo' Doesn't Exist

**Error**: `user jalsarovar-demo does not exist`

**Fix**:
```bash
# Create the user
sudo useradd -m -s /bin/bash jalsarovar-demo

# Verify user was created
id jalsarovar-demo
```

### Issue 4: Directory Doesn't Exist

**Error**: `No such file or directory: '/var/www/jalsarovar_demo'`

**Fix**:
```bash
# Create directory structure
sudo mkdir -p /var/www/jalsarovar_demo
sudo mkdir -p /var/log/jalsarovar-demo

# Set ownership
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/log/jalsarovar-demo
```

---

## Complete Manual Setup (If Deployment Script Fails)

If the automated script keeps failing, follow these steps:

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    postgresql-client \
    nginx \
    git \
    curl \
    build-essential \
    libpq-dev
```

### 2. Create User

```bash
sudo useradd -m -s /bin/bash jalsarovar-demo
```

### 3. Create Directories

```bash
sudo mkdir -p /var/www/jalsarovar_demo
sudo mkdir -p /var/log/jalsarovar-demo
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/log/jalsarovar-demo
```

### 4. Copy Application Files

```bash
# Assuming you extracted the package to /tmp
sudo cp -r /tmp/jalsarovar_deploy_20251223_012304 /var/www/jalsarovar_demo/jalsarovar
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo
```

### 5. Create Virtual Environment

```bash
sudo -u jalsarovar-demo python3.11 -m venv /var/www/jalsarovar_demo/venv
```

### 6. Install Dependencies

```bash
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/pip install --upgrade pip
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/pip install -r /var/www/jalsarovar_demo/jalsarovar/requirements.txt
```

### 7. Continue with Deployment

Now you can continue with the remaining steps from the deployment guide.

---

## Verification

After creating the venv, verify it's working:

### Check venv exists

```bash
ls -la /var/www/jalsarovar_demo/venv/
```

**Expected**: Directories like `bin/`, `lib/`, `include/`, `pyvenv.cfg`

### Check Python version in venv

```bash
/var/www/jalsarovar_demo/venv/bin/python3 --version
```

**Expected**: `Python 3.11.x`

### Check pip works

```bash
/var/www/jalsarovar_demo/venv/bin/pip --version
```

**Expected**: `pip 24.x.x from /var/www/jalsarovar_demo/venv/lib/python3.11/site-packages/pip (python 3.11)`

### Check Flask is installed

```bash
/var/www/jalsarovar_demo/venv/bin/flask --version
```

**Expected**: `Python 3.11.x` and `Flask 3.0.0`

### Check xgboost is installed

```bash
/var/www/jalsarovar_demo/venv/bin/python3 -c "import xgboost; print(xgboost.__version__)"
```

**Expected**: `2.0.3`

---

## What the Deployment Script Does (Step 5)

For reference, here's what the automated script does in Step 5:

```bash
# Line 143: Create virtual environment
sudo -u jalsarovar-demo python3.11 -m venv /var/www/jalsarovar_demo/venv

# Line 144: Upgrade pip
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/pip install --upgrade pip

# Line 145: Install all dependencies
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/pip install -r /var/www/jalsarovar_demo/jalsarovar/requirements.txt
```

This installs ~20 packages including:
- Flask and extensions
- PostgreSQL driver
- ML libraries (numpy, pandas, scikit-learn, xgboost)
- Gunicorn production server

---

## When to Use Manual vs Automated

| Situation | Recommended Approach |
|-----------|---------------------|
| First time deployment | ✅ Use automated script |
| Script fails once | ✅ Re-run automated script |
| Script fails repeatedly | ⚠️ Try manual setup |
| Specific step fails | ⚠️ Fix that step manually, re-run script |
| Testing/debugging | ⚠️ Manual setup for control |

---

## Next Steps After Fixing

Once the venv is created and dependencies installed:

1. **Configure environment** - Create `.env.production`
2. **Test database connection** - Verify PostgreSQL access
3. **Run migrations** - `flask db upgrade`
4. **Start service** - `systemctl start jalsarovar-demo`
5. **Test application** - `curl http://localhost:8001/health`

---

**Status**: This is a fixable issue - the venv just needs to be created!

**Time to Fix**: 5-10 minutes (mostly pip installing dependencies)
