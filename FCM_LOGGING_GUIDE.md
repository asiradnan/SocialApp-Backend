# FCM Notification Logging Guide

## Overview
Comprehensive logging has been added to track FCM notification events for debugging and monitoring in production.

## Log Files

### 1. `fcm_notifications.log`
**Purpose:** FCM-specific notifications and events  
**Location:** Project root directory  
**Contains:**
- Post/Poll creation events
- Notification sending attempts
- Success/failure counts
- Invalid token cleanup

### 2. `django.log`
**Purpose:** General application logs including FCM  
**Location:** Project root directory  
**Contains:**
- All FCM logs (duplicated from fcm_notifications.log)
- Django application logs
- Error stack traces

## Log Formats

### Post Created
```
INFO 📝 POST CREATED: Post ID=123 by John Doe (ID=5)
INFO 📤 Sending post notification to 15 device(s) for Post ID=123
INFO ✅ POST NOTIFICATION SUCCESS: Post ID=123, Sent=14/15, Failed=1
```

### Poll Created
```
INFO 📊 POLL CREATED: Poll ID=456 by Jane Smith (ID=7)
INFO 📤 Sending poll notification to 20 device(s) for Poll ID=456
INFO ✅ POLL NOTIFICATION SUCCESS: Poll ID=456, Sent=20/20, Failed=0
```

### No Recipients
```
WARNING ❌ No FCM tokens found for post 123 - No recipients to notify
```

### Notification Failure
```
ERROR ❌ POST NOTIFICATION FAILED: Post ID=123, All 5 attempts failed
```

### Invalid Token Cleanup
```
WARNING 🧹 Cleaning up 2 invalid tokens
INFO Removed 2 invalid FCM tokens from database
```

### Signal Events
```
INFO 🔔 Signal triggered: New post created (ID=123)
INFO 📲 FCM notification scheduled for post 123
```

## Production Setup (Gunicorn + Nginx)

### 1. Configure Log Rotation

Create `/etc/logrotate.d/django-socialbackend`:

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

### 2. Gunicorn Configuration

Update your gunicorn service or config:

```python
# gunicorn.conf.py
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
capture_output = True
```

### 3. Systemd Service Configuration

```ini
[Unit]
Description=Gunicorn daemon for Django Social Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/venv/bin"
ExecStart=/path/to/your/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/gunicorn.sock \
    --log-level info \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    SocialBackend.wsgi:application

[Install]
WantedBy=multi-user.target
```

### 4. View Logs in Production

```bash
# View FCM-specific logs
tail -f /path/to/project/fcm_notifications.log

# View all Django logs
tail -f /path/to/project/django.log

# View Gunicorn logs
tail -f /var/log/gunicorn/error.log

# Search for FCM events
grep "📝 POST CREATED" fcm_notifications.log
grep "📊 POLL CREATED" fcm_notifications.log
grep "✅.*SUCCESS" fcm_notifications.log
grep "❌.*FAILED" fcm_notifications.log

# Count notifications sent today
grep "$(date +%Y-%m-%d)" fcm_notifications.log | grep "SUCCESS" | wc -l

# Find errors
grep "ERROR" fcm_notifications.log

# Monitor in real-time with filtering
tail -f fcm_notifications.log | grep --color=always -E "POST|POLL|SUCCESS|FAILED"
```

## Testing Locally

### 1. Test Command
```bash
# Test with specific token
python manage.py test_fcm --token "your_fcm_token_here"

# Test with user ID
python manage.py test_fcm --user-id 5

# Test with first available user
python manage.py test_fcm
```

### 2. Create Test Post
```bash
# Django shell
python manage.py shell

from feed.models import Post
from users.models import CustomUser

author = CustomUser.objects.get(id=5)  # Use your instructor ID
post = Post.objects.create(
    author=author,
    text_content="Test post for FCM notification"
)

# Check logs immediately
exit()
tail -20 fcm_notifications.log
```

### 3. View Logs
```bash
# Last 50 lines of FCM logs
tail -50 fcm_notifications.log

# Follow FCM logs in real-time
tail -f fcm_notifications.log

# Filter for specific post
grep "Post ID=123" fcm_notifications.log

# View all notification successes
grep "SUCCESS" fcm_notifications.log
```

## Monitoring Best Practices

### 1. Success Rate Monitoring

Create a simple script to check notification success rate:

```bash
#!/bin/bash
# monitor_fcm.sh

LOG_FILE="fcm_notifications.log"

SUCCESS=$(grep -c "SUCCESS" "$LOG_FILE")
FAILED=$(grep -c "FAILED" "$LOG_FILE")
TOTAL=$((SUCCESS + FAILED))

if [ $TOTAL -gt 0 ]; then
    RATE=$(echo "scale=2; $SUCCESS * 100 / $TOTAL" | bc)
    echo "FCM Success Rate: $RATE% ($SUCCESS/$TOTAL)"
else
    echo "No FCM notifications found in logs"
fi
```

### 2. Alert on Failures

Add to your monitoring system (e.g., cron job):

```bash
# Check for recent failures every 5 minutes
*/5 * * * * grep "FAILED" /path/to/project/fcm_notifications.log | tail -10 | mail -s "FCM Failures Detected" admin@example.com
```

### 3. Daily Report

```bash
#!/bin/bash
# daily_fcm_report.sh

DATE=$(date +%Y-%m-%d)
LOG_FILE="fcm_notifications.log"

echo "=== FCM Report for $DATE ==="
echo ""
echo "Posts Created: $(grep "$DATE.*POST CREATED" "$LOG_FILE" | wc -l)"
echo "Polls Created: $(grep "$DATE.*POLL CREATED" "$LOG_FILE" | wc -l)"
echo "Successful Notifications: $(grep "$DATE.*SUCCESS" "$LOG_FILE" | wc -l)"
echo "Failed Notifications: $(grep "$DATE.*FAILED" "$LOG_FILE" | wc -l)"
echo "Invalid Tokens Cleaned: $(grep "$DATE.*Removed.*invalid" "$LOG_FILE" | wc -l)"
```

## Troubleshooting

### No Logs Appearing

**Check 1: File Permissions**
```bash
ls -la *.log
# Should be writable by gunicorn user (e.g., www-data)

sudo chown www-data:www-data *.log
sudo chmod 644 *.log
```

**Check 2: Gunicorn is Capturing Output**
```bash
# Restart gunicorn
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

**Check 3: Django Logging Configuration**
```python
# In settings.py, verify:
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # Important!
    ...
}
```

### Logs Not Rotating

```bash
# Test logrotate manually
sudo logrotate -f /etc/logrotate.d/django-socialbackend

# Check logrotate status
sudo logrotate -d /etc/logrotate.d/django-socialbackend
```

### Firebase Initialization Errors

```bash
# Check Firebase JSON file
ls -la *firebase*.json

# Verify permissions
sudo chmod 600 *firebase*.json
sudo chown www-data:www-data *firebase*.json

# Check logs for initialization
grep "Firebase Admin SDK" django.log
```

## Log Analysis Examples

### Find posts with no recipients
```bash
grep "No FCM tokens found" fcm_notifications.log
```

### Track specific post notification
```bash
grep "Post ID=123" fcm_notifications.log
```

### See all failed notifications
```bash
grep "FAILED" fcm_notifications.log | tail -20
```

### Count notifications per author
```bash
grep "POST CREATED" fcm_notifications.log | \
  awk -F'by ' '{print $2}' | \
  awk -F' \\(' '{print $1}' | \
  sort | uniq -c | sort -rn
```

### Average recipients per notification
```bash
grep "Sending.*notification to" fcm_notifications.log | \
  awk '{print $7}' | \
  awk '{sum+=$1; count++} END {print sum/count}'
```

## Example Log Output

```log
INFO 2025-11-07 14:23:15 fcm_helper 12345 67890 🔔 Signal triggered: New post created (ID=42)
INFO 2025-11-07 14:23:15 fcm_helper 12345 67890 📲 FCM notification scheduled for post 42
INFO 2025-11-07 14:23:15 fcm_helper 12345 67890 📝 POST CREATED: Post ID=42 by John Doe (ID=5)
INFO 2025-11-07 14:23:15 fcm_helper 12345 67890 📤 Sending post notification to 15 device(s) for Post ID=42
INFO 2025-11-07 14:23:16 fcm_helper 12345 67890 Successfully sent FCM notification: projects/socalwelfare/messages/0:123456789
INFO 2025-11-07 14:23:16 fcm_helper 12345 67890 Successfully sent FCM notification: projects/socalwelfare/messages/0:123456790
WARNING 2025-11-07 14:23:16 fcm_helper 12345 67890 Invalid FCM token (unregistered): dXyZ123abc...
INFO 2025-11-07 14:23:17 fcm_helper 12345 67890 ✅ POST NOTIFICATION SUCCESS: Post ID=42, Sent=14/15, Failed=1
WARNING 2025-11-07 14:23:17 fcm_helper 12345 67890 🧹 Cleaning up 1 invalid tokens
INFO 2025-11-07 14:23:17 fcm_helper 12345 67890 Removed 1 invalid FCM tokens from database
```

## Quick Reference

| Log Pattern | Meaning |
|-------------|---------|
| `📝 POST CREATED` | New post created by instructor |
| `📊 POLL CREATED` | New poll created by instructor |
| `📤 Sending` | Notification being sent to devices |
| `✅ SUCCESS` | Notification(s) sent successfully |
| `❌ FAILED` | Notification(s) failed to send |
| `🧹 Cleaning up` | Removing invalid FCM tokens |
| `🔔 Signal triggered` | Django signal fired |
| `📲 scheduled` | Notification queued for sending |

## Support

For issues with logging:
1. Check file permissions
2. Verify Gunicorn is running with correct user
3. Check Django settings.py LOGGING configuration
4. Ensure Firebase JSON file is accessible
5. Review system logs: `journalctl -u gunicorn -n 50`
