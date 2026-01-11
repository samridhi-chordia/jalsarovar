# Fix: ImportError - Cannot Import SiteRiskPrediction

## Error Message
```
ImportError: cannot import name 'SiteRiskPrediction' from 'app.models'
(/var/www/jalsarovar_demo/app/models/__init__.py)
```

## Root Cause

The error path shows `/var/www/jalsarovar_demo/app/models/` but should be `/var/www/jalsarovar_demo/jalsarovar/app/models/`.

**This means the files were copied to the wrong directory structure!**

---

## Expected Directory Structure

```
/var/www/jalsarovar_demo/
├── venv/                          # Virtual environment
└── jalsarovar/                    # ⚠️ THIS DIRECTORY IS MISSING!
    ├── app/
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── ml_prediction.py  # Contains SiteRiskPrediction
    │   │   └── ...
    │   └── ...
    ├── config.py
    ├── app.py
    └── requirements.txt
```

## Actual Directory Structure (Wrong)

```
/var/www/jalsarovar_demo/
├── venv/
└── app/                           # ❌ WRONG! Missing jalsarovar/ parent
    ├── models/
    │   ├── __init__.py
    │   └── ...
    └── ...
```

---

## Quick Fix

### Step 1: Check Current Structure

```bash
# On remote server
ls -la /var/www/jalsarovar_demo/
```

**What to look for:**
- ✅ **Correct**: You see `jalsarovar/` directory
- ❌ **Wrong**: You see `app/` directory directly

### Step 2: Fix the Directory Structure

If the structure is wrong, recreate it:

```bash
# Backup current structure (if it exists)
sudo mv /var/www/jalsarovar_demo /var/www/jalsarovar_demo_BROKEN_$(date +%Y%m%d_%H%M%S)

# Recreate directories
sudo mkdir -p /var/www/jalsarovar_demo
sudo mkdir -p /var/log/jalsarovar-demo

# Set ownership
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/log/jalsarovar-demo

# Extract package again with CORRECT structure
cd /tmp
tar -xzf jalsarovar_20251223_012304.tar.gz
cd jalsarovar_deploy_20251223_012304

# Copy with correct structure (note the trailing slash!)
sudo cp -r . /var/www/jalsarovar_demo/jalsarovar/

# Set ownership
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo
```

### Step 3: Verify Correct Structure

```bash
# Should show jalsarovar directory
ls -la /var/www/jalsarovar_demo/

# Should show app, config.py, app.py, etc.
ls -la /var/www/jalsarovar_demo/jalsarovar/

# Should show models directory
ls -la /var/www/jalsarovar_demo/jalsarovar/app/

# Should show ml_prediction.py file
ls -la /var/www/jalsarovar_demo/jalsarovar/app/models/ | grep ml_prediction
```

**Expected output**: `ml_prediction.py` should be listed

### Step 4: Verify ml_prediction.py Contains Classes

```bash
# Check SiteRiskPrediction is defined
grep "class SiteRiskPrediction" /var/www/jalsarovar_demo/jalsarovar/app/models/ml_prediction.py
```

**Expected output**: `class SiteRiskPrediction(db.Model):`

---

## Root Cause Analysis

### What Went Wrong

The deployment script's copy command should be:

```bash
# CORRECT (what it should be):
cp -r ${DEPLOY_DIR} ${WEB_DIR}

# Which expands to:
cp -r /tmp/jalsarovar_deploy_20251223_012304 /var/www/jalsarovar_demo/jalsarovar
```

This creates:
```
/var/www/jalsarovar_demo/
└── jalsarovar/              # Directory created by cp
    ├── app/
    └── ...
```

### If It Copied Wrong

If somehow files were copied as:
```bash
# WRONG:
cp -r /tmp/jalsarovar_deploy_20251223_012304/* /var/www/jalsarovar_demo/
```

This creates:
```
/var/www/jalsarovar_demo/
├── app/                     # ❌ Wrong level!
├── config.py
└── ...
```

---

## Complete Re-deployment (Safest Fix)

If the structure is messed up, the safest approach is to re-deploy:

### 1. Clean Up Broken Installation

```bash
# Remove broken installation
sudo rm -rf /var/www/jalsarovar_demo
sudo rm -f /etc/systemd/system/jalsarovar-demo.service
sudo rm -f /etc/nginx/sites-enabled/jalsarovar-demo
sudo rm -f /etc/nginx/sites-available/jalsarovar-demo
```

### 2. Re-run Deployment Script

```bash
# Go to extracted package
cd /tmp/jalsarovar_deploy_20251223_012304

# Run deployment script
sudo bash deployment/scripts/remote_setup.sh
```

### 3. Verify Correct Structure After Deployment

```bash
# Check structure
tree -L 3 /var/www/jalsarovar_demo/ 2>/dev/null || \
ls -laR /var/www/jalsarovar_demo/ | head -50

# Expected structure:
# /var/www/jalsarovar_demo/
# ├── venv/
# └── jalsarovar/
#     ├── app/
#     │   ├── models/
#     │   └── ...
#     ├── app.py
#     └── ...
```

---

## Verify All Models Are Imported

After fixing the structure, test the imports:

```bash
cd /var/www/jalsarovar_demo/jalsarovar

sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, '/var/www/jalsarovar_demo/jalsarovar')

# Test importing all models
from app.models import (
    User, Site, WaterSample, TestResult, Analysis,
    SiteRiskPrediction, ContaminationPrediction,
    WaterQualityForecast, AnomalyDetection, WQIReading
)

print("✓ All models imported successfully!")
print(f"✓ SiteRiskPrediction: {SiteRiskPrediction.__name__}")
print(f"✓ ContaminationPrediction: {ContaminationPrediction.__name__}")
EOF
```

**Expected output**:
```
✓ All models imported successfully!
✓ SiteRiskPrediction: SiteRiskPrediction
✓ ContaminationPrediction: ContaminationPrediction
```

---

## Update Systemd Service (If Needed)

If you fixed the directory structure manually, update the systemd service:

```bash
sudo nano /etc/systemd/system/jalsarovar-demo.service
```

Ensure `WorkingDirectory` is correct:
```ini
[Service]
WorkingDirectory=/var/www/jalsarovar_demo/jalsarovar
```

**NOT**:
```ini
WorkingDirectory=/var/www/jalsarovar_demo
```

Save and reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart jalsarovar-demo
```

---

## Prevent This Issue

The deployment script (remote_setup.sh line 134) should copy as:

```bash
cp -r ${DEPLOY_DIR} ${WEB_DIR}
```

Where:
- `DEPLOY_DIR=/tmp/jalsarovar_deploy_20251223_012304`
- `WEB_DIR=/var/www/jalsarovar_demo/jalsarovar`

This creates the correct structure automatically.

---

## Quick Diagnostic Script

Run this to diagnose the issue:

```bash
#!/bin/bash
echo "=== Directory Structure Check ==="
echo ""

echo "1. Base directory exists?"
ls -ld /var/www/jalsarovar_demo/ 2>/dev/null && echo "✓ Exists" || echo "✗ Missing"

echo ""
echo "2. jalsarovar subdirectory exists?"
ls -ld /var/www/jalsarovar_demo/jalsarovar/ 2>/dev/null && echo "✓ Exists" || echo "✗ Missing (PROBLEM!)"

echo ""
echo "3. app directory location?"
if [ -d "/var/www/jalsarovar_demo/jalsarovar/app" ]; then
    echo "✓ app/ is at /var/www/jalsarovar_demo/jalsarovar/app/ (CORRECT)"
elif [ -d "/var/www/jalsarovar_demo/app" ]; then
    echo "✗ app/ is at /var/www/jalsarovar_demo/app/ (WRONG - missing jalsarovar/)"
else
    echo "✗ app/ directory not found"
fi

echo ""
echo "4. ml_prediction.py exists?"
if [ -f "/var/www/jalsarovar_demo/jalsarovar/app/models/ml_prediction.py" ]; then
    echo "✓ Found at correct location"
    grep -c "class SiteRiskPrediction" /var/www/jalsarovar_demo/jalsarovar/app/models/ml_prediction.py && \
    echo "✓ SiteRiskPrediction class is defined"
elif [ -f "/var/www/jalsarovar_demo/app/models/ml_prediction.py" ]; then
    echo "✗ Found at wrong location (missing jalsarovar/ parent)"
else
    echo "✗ Not found"
fi

echo ""
echo "=== Diagnosis Complete ==="
```

Save as `/tmp/check_structure.sh` and run:
```bash
bash /tmp/check_structure.sh
```

---

## Summary

**Problem**: Files copied to `/var/www/jalsarovar_demo/app/` instead of `/var/www/jalsarovar_demo/jalsarovar/app/`

**Solution**: Re-deploy or manually fix directory structure

**Prevention**: Ensure deployment script uses `cp -r ${DEPLOY_DIR} ${WEB_DIR}` (not `cp -r ${DEPLOY_DIR}/* ${WEB_DIR}/`)

---

**Status**: Fixable by recreating correct directory structure

**Time to Fix**: 5 minutes (re-deployment)
