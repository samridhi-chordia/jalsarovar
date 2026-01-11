# Database Transfer and Restoration Guide

**Purpose**: Transfer local database to demo.jalsarovar.com server

**Time Required**: 10-20 minutes (depending on database size)

---

## 🚀 Quick Start (Automated Script)

**For fastest restoration, use the automated script:**

### On Local Mac:
```bash
cd /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar
./deployment/scripts/create_database_dump.sh
scp backups/jalsarovar_db_*.sql.gz user@demo.jalsarovar.com:/tmp/
```

### On Remote Server:
```bash
ssh user@demo.jalsarovar.com
sudo bash /var/www/jalsarovar_demo/jalsarovar/deployment/scripts/restore_database_remote.sh
```

**Done!** The script handles everything automatically.

**See**: [QUICK_DATABASE_RESTORE.md](QUICK_DATABASE_RESTORE.md) for details.

---

## 📖 Manual Restoration (Detailed Guide)

The sections below provide step-by-step manual instructions if you prefer manual control or if the automated script is not available.

---

## Overview

This guide covers:
1. Creating a database dump on your local Mac
2. Transferring the dump to remote server
3. Restoring the database on remote server
4. Verifying the restoration

---

## ⚠️ Important Notes

- **Demo Database**: This will create/restore to `jal_sarovar_demo` database
- **Production Safety**: Your production database at `/var/www/jalsarovar` is NOT affected
- **Backup First**: If demo database already exists, it will be backed up automatically
- **Data Loss**: Existing demo database data will be replaced with your local data

---

## Prerequisites

### On Local Machine (Mac):
- [ ] PostgreSQL installed (`psql --version` to verify)
- [ ] Access to local database `jalsarovar_amrit_sarovar`
- [ ] Database credentials in `.env` file
- [ ] SSH access to remote server

### On Remote Server:
- [ ] PostgreSQL 15 installed
- [ ] Sufficient disk space (2-3x database size)
- [ ] Database user with CREATE DATABASE privileges
- [ ] Demo application already deployed (optional but recommended)

---

## Step 1: Create Database Dump (On Your Mac)

### Option A: Using the Automated Script (Recommended)

```bash
# Navigate to application directory
cd /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar

# Run the dump script
./deployment/scripts/create_database_dump.sh
```

**Expected Output**:
```
Jal Sarovar Database Dump Creator
For transfer to demo.jalsarovar.com

Database Configuration:
  Host: localhost
  Port: 5432
  Database: jalsarovar_amrit_sarovar
  User: postgres

✓ Database connection successful

Gathering database statistics...
  Database size: 45 MB
  Number of tables: 25

Creating database dump...
✓ Database dump created successfully
  Dump file size: 12M

Compressing dump file...
✓ Compression successful

=========================================
Database dump created successfully!
=========================================

Dump file location: /Users/test/.../jalsarovar_db_20250122_143022.sql.gz
Original size: 12M
Compressed size: 2.1M
```

### Option B: Manual Dump (Alternative)

```bash
# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=jalsarovar_amrit_sarovar
export DB_USER=postgres
export DB_PASSWORD=Autodrome@123

# Create backups directory
mkdir -p /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar/backups

# Create dump
PGPASSWORD=${DB_PASSWORD} pg_dump \
    -h ${DB_HOST} \
    -p ${DB_PORT} \
    -U ${DB_USER} \
    -d ${DB_NAME} \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --format=plain \
    --file=/Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar/backups/jalsarovar_db.sql

# Compress it
gzip /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar/backups/jalsarovar_db.sql
```

---

## Step 2: Transfer to Remote Server

### Transfer the Dump File

```bash
# Using the automated script output
scp /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar/backups/jalsarovar_db_*.sql.gz user@demo.jalsarovar.com:/tmp/

# Or if demo is on same server as main domain:
scp /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar/backups/jalsarovar_db_*.sql.gz user@jalsarovar.com:/tmp/
```

**Replace `user`** with your SSH username.

**Expected Output**:
```
jalsarovar_db_20250122_143022.sql.gz    100%   2.1MB   1.2MB/s   00:02
```

---

## Step 3: Restore on Remote Server

### SSH to Server

```bash
ssh user@demo.jalsarovar.com
# Or: ssh user@jalsarovar.com
```

### Prepare for Restoration

```bash
# Navigate to /tmp
cd /tmp

# Decompress the dump file
gunzip jalsarovar_db_*.sql.gz

# You should now have jalsarovar_db_TIMESTAMP.sql
ls -lh jalsarovar_db_*.sql
```

### Set Database Credentials

You'll need the database credentials you configured during demo deployment.

```bash
# Set environment variables (use your actual values)
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=jal_sarovar_demo
export DB_USER=postgres
export DB_PASSWORD=your-actual-password
```

**Note**: These should match what you entered during `remote_setup.sh` deployment.

### Test Database Connection

```bash
# Test connection
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "SELECT 1"
```

**Expected**: `1` (output showing connection works)

### Backup Existing Demo Database (If Exists)

```bash
# Check if demo database exists
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "\l" | grep ${DB_NAME}

# If it exists, back it up first
if PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "\l" | grep -q ${DB_NAME}; then
    echo "Backing up existing demo database..."
    BACKUP_FILE="/tmp/jal_sarovar_demo_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
    PGPASSWORD=${DB_PASSWORD} pg_dump \
        -h ${DB_HOST} \
        -p ${DB_PORT} \
        -U ${DB_USER} \
        -d ${DB_NAME} | gzip > ${BACKUP_FILE}
    echo "Backup saved to: ${BACKUP_FILE}"
fi
```

### Drop and Recreate Demo Database

```bash
# Drop existing demo database (if exists)
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"

# Create fresh demo database
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "CREATE DATABASE ${DB_NAME};"

# Verify creation
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "\l" | grep ${DB_NAME}
```

**Expected Output**:
```
DROP DATABASE
CREATE DATABASE
 jal_sarovar_demo | postgres | UTF8 | ...
```

### Restore the Database

```bash
# Restore from dump file
PGPASSWORD=${DB_PASSWORD} psql \
    -h ${DB_HOST} \
    -p ${DB_PORT} \
    -U ${DB_USER} \
    -d ${DB_NAME} \
    < /tmp/jalsarovar_db_*.sql
```

**Expected Output**:
You'll see many lines like:
```
SET
SET
CREATE EXTENSION
CREATE TABLE
ALTER TABLE
COPY 1234
COPY 567
...
CREATE INDEX
ALTER TABLE
```

**Note**: Some warnings about roles/ownership are normal and can be ignored.

### Run Database Migrations (Important!)

After restoration, run migrations to ensure schema is up-to-date:

```bash
# Navigate to demo application directory
cd /var/www/jalsarovar_demo/jalsarovar

# Run migrations as demo user
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Running upgrade
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl
```

---

## Step 4: Verify Restoration

### Check Database Tables

```bash
# Count tables
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c "
SELECT schemaname, COUNT(*) as table_count
FROM pg_tables
WHERE schemaname = 'public'
GROUP BY schemaname;
"
```

**Expected**: Should show table count (e.g., 20-30 tables)

### Check Sample Data

```bash
# Count records in key tables
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c "
SELECT
    'sites' as table_name, COUNT(*) as record_count FROM sites
UNION ALL
SELECT 'samples', COUNT(*) FROM samples
UNION ALL
SELECT 'test_results', COUNT(*) FROM test_results
UNION ALL
SELECT 'analyses', COUNT(*) FROM analyses
UNION ALL
SELECT 'users', COUNT(*) FROM users;
"
```

**Expected Output**:
```
  table_name   | record_count
---------------+--------------
 sites         |          125
 samples       |         3456
 test_results  |         3456
 analyses      |         3456
 users         |            5
```

### Check Application Connectivity

```bash
# If demo application is running, test it
curl http://localhost:8001/health

# Expected response:
# {"status": "healthy", "service": "jal-sarovar"}
```

### Restart Demo Application

```bash
# Restart the demo service to ensure it picks up database changes
sudo systemctl restart jalsarovar-demo

# Check status
sudo systemctl status jalsarovar-demo
```

**Expected**: `Active: active (running)`

### Test via Browser

Open in browser: **http://demo.jalsarovar.com**

- Should see the application homepage
- Try logging in with your local credentials
- Check if sites/samples data appears

---

## Step 5: Cleanup

### Remove Dump Files (Optional)

```bash
# On remote server
rm /tmp/jalsarovar_db_*.sql
rm /tmp/jalsarovar_db_*.sql.gz  # if any compressed files remain

# On local Mac (keep backups directory, just remove if space is tight)
# rm /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar/backups/jalsarovar_db_*.sql.gz
```

---

## Troubleshooting

### Error: Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check if PostgreSQL is listening
sudo lsof -i :5432

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Error: Role/User Does Not Exist

The dump includes `--no-owner` flag, so ownership warnings are normal. If you see errors:

```bash
# Create the user if needed
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "
CREATE USER jalsarovar_demo_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO jalsarovar_demo_user;
"
```

### Error: Permission Denied

```bash
# Grant permissions to postgres user
sudo -u postgres psql -c "ALTER USER postgres WITH SUPERUSER;"

# Or restore as postgres user
sudo -u postgres bash
PGPASSWORD=${DB_PASSWORD} psql -d ${DB_NAME} < /tmp/jalsarovar_db_*.sql
```

### Error: Disk Space Full

```bash
# Check available space
df -h

# Remove old backups if needed
sudo find /tmp -name "*.sql*" -mtime +7 -delete

# Check database sizes
sudo -u postgres psql -c "
SELECT pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
ORDER BY pg_database_size(pg_database.datname) DESC;
"
```

### Application Shows Old Data

```bash
# Clear application cache (if using Redis)
redis-cli FLUSHALL

# Restart the application
sudo systemctl restart jalsarovar-demo

# Check logs
sudo journalctl -u jalsarovar-demo -n 50
```

---

## Complete Restoration Script

For convenience, here's a complete script to run on the remote server:

```bash
#!/bin/bash
# Save this as /tmp/restore_demo_db.sh and run: bash /tmp/restore_demo_db.sh

set -e

# Configuration (CHANGE THESE!)
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=jal_sarovar_demo
export DB_USER=postgres
export DB_PASSWORD=your-actual-password

# Find the dump file
DUMP_FILE=$(ls -t /tmp/jalsarovar_db_*.sql.gz | head -1)

if [ -z "$DUMP_FILE" ]; then
    echo "Error: No dump file found in /tmp/"
    exit 1
fi

echo "Using dump file: $DUMP_FILE"

# Decompress
echo "Decompressing..."
gunzip $DUMP_FILE
SQL_FILE="${DUMP_FILE%.gz}"

# Backup existing database
echo "Backing up existing demo database..."
BACKUP_FILE="/tmp/jal_sarovar_demo_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
PGPASSWORD=${DB_PASSWORD} pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} 2>/dev/null | gzip > ${BACKUP_FILE} || echo "No existing database to backup"

# Drop and recreate
echo "Dropping existing database..."
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"

echo "Creating fresh database..."
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "CREATE DATABASE ${DB_NAME};"

# Restore
echo "Restoring database..."
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} < ${SQL_FILE}

# Run migrations
echo "Running migrations..."
cd /var/www/jalsarovar_demo/jalsarovar
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade

# Restart application
echo "Restarting application..."
sudo systemctl restart jalsarovar-demo

# Verify
echo ""
echo "Verification:"
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c "
SELECT 'sites' as table_name, COUNT(*) as record_count FROM sites
UNION ALL SELECT 'samples', COUNT(*) FROM samples
UNION ALL SELECT 'test_results', COUNT(*) FROM test_results;"

echo ""
echo "✓ Database restoration complete!"
echo "✓ Backup saved to: ${BACKUP_FILE}"
echo ""
echo "Test at: http://demo.jalsarovar.com"
```

---

## Quick Reference Commands

### Create Dump (Mac):
```bash
cd /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar
./deployment/scripts/create_database_dump.sh
```

### Transfer:
```bash
scp backups/jalsarovar_db_*.sql.gz user@demo.jalsarovar.com:/tmp/
```

### Restore (Server):
```bash
cd /tmp
gunzip jalsarovar_db_*.sql.gz
PGPASSWORD=your-password psql -U postgres -d jal_sarovar_demo < jalsarovar_db_*.sql
cd /var/www/jalsarovar_demo/jalsarovar
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade
sudo systemctl restart jalsarovar-demo
```

---

## Security Notes

1. **Never commit dump files** to version control
2. **Secure transfer**: Use SCP over SSH (as shown above)
3. **Clean up**: Remove dump files after restoration
4. **Passwords**: Never include passwords in scripts committed to git
5. **Backups**: Always backup before restoring
6. **Permissions**: Ensure dump files have restricted permissions (600)

---

## Database Migration vs Restoration

**When to Restore Database**:
- Initial demo deployment
- Syncing production data to demo
- Major data refresh

**When to Run Migrations Only**:
- Code updates that include schema changes
- After git pull with new migrations
- Incremental updates

**Both** (Restore then Migrate):
- When restoring older dumps to newer code
- Ensures schema matches current application version

---

## Success Checklist

After restoration:

- [ ] Database tables verified
- [ ] Sample data counts match expectations
- [ ] Application can connect to database
- [ ] Demo application restarted successfully
- [ ] Website accessible at demo.jalsarovar.com
- [ ] Login works with credentials
- [ ] Sites/samples display correctly
- [ ] No errors in application logs
- [ ] Production database unaffected

---

**Last Updated**: December 22, 2025
**Version**: 1.0
**For**: demo.jalsarovar.com database restoration
