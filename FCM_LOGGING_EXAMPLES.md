# FCM Logging - Example Outputs

This document shows exactly what you'll see in your logs for different scenarios.

---

## Scenario 1: Successful Post with Notifications

### What happens:
1. Instructor creates a post
2. 15 users have FCM tokens
3. 14 notifications sent successfully
4. 1 token is invalid

### Log Output (`fcm_notifications.log`):
```
INFO 2025-11-07 10:30:15,123 feed.signals 📝 Signal triggered: New post created (ID=42)
INFO 2025-11-07 10:30:15,124 feed.signals 📲 FCM notification scheduled for post 42
INFO 2025-11-07 10:30:15,150 utils.fcm_helper 📝 POST CREATED: Post ID=42 by John Doe (ID=5)
INFO 2025-11-07 10:30:15,175 utils.fcm_helper 📤 Sending post notification to 15 device(s) for Post ID=42
INFO 2025-11-07 10:30:15,500 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:1234567890abcdef
INFO 2025-11-07 10:30:15,525 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:0987654321fedcba
INFO 2025-11-07 10:30:15,550 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:abcd1234efgh5678
...
WARNING 2025-11-07 10:30:16,100 utils.fcm_helper Invalid FCM token (unregistered): eXyZ789invalid...
INFO 2025-11-07 10:30:16,150 utils.fcm_helper ✅ POST NOTIFICATION SUCCESS: Post ID=42, Sent=14/15, Failed=1
WARNING 2025-11-07 10:30:16,151 utils.fcm_helper 🧹 Cleaning up 1 invalid tokens
INFO 2025-11-07 10:30:16,175 utils.fcm_helper Removed 1 invalid FCM tokens from database
```

---

## Scenario 2: Poll Created with Perfect Success

### What happens:
1. Instructor creates a poll
2. 20 users have FCM tokens
3. All 20 notifications sent successfully

### Log Output:
```
INFO 2025-11-07 11:15:30,456 feed.signals 📊 Signal triggered: New poll created (ID=15)
INFO 2025-11-07 11:15:30,457 feed.signals 📲 FCM notification scheduled for poll 15
INFO 2025-11-07 11:15:30,480 utils.fcm_helper 📊 POLL CREATED: Poll ID=15 by Jane Smith (ID=8)
INFO 2025-11-07 11:15:30,505 utils.fcm_helper 📤 Sending poll notification to 20 device(s) for Poll ID=15
INFO 2025-11-07 11:15:30,750 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:poll1234567
INFO 2025-11-07 11:15:30,775 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:poll2345678
...
INFO 2025-11-07 11:15:31,980 utils.fcm_helper ✅ POLL NOTIFICATION SUCCESS: Poll ID=15, Sent=20/20, Failed=0
```

---

## Scenario 3: Post with No Recipients

### What happens:
1. Instructor creates a post
2. No users have FCM tokens (or all users muted this instructor)
3. No notifications sent

### Log Output:
```
INFO 2025-11-07 12:00:00,123 feed.signals 📝 Signal triggered: New post created (ID=50)
INFO 2025-11-07 12:00:00,124 feed.signals 📲 FCM notification scheduled for post 50
INFO 2025-11-07 12:00:00,145 utils.fcm_helper 📝 POST CREATED: Post ID=50 by Alice Brown (ID=12)
WARNING 2025-11-07 12:00:00,170 utils.fcm_helper ❌ No FCM tokens found for post 50 - No recipients to notify
```

---

## Scenario 4: Firebase Initialization Error

### What happens:
1. Post created
2. Firebase service account file missing or invalid
3. Notification fails

### Log Output:
```
INFO 2025-11-07 13:30:15,789 feed.signals 📝 Signal triggered: New post created (ID=60)
INFO 2025-11-07 13:30:15,790 feed.signals 📲 FCM notification scheduled for post 60
INFO 2025-11-07 13:30:15,810 utils.fcm_helper 📝 POST CREATED: Post ID=60 by Bob Wilson (ID=20)
ERROR 2025-11-07 13:30:15,850 utils.fcm_helper Failed to initialize Firebase Admin SDK: [Errno 2] No such file or directory: '/path/to/firebase.json'
ERROR 2025-11-07 13:30:15,855 utils.fcm_helper Firebase initialization failed: [Errno 2] No such file or directory: '/path/to/firebase.json'
```

---

## Scenario 5: Multiple Invalid Tokens

### What happens:
1. Post created
2. 10 users have tokens
3. 5 tokens are invalid
4. 5 notifications succeed

### Log Output:
```
INFO 2025-11-07 14:00:00,100 feed.signals 📝 Signal triggered: New post created (ID=70)
INFO 2025-11-07 14:00:00,101 feed.signals 📲 FCM notification scheduled for post 70
INFO 2025-11-07 14:00:00,125 utils.fcm_helper 📝 POST CREATED: Post ID=70 by Carol Davis (ID=25)
INFO 2025-11-07 14:00:00,150 utils.fcm_helper 📤 Sending post notification to 10 device(s) for Post ID=70
INFO 2025-11-07 14:00:00,400 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:valid123
WARNING 2025-11-07 14:00:00,425 utils.fcm_helper Invalid FCM token (unregistered): invalid456
INFO 2025-11-07 14:00:00,450 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:valid789
WARNING 2025-11-07 14:00:00,475 utils.fcm_helper Invalid FCM token (unregistered): invalid012
INFO 2025-11-07 14:00:00,500 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:valid345
WARNING 2025-11-07 14:00:00,525 utils.fcm_helper Invalid FCM token (sender ID mismatch): wrongproject678
INFO 2025-11-07 14:00:00,550 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:valid901
WARNING 2025-11-07 14:00:00,575 utils.fcm_helper Invalid FCM token (unregistered): invalid234
INFO 2025-11-07 14:00:00,600 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:valid567
WARNING 2025-11-07 14:00:00,625 utils.fcm_helper Invalid FCM token (unregistered): invalid890
INFO 2025-11-07 14:00:00,650 utils.fcm_helper ✅ POST NOTIFICATION SUCCESS: Post ID=70, Sent=5/10, Failed=5
WARNING 2025-11-07 14:00:00,651 utils.fcm_helper 🧹 Cleaning up 5 invalid tokens
INFO 2025-11-07 14:00:00,680 utils.fcm_helper Removed 5 invalid FCM tokens from database
```

---

## Scenario 6: Signal Error

### What happens:
1. Post created
2. Error importing FCM helper
3. Signal catches error and logs it

### Log Output:
```
INFO 2025-11-07 15:00:00,200 feed.signals 📝 Signal triggered: New post created (ID=80)
ERROR 2025-11-07 15:00:00,250 feed.signals ❌ Failed to schedule FCM notification for post 80: No module named 'utils.fcm_helper'
Traceback (most recent call last):
  File "/path/to/feed/signals.py", line 95, in send_post_notification
    from utils.fcm_helper import send_post_notification as send_fcm_post
ModuleNotFoundError: No module named 'utils.fcm_helper'
```

---

## Scenario 7: Test Command Output

### Running test command:
```bash
$ python manage.py test_fcm --user-id 5
```

### Console Output:
```
Using token from user: john.doe@example.com
Sending test notification to token: dXyZ123abcdefghijk...
✅ Notification sent successfully!
   Success: 1
   Failed: 0

Check logs for details:
  - fcm_notifications.log (FCM-specific logs)
  - django.log (all logs)
```

### Log Output (`fcm_notifications.log`):
```
INFO 2025-11-07 16:00:00,500 utils.fcm_helper 📤 Sending test notification
INFO 2025-11-07 16:00:00,750 utils.fcm_helper Successfully sent FCM notification: projects/socalwelfare/messages/0:test12345
INFO 2025-11-07 16:00:00,755 utils.fcm_helper FCM notification batch result: {'success': True, 'success_count': 1, 'failed_count': 0, 'invalid_tokens': [], 'total': 1}
```

---

## Scenario 8: Complete All Failures

### What happens:
1. Post created
2. All tokens are invalid or network issues
3. Complete failure

### Log Output:
```
INFO 2025-11-07 17:00:00,100 feed.signals 📝 Signal triggered: New post created (ID=90)
INFO 2025-11-07 17:00:00,101 feed.signals 📲 FCM notification scheduled for post 90
INFO 2025-11-07 17:00:00,125 utils.fcm_helper 📝 POST CREATED: Post ID=90 by David Lee (ID=30)
INFO 2025-11-07 17:00:00,150 utils.fcm_helper 📤 Sending post notification to 5 device(s) for Post ID=90
WARNING 2025-11-07 17:00:00,400 utils.fcm_helper Invalid FCM token (unregistered): token1
WARNING 2025-11-07 17:00:00,425 utils.fcm_helper Invalid FCM token (unregistered): token2
WARNING 2025-11-07 17:00:00,450 utils.fcm_helper Invalid FCM token (unregistered): token3
WARNING 2025-11-07 17:00:00,475 utils.fcm_helper Invalid FCM token (unregistered): token4
WARNING 2025-11-07 17:00:00,500 utils.fcm_helper Invalid FCM token (unregistered): token5
ERROR 2025-11-07 17:00:00,525 utils.fcm_helper ❌ POST NOTIFICATION FAILED: Post ID=90, All 5 attempts failed
WARNING 2025-11-07 17:00:00,526 utils.fcm_helper 🧹 Cleaning up 5 invalid tokens
INFO 2025-11-07 17:00:00,550 utils.fcm_helper Removed 5 invalid FCM tokens from database
```

---

## Filtering Examples

### Show only post creations:
```bash
$ grep "POST CREATED" fcm_notifications.log
INFO 2025-11-07 10:30:15,150 utils.fcm_helper 📝 POST CREATED: Post ID=42 by John Doe (ID=5)
INFO 2025-11-07 12:00:00,145 utils.fcm_helper 📝 POST CREATED: Post ID=50 by Alice Brown (ID=12)
INFO 2025-11-07 14:00:00,125 utils.fcm_helper 📝 POST CREATED: Post ID=70 by Carol Davis (ID=25)
```

### Show only successes:
```bash
$ grep "SUCCESS" fcm_notifications.log
INFO 2025-11-07 10:30:16,150 utils.fcm_helper ✅ POST NOTIFICATION SUCCESS: Post ID=42, Sent=14/15, Failed=1
INFO 2025-11-07 11:15:31,980 utils.fcm_helper ✅ POLL NOTIFICATION SUCCESS: Poll ID=15, Sent=20/20, Failed=0
INFO 2025-11-07 14:00:00,650 utils.fcm_helper ✅ POST NOTIFICATION SUCCESS: Post ID=70, Sent=5/10, Failed=5
```

### Show only failures:
```bash
$ grep "FAILED" fcm_notifications.log
ERROR 2025-11-07 17:00:00,525 utils.fcm_helper ❌ POST NOTIFICATION FAILED: Post ID=90, All 5 attempts failed
```

### Count notifications by type:
```bash
$ grep -c "POST CREATED" fcm_notifications.log
15

$ grep -c "POLL CREATED" fcm_notifications.log
8
```

### Show today's activity:
```bash
$ grep "$(date +%Y-%m-%d)" fcm_notifications.log | grep -E "POST|POLL" | head -10
INFO 2025-11-07 10:30:15,150 utils.fcm_helper 📝 POST CREATED: Post ID=42 by John Doe (ID=5)
INFO 2025-11-07 11:15:30,480 utils.fcm_helper 📊 POLL CREATED: Poll ID=15 by Jane Smith (ID=8)
...
```

---

## Real-time Monitoring

### Watch logs live with color:
```bash
$ tail -f fcm_notifications.log | grep --color=always -E "POST|POLL|SUCCESS|FAILED|❌|✅"
```

### Output (colored in terminal):
```
INFO 2025-11-07 18:00:00,100 utils.fcm_helper 📝 POST CREATED: Post ID=100 by Emily Chen (ID=35)
INFO 2025-11-07 18:00:00,150 utils.fcm_helper 📤 Sending post notification to 25 device(s) for Post ID=100
INFO 2025-11-07 18:00:01,500 utils.fcm_helper ✅ POST NOTIFICATION SUCCESS: Post ID=100, Sent=25/25, Failed=0
```

---

These are the exact log formats you'll see in production! 🎯
