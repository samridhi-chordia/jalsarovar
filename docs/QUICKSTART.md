# JalSarovar - Quick Start Guide

## Overview
JalSarovar is now updated with **all the latest features** from the development version, including the Voice Agent that was previously missing.

## What's Included

✓ **Voice Agent** (IVR Notifications) - Added Nov 28, 2025
✓ **Risk Prediction** - Site Risk Assessment
✓ **WQI Calculator** - Water Quality Index computation
✓ **ML Analytics** - Anomaly Detection, Forecasting, Site Risk Classification
✓ **Data Import/Export** - CSV import wizard for sites and test results
✓ **Intervention Tracking** - Water treatment intervention management
✓ **Residential Monitoring** - Raspberry Pi integration for home water quality
✓ **Admin Dashboard** - User management and system configuration

## Database
- **220 MB** uncompressed database with real-world data
- **378,000+** test results from multiple sources
- **68,000+** water quality monitoring sites
- Includes US (USGS), India (CPCB), and synthetic data

## Quick Start (tcsh shell)

```tcsh
cd ~/jalsarovar

# Step 1: Activate virtual environment
source venv/bin/activate.csh

# Step 2: Set environment variables
setenv FLASK_APP app.py
setenv FLASK_ENV development

# Step 3: Start Flask application
flask run --port 5050
```

## Quick Start (bash/zsh shell)

```bash
cd ~/jalsarovar

# Step 1: Activate virtual environment
source venv/bin/activate

# Step 2: Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

# Step 3: Start Flask application
flask run --port 5050
```

## Access the Application

**URL:** http://localhost:5050
**Username:** admin
**Password:** admin123

## Verify Voice Agent is Present

After logging in:
1. Check the navigation menu - you should see "Voice Agent" link
2. Click on "Voice Agent" → "Info" to see the IVR notification system
3. Navigate to "Voice Agent" → "Admin Dashboard" to manage voice notifications

## Features to Explore

### Voice Agent (NEW!)
- `/voice/info` - Information about voice notification system
- `/voice/admin` - Admin dashboard for managing voice notifications
- `/voice/my-notifications` - View your notification logs

### Risk Prediction
- `/risk/dashboard` - Overall risk assessment dashboard
- `/risk/site/<id>` - Individual site risk prediction

### WQI Calculator
- `/wqi/info` - Water Quality Index information
- `/wqi/calculator` - Calculate WQI for water samples
- `/wqi/dashboard` - WQI dashboard and trends

### ML Analytics
- `/ml/dashboard` - Machine learning models overview
- `/ml/anomaly-detection` - Detect water quality anomalies
- `/ml/site-risk` - ML-based site risk classification
- `/ml/cost-analysis` - Cost optimization analysis

### Data Management
- `/admin/import` - Import CSV data for sites and test results
- `/samples` - View and manage water samples
- `/tests` - Manage test results

## Important Files

- **`.env`** - Environment configuration (database path, secret key)
- **`instance/jalsarovar.db`** - SQLite database (220 MB)
- **`requirements.txt`** - Python dependencies
- **`app.py`** - Flask application entry point
- **`setup_and_test.sh`** - Automated setup script

## Backup

The old jalsarovar directory was backed up to:
**`~/jalsarovar_old_backup`**

## Troubleshooting

### Database Error
If you see "unable to open database file":
- Verify `.env` has absolute path: `DATABASE_URL=sqlite:////Users/test/jalsarovar/instance/jalsarovar.db`
- Check database exists: `ls -lh instance/jalsarovar.db`

### Import Error
If you see module import errors:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Port Already in Use
If port 5050 is already in use:
- Use a different port: `flask run --port 5051`
- Or kill existing Flask processes: `pkill -f "flask run"`

## Next Steps

1. **Test Voice Agent** - Navigate to Voice Agent section and verify it's working
2. **Import Data** - Try the CSV import wizard at `/admin/import`
3. **Run ML Models** - Test anomaly detection and risk prediction features
4. **Calculate WQI** - Use the WQI calculator for sample water quality assessments

## Support

For issues or questions, refer to:
- `README.md` - Full functional specifications
- `VOICE_AGENT_GUIDE.md` - Voice Agent documentation
- `ML_ALGORITHMS_DETAILED.md` - ML models documentation
- `DEPLOYMENT_README.md` - Deployment guide for production

---

**JalSarovar** - Water Quality Monitoring and Management System
Version: Development (with all latest features)
Last Updated: December 1, 2025
