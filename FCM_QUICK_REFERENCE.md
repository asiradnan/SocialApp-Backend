# FCM Logging - Quick Reference Card

## 🎯 Essential Commands

### View Logs
```bash
# FCM-specific logs
tail -f fcm_notifications.log

# All Django logs
tail -f django.log

# Filtered view (successes/failures only)
tail -f fcm_notifications.log | grep --color=always -E "SUCCESS|FAILED"
```

### Test Notifications
```bash
python manage.py test_fcm                # Use first available user
python manage.py test_fcm --user-id 5    # Specific user
python manage.py test_fcm --token "..."  # Specific token
```

### Search Logs
```bash
grep "POST CREATED" fcm_notifications.log     # All posts
grep "POLL CREATED" fcm_notifications.log     # All polls
grep "SUCCESS" fcm_notifications.log          # Successes
grep "FAILED" fcm_notifications.log           # Failures
grep "Post ID=42" fcm_notifications.log       # Specific post
```

### Statistics
```bash
# Count today's notifications
grep "$(date +%Y-%m-%d)" fcm_notifications.log | grep "SUCCESS" | wc -l

# Success/failure counts
echo "Success: $(grep -c 'SUCCESS' fcm_notifications.log)"
echo "Failed: $(grep -c 'FAILED' fcm_notifications.log)"
```

---

## 📝 Log Patterns

| Icon | Meaning | Example |
|------|---------|---------|
| 📝 | Post created | `POST CREATED: Post ID=42 by John Doe` |
| 📊 | Poll created | `POLL CREATED: Poll ID=15 by Jane Smith` |
| 📤 | Sending notifications | `Sending post notification to 15 device(s)` |
| ✅ | Success | `SUCCESS: Sent=14/15, Failed=1` |
| ❌ | Failure or no recipients | `FAILED: All 5 attempts failed` |
| 🧹 | Cleaning invalid tokens | `Cleaning up 2 invalid tokens` |
| 🔔 | Signal triggered | `Signal triggered: New post created` |
| 📲 | Notification scheduled | `FCM notification scheduled` |

---

## 🔧 Production Setup

### 1. Deploy
```bash
git pull
sudo systemctl restart gunicorn
```

### 2. Set Permissions
```bash
sudo chown www-data:www-data /path/to/project/*.log
sudo chmod 644 /path/to/project/*.log
```

### 3. Configure Log Rotation
```bash
# Create /etc/logrotate.d/django-socialbackend
/path/to/project/*.log {
    daily
    rotate 14
    compress
    create 0644 www-data www-data
}
```

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| No logs appearing | Check permissions: `ls -la *.log` |
| | Restart Gunicorn: `systemctl restart gunicorn` |
| Firebase errors | Check JSON file: `ls -la *firebase*.json` |
| | Verify permissions: `chmod 600 firebase.json` |
| All notifications fail | Check Firebase initialization in logs |
| | Verify service account JSON path in settings.py |

---

## 📊 Example Log Flow

```
🔔 Signal triggered: New post created (ID=42)
📲 FCM notification scheduled for post 42
📝 POST CREATED: Post ID=42 by John Doe (ID=5)
📤 Sending post notification to 15 device(s) for Post ID=42
✅ POST NOTIFICATION SUCCESS: Post ID=42, Sent=14/15, Failed=1
🧹 Cleaning up 1 invalid tokens
```

---

## 📚 Documentation Files

- `FCM_LOGGING_SUMMARY.md` - Complete overview
- `FCM_LOGGING_QUICKSTART.md` - Quick start guide
- `FCM_LOGGING_GUIDE.md` - Comprehensive reference
- `FCM_LOGGING_EXAMPLES.md` - Real log examples
- `FCM_API_REFERENCE.md` - API endpoints
- `FCM_IMPLEMENTATION.md` - Full setup guide

---

## ⚡ Most Used Commands

```bash
# Monitor in real-time
tail -f fcm_notifications.log

# Test notifications
python manage.py test_fcm

# Check today's stats
grep "$(date +%Y-%m-%d)" fcm_notifications.log | grep -E "POST|POLL|SUCCESS|FAILED"

# Find errors
grep "ERROR" fcm_notifications.log

# Count notifications
grep -c "POST CREATED" fcm_notifications.log
grep -c "POLL CREATED" fcm_notifications.log
```

---

**Ready for production!** 🚀
