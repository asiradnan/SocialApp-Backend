# 🚀 FCM Logging - Deployment Checklist

## Pre-Deployment Checks ✅

### Local Testing
- [ ] **Run Django checks:** `python manage.py check`
  ```bash
  cd /path/to/project
  venv/bin/python manage.py check
  ```

- [ ] **Test FCM notification:**
  ```bash
  python manage.py test_fcm --user-id <instructor_id>
  ```

- [ ] **Verify log files created:**
  ```bash
  ls -la *.log
  ```
  Expected: `django.log` and `fcm_notifications.log`

- [ ] **Create test post/poll and verify logging:**
  ```bash
  # Create content via API or Django admin
  # Then check:
  tail -20 fcm_notifications.log
  ```

### Firebase Configuration
- [ ] **Firebase JSON file exists:**
  ```bash
  ls -la *firebase*.json
  ```
  Should show: `socalwelfare-firebase-adminsdk-fbsvc-5f4cf67c25.json`

- [ ] **Firebase JSON in .gitignore:**
  ```bash
  grep -i firebase .gitignore
  ```
  Should show patterns like `*-firebase-adminsdk-*.json`

- [ ] **Settings.py has correct path:**
  ```python
  # Verify in SocialBackend/settings.py
  FIREBASE_CONFIG = {
      'SERVICE_ACCOUNT_KEY_PATH': BASE_DIR / 'socalwelfare-firebase-adminsdk-fbsvc-5f4cf67c25.json',
      'PROJECT_ID': 'socalwelfare',
  }
  ```

### Code Review
- [ ] **All files committed (except Firebase JSON):**
  ```bash
  git status
  ```

- [ ] **No sensitive data in commits:**
  ```bash
  git log --all --full-history --source --pretty=format:"%H" -- "*firebase*.json"
  ```
  Should show nothing (file never committed)

---

## Deployment Steps 🎯

### 1. Backup (if updating existing deployment)
```bash
# On production server
cd /path/to/project
cp -r . ../project_backup_$(date +%Y%m%d)
pg_dump database_name > backup_$(date +%Y%m%d).sql  # If using PostgreSQL
```

### 2. Deploy Code
```bash
# On production server
cd /path/to/project
git pull origin main
source venv/bin/activate
pip install -r requirements.txt  # In case new dependencies
python manage.py migrate
python manage.py collectstatic --noinput
```

### 3. Configure Firebase JSON
```bash
# Copy Firebase JSON to production server (SECURELY)
# Option 1: SCP from local
scp socalwelfare-firebase-adminsdk-*.json user@server:/path/to/project/

# Option 2: Upload via secure method (not Git!)

# Set correct permissions
cd /path/to/project
chmod 600 socalwelfare-firebase-adminsdk-*.json
chown www-data:www-data socalwelfare-firebase-adminsdk-*.json
```

### 4. Set Log File Permissions
```bash
cd /path/to/project

# Create log files if they don't exist
touch django.log fcm_notifications.log

# Set permissions
sudo chown www-data:www-data *.log
sudo chmod 644 *.log

# Verify
ls -la *.log
```

### 5. Configure Log Rotation
```bash
# Create logrotate config
sudo nano /etc/logrotate.d/django-socialbackend
```

**Content:**
```conf
/path/to/your/project/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0644 www-data www-data
    sharedscripts
    postrotate
        systemctl reload gunicorn
    endscript
}
```

**Test logrotate:**
```bash
sudo logrotate -d /etc/logrotate.d/django-socialbackend
```

### 6. Restart Services
```bash
# Restart Gunicorn
sudo systemctl restart gunicorn
sudo systemctl status gunicorn

# Reload Nginx (if needed)
sudo systemctl reload nginx

# Check for errors
sudo journalctl -u gunicorn -n 50
```

---

## Post-Deployment Verification ✅

### 1. Check Services Running
```bash
# Gunicorn status
sudo systemctl status gunicorn

# Nginx status
sudo systemctl status nginx

# Check processes
ps aux | grep gunicorn
```

### 2. Test API Access
```bash
# Health check (if you have one)
curl https://your-domain.com/api/health/

# Or test any public endpoint
curl https://your-domain.com/api/
```

### 3. Verify Firebase Initialization
```bash
cd /path/to/project

# Check Django logs for Firebase initialization
grep "Firebase Admin SDK" django.log

# Should see: "Firebase Admin SDK initialized successfully"
```

### 4. Test FCM Notifications
```bash
# Option 1: Use management command
cd /path/to/project
source venv/bin/activate
python manage.py test_fcm --user-id <id>

# Option 2: Create test post via API
curl -X POST https://your-domain.com/api/feed/posts/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text_content": "Test notification"}'
```

### 5. Verify Logging Works
```bash
cd /path/to/project

# Check if logs are being written
ls -la *.log

# View recent FCM logs
tail -20 fcm_notifications.log

# Monitor in real-time
tail -f fcm_notifications.log
```

### 6. Test Notification Flow
**Create a post and verify logs show:**
- [ ] `🔔 Signal triggered: New post created`
- [ ] `📲 FCM notification scheduled`
- [ ] `📝 POST CREATED: Post ID=X by Author`
- [ ] `📤 Sending post notification to N device(s)`
- [ ] `✅ POST NOTIFICATION SUCCESS` (or appropriate result)

```bash
# Watch logs while creating content
tail -f fcm_notifications.log
```

---

## Monitoring Setup 📊

### 1. Set Up Daily Reports (Optional)
```bash
# Create monitoring script
sudo nano /usr/local/bin/fcm_daily_report.sh
```

**Script content:**
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
LOG_FILE="/path/to/project/fcm_notifications.log"

echo "=== FCM Report for $DATE ==="
echo "Posts Created: $(grep "$DATE.*POST CREATED" "$LOG_FILE" | wc -l)"
echo "Polls Created: $(grep "$DATE.*POLL CREATED" "$LOG_FILE" | wc -l)"
echo "Successful: $(grep "$DATE.*SUCCESS" "$LOG_FILE" | wc -l)"
echo "Failed: $(grep "$DATE.*FAILED" "$LOG_FILE" | wc -l)"
```

**Make executable and add to cron:**
```bash
sudo chmod +x /usr/local/bin/fcm_daily_report.sh

# Add to cron (runs at 11:59 PM daily)
crontab -e
# Add: 59 23 * * * /usr/local/bin/fcm_daily_report.sh | mail -s "Daily FCM Report" admin@example.com
```

### 2. Set Up Failure Alerts (Optional)
```bash
# Add to cron (check every 5 minutes)
crontab -e
# Add: */5 * * * * grep "FAILED" /path/to/project/fcm_notifications.log | tail -5 | mail -s "FCM Failures" admin@example.com
```

---

## Troubleshooting Guide 🔧

### Logs Not Appearing
**Symptom:** No log files created or empty

**Solutions:**
1. Check file permissions:
   ```bash
   ls -la /path/to/project/*.log
   sudo chown www-data:www-data /path/to/project/*.log
   sudo chmod 644 /path/to/project/*.log
   ```

2. Check Gunicorn user:
   ```bash
   ps aux | grep gunicorn
   # Should run as www-data or configured user
   ```

3. Check Gunicorn configuration:
   ```bash
   sudo systemctl cat gunicorn
   # Verify User= and WorkingDirectory= settings
   ```

4. Test write permissions:
   ```bash
   sudo -u www-data touch /path/to/project/test.log
   ```

### Firebase Initialization Fails
**Symptom:** Errors like "Failed to initialize Firebase Admin SDK"

**Solutions:**
1. Check file exists:
   ```bash
   ls -la /path/to/project/*firebase*.json
   ```

2. Check permissions:
   ```bash
   # Should be readable by Gunicorn user
   chmod 600 /path/to/project/*firebase*.json
   chown www-data:www-data /path/to/project/*firebase*.json
   ```

3. Verify path in settings.py matches actual file

4. Check logs:
   ```bash
   grep -i firebase /path/to/project/django.log
   sudo journalctl -u gunicorn -n 100 | grep -i firebase
   ```

### No Notifications Sent
**Symptom:** Posts created but no "POST CREATED" in logs

**Solutions:**
1. Check if signals are registered:
   ```bash
   # Look for signal imports in feed/apps.py
   grep -r "default_app_config" feed/
   ```

2. Verify feed app is in INSTALLED_APPS:
   ```bash
   grep "feed" /path/to/project/SocialBackend/settings.py
   ```

3. Check Django admin - did signal actually fire?
   ```bash
   python manage.py shell
   >>> from feed.models import Post
   >>> Post.objects.latest('created_at')  # Check recent posts
   ```

4. Look for errors:
   ```bash
   grep -i error /path/to/project/django.log | tail -20
   ```

### Gunicorn Won't Start
**Symptom:** Service fails to start after deployment

**Solutions:**
1. Check logs:
   ```bash
   sudo journalctl -u gunicorn -n 50
   ```

2. Test manually:
   ```bash
   cd /path/to/project
   source venv/bin/activate
   gunicorn SocialBackend.wsgi:application --bind 127.0.0.1:8000
   ```

3. Check for Python errors:
   ```bash
   python manage.py check --deploy
   ```

---

## Security Checklist 🔐

- [ ] **Firebase JSON NOT in Git:**
  ```bash
  git log --all --oneline --decorate -- "*firebase*.json"
  # Should show nothing
  ```

- [ ] **Firebase JSON has restricted permissions:**
  ```bash
  ls -la *firebase*.json
  # Should be: -rw------- (600)
  ```

- [ ] **Firebase JSON owned by Gunicorn user:**
  ```bash
  ls -la *firebase*.json
  # Should be: www-data www-data
  ```

- [ ] **Log files NOT world-readable:**
  ```bash
  ls -la *.log
  # Should be: -rw-r--r-- (644) or more restrictive
  ```

- [ ] **.gitignore includes Firebase patterns:**
  ```bash
  cat .gitignore | grep -i firebase
  ```

- [ ] **Production uses HTTPS** (for FCM tokens)

- [ ] **Django settings secure for production:**
  ```python
  DEBUG = False
  ALLOWED_HOSTS = ['your-domain.com']
  SECRET_KEY = 'long-random-string'
  SECURE_SSL_REDIRECT = True
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  ```

---

## Final Verification ✅

### Complete This Flow
1. [ ] **Deploy code to production**
2. [ ] **Configure Firebase JSON with correct permissions**
3. [ ] **Restart Gunicorn**
4. [ ] **Check service status - all green**
5. [ ] **View logs:** `tail -f fcm_notifications.log`
6. [ ] **Create test post via API**
7. [ ] **Verify logs show:**
   - Signal triggered
   - Post created with ID
   - Notification sent (or no recipients if no tokens)
   - Success/failure logged
8. [ ] **Check from mobile app (if FCM tokens exist)**
9. [ ] **Verify notification received on device**
10. [ ] **Monitor logs for 24 hours for any issues**

---

## Quick Commands Summary

```bash
# Deployment
git pull && sudo systemctl restart gunicorn

# View logs
tail -f /path/to/project/fcm_notifications.log

# Check status
sudo systemctl status gunicorn

# Test notification
cd /path/to/project && python manage.py test_fcm

# Today's stats
grep "$(date +%Y-%m-%d)" fcm_notifications.log | grep -c "SUCCESS"

# Check errors
grep ERROR django.log | tail -20

# Restart services
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

---

## Support & Documentation 📚

Refer to these files for details:
- `FCM_QUICK_REFERENCE.md` - Quick commands
- `FCM_LOGGING_QUICKSTART.md` - Getting started
- `FCM_LOGGING_GUIDE.md` - Complete guide
- `FCM_LOGGING_EXAMPLES.md` - Example outputs
- `FCM_API_REFERENCE.md` - API endpoints
- `FCM_IMPLEMENTATION.md` - Full setup

---

## Success Criteria ✨

Your deployment is successful when:
- ✅ Gunicorn runs without errors
- ✅ Logs are being written (`fcm_notifications.log` updates)
- ✅ Creating a post shows in logs immediately
- ✅ Notifications sent to devices (if FCM tokens exist)
- ✅ No Firebase initialization errors
- ✅ Log rotation configured
- ✅ Services restart without issues

---

**Ready for production deployment!** 🚀

Print this checklist and mark items as you complete them.
