# Quick Database Restoration - demo.jalsarovar.com

**Purpose**: Fast database restoration on remote server with automated script

**Time Required**: 5-10 minutes

---

## 🚀 Quick Steps

### On Your Local Mac (Create & Transfer Dump)

```bash
# 1. Create database dump
cd /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar
./deployment/scripts/create_database_dump.sh

# 2. Transfer to server
scp backups/jalsarovar_db_*.sql.gz user@demo.jalsarovar.com:/tmp/
```

### On Remote Server (Restore Database)

```bash
# 1. SSH to server
ssh user@demo.jalsarovar.com

# 2. Run restoration script
cd /tmp
sudo bash /var/www/jalsarovar_demo/jalsarovar/deployment/scripts/restore_database_remote.sh
```

**That's it!** The script will:
- ✅ Find the dump file automatically
- ✅ Prompt for database credentials
- ✅ Test connection
- ✅ Backup existing database (if exists)
- ✅ Drop and recreate database
- ✅ Restore from dump
- ✅ Run migrations
- ✅ Restart application
- ✅ Verify everything works

---

## 📋 What the Script Does

### 1. Pre-Restoration Checks
- Finds most recent dump file in `/tmp/`
- Tests database connection
- Checks if database already exists
- Creates backup of existing data

### 2. Database Restoration
- Drops existing demo database (with confirmation)
- Creates fresh database
- Restores from dump file
- Shows progress and statistics

### 3. Post-Restoration Tasks
- Runs database migrations
- Restarts demo application
- Tests health endpoint
- Displays verification data

### 4. Cleanup
- Removes temporary files
- Shows summary and next steps

---

## 💡 Interactive Prompts

The script will ask for:

| Prompt | Default | Notes |
|--------|---------|-------|
| Database Host | `localhost` | Usually localhost |
| Database Port | `5432` | Standard PostgreSQL port |
| Database Name | `jal_sarovar_demo` | Demo database name |
| Database User | `postgres` | Database user |
| Database Password | *(none)* | Enter your password |
| Confirm restoration | *(none)* | Type `yes` to proceed |

**Use the same credentials you entered during demo deployment.**

---

## 📊 Example Output

```
Jal Sarovar Database Restoration
For demo.jalsarovar.com

Found dump file: /tmp/jalsarovar_db_20250122_225855.sql.gz
Dump file size: 2.3M

Database Configuration
Enter database credentials (these should match your demo deployment)

Database Host [localhost]:
Database Port [5432]:
Database Name [jal_sarovar_demo]:
Database User [postgres]:
Database Password:

✓ Database connection successful

Checking for existing database...
Database 'jal_sarovar_demo' already exists

Existing database statistics:
  Tables: 24
  Size: 45 MB

Creating backup of existing database...
Backup location: /var/backups/jalsarovar_demo/jal_sarovar_demo_backup_20250122_230045.sql.gz
✓ Backup created successfully (2.1M)

⚠️  WARNING: This will REPLACE all data in 'jal_sarovar_demo' database
Continue with restoration? (yes/no): yes

Preparing dump file...
Decompressing dump file...
✓ Decompression successful (23M)

Dropping existing database...
✓ Database dropped

Creating fresh database...
✓ Database created

Restoring database from dump...
This may take a few minutes depending on database size...

✓ Database restored successfully

Verifying restoration...
Restored database statistics:
  Tables: 24
  Size: 48 MB

Record counts in key tables:
  table_name   | records
---------------+---------
 analyses      |    3456
 samples       |    3456
 sites         |     125
 test_results  |    3456
 users         |       5

Running database migrations...
✓ Migrations completed

Restarting demo application...
✓ Application restarted
✓ Service is running

Testing application health...
✓ Application is responding
{
  "status": "healthy",
  "service": "jal-sarovar"
}

Cleaning up...
✓ Removed decompressed SQL file

=========================================
Database Restoration Complete!
=========================================

Summary:
  Database: jal_sarovar_demo
  Tables: 24
  Size: 48 MB
  Backup: /var/backups/jalsarovar_demo/jal_sarovar_demo_backup_20250122_230045.sql.gz

Next steps:
  1. Test at: http://demo.jalsarovar.com
  2. Login with your credentials
  3. Verify sites and samples data

Troubleshooting:
  View logs: sudo journalctl -u jalsarovar-demo -f
  Check status: sudo systemctl status jalsarovar-demo
  Restart: sudo systemctl restart jalsarovar-demo
```

---

## 🔧 Manual Steps (If Script Not Available)

If the automated script is not available, follow these manual steps:

```bash
# 1. Decompress dump
cd /tmp
gunzip jalsarovar_db_*.sql.gz

# 2. Set credentials
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=jal_sarovar_demo
export DB_USER=postgres
export DB_PASSWORD=your-password

# 3. Backup existing database
PGPASSWORD=${DB_PASSWORD} pg_dump -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} | gzip > /tmp/backup_$(date +%Y%m%d).sql.gz

# 4. Drop and recreate
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -U ${DB_USER} -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -U ${DB_USER} -d postgres -c "CREATE DATABASE ${DB_NAME};"

# 5. Restore
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} < jalsarovar_db_*.sql

# 6. Run migrations
cd /var/www/jalsarovar_demo/jalsarovar
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade

# 7. Restart application
sudo systemctl restart jalsarovar-demo
```

---

## 🛡️ Safety Features

The restoration script includes:

1. **Automatic Backup**: Existing database backed up before restoration
2. **Connection Test**: Verifies credentials before proceeding
3. **Confirmation Prompt**: Requires explicit "yes" to replace data
4. **Error Handling**: Stops on errors, preserves existing data
5. **Verification**: Shows statistics before and after restoration
6. **Cleanup**: Removes temporary files automatically

---

## 🐛 Troubleshooting

### Script Can't Find Dump File

```bash
# List dump files
ls -lh /tmp/jalsarovar_db_*.sql.gz

# If not found, transfer it:
# On your Mac:
scp backups/jalsarovar_db_*.sql.gz user@demo.jalsarovar.com:/tmp/
```

### Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check credentials in demo .env file
cat /var/www/jalsarovar_demo/jalsarovar/.env.production | grep DB_
```

### Application Won't Start After Restoration

```bash
# Check logs
sudo journalctl -u jalsarovar-demo -n 100

# Try manual restart
sudo systemctl restart jalsarovar-demo

# Check status
sudo systemctl status jalsarovar-demo
```

### Permission Denied Errors

```bash
# Run script with sudo
sudo bash /var/www/jalsarovar_demo/jalsarovar/deployment/scripts/restore_database_remote.sh
```

### Migrations Fail

```bash
# Check migration status
cd /var/www/jalsarovar_demo/jalsarovar
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db current

# Force upgrade
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade
```

---

## 📍 File Locations

After restoration:

```
Database Dump:
  /tmp/jalsarovar_db_YYYYMMDD_HHMMSS.sql.gz

Backup (if database existed):
  /var/backups/jalsarovar_demo/jal_sarovar_demo_backup_YYYYMMDD_HHMMSS.sql.gz

Restoration Script:
  /var/www/jalsarovar_demo/jalsarovar/deployment/scripts/restore_database_remote.sh

Application:
  /var/www/jalsarovar_demo/jalsarovar/

Logs:
  sudo journalctl -u jalsarovar-demo
  /var/log/jalsarovar-demo/
```

---

## ✅ Verification Checklist

After restoration:

- [ ] Database tables restored (check count matches)
- [ ] Record counts match expectations
- [ ] Application service running
- [ ] Health endpoint responding
- [ ] Can access http://demo.jalsarovar.com
- [ ] Can login with credentials
- [ ] Sites list displays
- [ ] Sample data visible
- [ ] No errors in logs

---

## 🔄 Regular Updates

To regularly sync your local database to demo:

```bash
# On Mac - weekly/monthly sync
cd /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar
./deployment/scripts/create_database_dump.sh
scp backups/jalsarovar_db_*.sql.gz user@demo.jalsarovar.com:/tmp/

# On Server - restore
ssh user@demo.jalsarovar.com
sudo bash /var/www/jalsarovar_demo/jalsarovar/deployment/scripts/restore_database_remote.sh
```

---

## 📚 Related Documentation

- **[RESTORE_DATABASE.md](RESTORE_DATABASE.md)** - Comprehensive restoration guide with troubleshooting
- **[DEPLOY_TO_DEMO.md](../DEPLOY_TO_DEMO.md)** - Complete deployment guide
- **[deployment/README.md](README.md)** - All deployment options

---

**Last Updated**: December 22, 2025
**Version**: 1.0
**Script Location**: `deployment/scripts/restore_database_remote.sh`
