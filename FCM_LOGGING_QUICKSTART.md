# FCM Logging - Quick Start Guide

## ✅ What's Been Added

### 1. Enhanced Logging Configuration (`settings.py`)
- **New log file:** `fcm_notifications.log` - FCM-specific events
- **Enhanced formatters:** Verbose logging with timestamps, module names
- **Separate loggers:** Dedicated logger for `utils.fcm_helper`

### 2. Detailed Log Messages
**Post Creation:**
```
📝 POST CREATED: Post ID=123 by John Doe (ID=5)
📤 Sending post notification to 15 device(s) for Post ID=123
✅ POST NOTIFICATION SUCCESS: Post ID=123, Sent=14/15, Failed=1
```

**Poll Creation:**
```
📊 POLL CREATED: Poll ID=456 by Jane Smith (ID=7)
📤 Sending poll notification to 20 device(s) for Poll ID=456
✅ POLL NOTIFICATION SUCCESS: Poll ID=456, Sent=20/20, Failed=0
```

**No Recipients:**
```
❌ No FCM tokens found for post 123 - No recipients to notify
```

**Failures:**
```
❌ POST NOTIFICATION FAILED: Post ID=123, All 5 attempts failed
```

### 3. Test Command
```bash
python manage.py test_fcm              # Test with first available token
python manage.py test_fcm --user-id 5  # Test with specific user
```

## 🚀 Quick Usage

### Local Development

**Start your server and watch logs:**
```bash
# Terminal 1: Run Django
python manage.py runserver

# Terminal 2: Watch FCM logs
tail -f fcm_notifications.log
```

**Create a post to test:**
```bash
python manage.py shell

from feed.models import Post
from users.models import CustomUser

author = CustomUser.objects.filter(is_instructor=True).first()
post = Post.objects.create(
    author=author,
    text_content="Test post for FCM notification"
)
exit()

# Check logs
tail -20 fcm_notifications.log
```

### Production (Gunicorn + Nginx)

**View logs:**
```bash
# FCM-specific logs
tail -f /path/to/project/fcm_notifications.log

# All Django logs
tail -f /path/to/project/django.log

# Filter for events
tail -f fcm_notifications.log | grep --color=always -E "POST|POLL|SUCCESS|FAILED"
```

**Common searches:**
```bash
# All posts created today
grep "$(date +%Y-%m-%d)" fcm_notifications.log | grep "POST CREATED"

# Failed notifications
grep "FAILED" fcm_notifications.log

# Success rate check
grep -c "SUCCESS" fcm_notifications.log
grep -c "FAILED" fcm_notifications.log
```

## 🔧 Production Setup Checklist

- [ ] **Log File Permissions:**
  ```bash
  sudo chown www-data:www-data /path/to/project/*.log
  sudo chmod 644 /path/to/project/*.log
  ```

- [ ] **Configure Log Rotation:** `/etc/logrotate.d/django-socialbackend`
  ```conf
  /path/to/project/*.log {
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

- [ ] **Restart Gunicorn:**
  ```bash
  sudo systemctl restart gunicorn
  sudo systemctl status gunicorn
  ```

- [ ] **Test Logging:**
  ```bash
  # Create a post via API and check logs
  tail -f /path/to/project/fcm_notifications.log
  ```

## 📊 What You'll See

### When Post is Created:
1. Signal triggers: `🔔 Signal triggered: New post created`
2. Notification scheduled: `📲 FCM notification scheduled`
3. Post creation logged: `📝 POST CREATED: Post ID=X by Author Name`
4. Recipients counted: `📤 Sending post notification to N device(s)`
5. Result logged: `✅ SUCCESS` or `❌ FAILED`

### When Poll is Created:
Same flow with poll icon: `📊 POLL CREATED`

### When No Recipients:
`❌ No FCM tokens found for post X - No recipients to notify`

### When Invalid Tokens Found:
```
🧹 Cleaning up 2 invalid tokens
Removed 2 invalid FCM tokens from database
```

## 🐛 Troubleshooting

**No logs appearing?**
1. Check file permissions: `ls -la *.log`
2. Check Gunicorn user can write: `sudo -u www-data touch test.log`
3. Verify Firebase JSON file exists and is readable
4. Restart Gunicorn: `sudo systemctl restart gunicorn`

**Firebase errors?**
1. Check JSON file location matches settings.py
2. Verify file permissions: `chmod 600 *firebase*.json`
3. Check initialization: `grep "Firebase Admin SDK" django.log`

**Want more details?**
See `FCM_LOGGING_GUIDE.md` for comprehensive documentation.

## 📁 Files Modified

- ✅ `SocialBackend/settings.py` - Enhanced logging configuration
- ✅ `utils/fcm_helper.py` - Added detailed logging to all functions
- ✅ `feed/signals.py` - Added signal logging for post/poll creation
- ✅ `feed/management/commands/test_fcm.py` - New test command

## 📝 New Files Created

- `fcm_notifications.log` - Auto-created on first notification
- `FCM_LOGGING_GUIDE.md` - Comprehensive logging guide
- `FCM_LOGGING_QUICKSTART.md` - This file

## 🎯 Next Steps

1. **Deploy to production** with updated code
2. **Set up log rotation** on your server
3. **Monitor logs** after deployment
4. **Test notifications** using the test command or by creating posts

## 📞 Log Monitoring Commands

```bash
# Real-time monitoring
tail -f fcm_notifications.log

# Count today's notifications
grep "$(date +%Y-%m-%d)" fcm_notifications.log | grep "SUCCESS" | wc -l

# Find errors
grep "ERROR" fcm_notifications.log

# Check specific post
grep "Post ID=123" fcm_notifications.log

# Success rate
echo "Success: $(grep -c 'SUCCESS' fcm_notifications.log)"
echo "Failed: $(grep -c 'FAILED' fcm_notifications.log)"
```

---

**Ready to deploy!** 🚀 All logging is configured and working.
