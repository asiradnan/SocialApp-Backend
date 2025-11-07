# Firebase Cloud Messaging (FCM) Integration - Django Backend

## ✅ Implementation Complete!

This document describes the FCM push notification system that has been implemented in your Django SocialBackend project.

## 🚀 What Was Implemented

### 1. Database Changes
- **`fcm_token` field** added to `CustomUser` model to store device tokens
- **`MutedInstructor` model** created to allow users to mute notifications from specific instructors
- Migrations created and applied successfully

### 2. Firebase Configuration
- Firebase Admin SDK installed (`firebase-admin`)
- Service account credentials configured in `settings.py`
- FCM helper utilities created in `utils/fcm_helper.py`

### 3. API Endpoints Created

#### FCM Token Management
- **POST** `/api/users/fcm-token/` - Update FCM token
  ```json
  {
    "fcm_token": "device_fcm_token_here"
  }
  ```

- **DELETE** `/api/users/fcm-token/` - Remove FCM token (for logout)

#### Notification Preferences
- **GET** `/api/users/muted-instructors/` - Get list of muted instructors
- **POST** `/api/users/muted-instructors/` - Mute an instructor
  ```json
  {
    "instructor_id": 123
  }
  ```

- **DELETE** `/api/users/muted-instructors/{instructor_id}/` - Unmute an instructor
- **GET** `/api/users/muted-instructors/{instructor_id}/status/` - Check if instructor is muted

### 4. Automatic Notifications
- **New Post**: Notifications sent automatically when instructors create posts
- **New Poll**: Notifications sent automatically when instructors create polls
- **Smart Filtering**: Notifications exclude:
  - The post/poll author
  - Users who have muted that instructor
  - Users without FCM tokens

### 5. Admin Interface
- CustomUser admin now shows "Has FCM Token" status
- New admin interface for managing MutedInstructor relationships
- Enhanced user management with notification preferences

## 📱 How It Works

### 1. When a User Opens the App (Android)
The Android app should:
1. Request FCM token from Firebase
2. Send the token to the backend:
```kotlin
// In your Android app
val token = FirebaseMessaging.getInstance().token.await()

// Send to backend
api.updateFCMToken(token)
```

### 2. When an Instructor Creates Content
1. Instructor creates a post or poll
2. Django signal triggers after creation
3. FCM notification sent to all eligible users
4. Invalid tokens automatically cleaned up

### 3. When a User Wants to Mute Notifications
```kotlin
// In your Android app
api.muteInstructor(instructorId)
```

## 🔧 FCM Helper Functions

Located in `utils/fcm_helper.py`:

### `send_post_notification(post, author)`
Sends notification for new posts
```python
from utils.fcm_helper import send_post_notification

result = send_post_notification(post_instance, author_instance)
```

### `send_poll_notification(poll, author)`
Sends notification for new polls
```python
from utils.fcm_helper import send_poll_notification

result = send_poll_notification(poll_instance, author_instance)
```

### `send_fcm_notification(tokens, title, body, data)`
Generic FCM notification sender
```python
from utils.fcm_helper import send_fcm_notification

result = send_fcm_notification(
    tokens=['token1', 'token2'],
    title='Notification Title',
    body='Notification message',
    data={'key': 'value'}
)
```

### `test_fcm_notification(token, title, body)`
Test notifications to a specific device
```python
from utils.fcm_helper import test_fcm_notification

result = test_fcm_notification(
    token='device_token',
    title='Test',
    body='This is a test'
)
```

## 🧪 Testing Your Implementation

### Step 1: Update Requirements
```bash
pip freeze > requirements.txt
```

### Step 2: Test FCM Token Update
```bash
curl -X POST http://localhost:8000/api/users/fcm-token/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fcm_token": "test_token_12345"}'
```

### Step 3: Test Muting an Instructor
```bash
curl -X POST http://localhost:8000/api/users/muted-instructors/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"instructor_id": 1}'
```

### Step 4: Create a Test Post/Poll
When an instructor creates content, check the Django logs for:
```
INFO FCM notification batch result: {'success': True, 'success_count': 5, ...}
```

### Step 5: Test Notification in Django Shell
```bash
python manage.py shell
```

```python
from utils.fcm_helper import test_fcm_notification

# Get a user's FCM token from database
from users.models import CustomUser
user = CustomUser.objects.filter(fcm_token__isnull=False).first()

if user and user.fcm_token:
    result = test_fcm_notification(
        token=user.fcm_token,
        title="Test Notification",
        body="If you see this, FCM is working!"
    )
    print(result)
```

## 📋 API Response Examples

### FCM Token Update - Success
```json
{
  "message": "FCM token updated successfully"
}
```

### Mute Instructor - Success
```json
{
  "message": "Instructor muted successfully"
}
```

### Get Muted Instructors
```json
[
  {
    "id": 1,
    "instructor": 5,
    "instructor_name": "John Doe",
    "instructor_email": "john@example.com",
    "muted_at": "2025-11-07T10:30:00Z"
  }
]
```

### Check Muted Status
```json
{
  "is_muted": true,
  "instructor_id": 5
}
```

## 🔐 Security Notes

### Service Account Credentials
- ✅ Service account JSON file added to `.gitignore`
- ⚠️ **NEVER commit this file to Git!**
- 📁 File location: `/socalwelfare-firebase-adminsdk-fbsvc-5f4cf67c25.json`

### Production Deployment
When deploying to production:
1. Upload the service account JSON to your server (outside web root)
2. Update `settings.py` to use environment variable:
```python
FIREBASE_CONFIG = {
    'SERVICE_ACCOUNT_KEY_PATH': os.getenv(
        'FIREBASE_SERVICE_ACCOUNT_PATH',
        BASE_DIR / 'socalwelfare-firebase-adminsdk-fbsvc-5f4cf67c25.json'
    ),
    'PROJECT_ID': 'socalwelfare',
}
```
3. Set proper file permissions: `chmod 600 firebase-service-account.json`

## 🐛 Troubleshooting

### Firebase Not Initializing
**Problem**: `Firebase Admin SDK initialization failed`
**Solution**: 
- Check service account file path in `settings.py`
- Verify file permissions
- Check Firebase Console for project ID

### Notifications Not Received
**Problem**: Users not receiving notifications
**Solution**:
1. Check if user has FCM token: `python manage.py shell`
   ```python
   from users.models import CustomUser
   CustomUser.objects.filter(fcm_token__isnull=False).count()
   ```
2. Check Django logs for FCM errors
3. Verify Firebase project settings
4. Test with Firebase Console → Cloud Messaging → Send test message

### Invalid Tokens
**Problem**: `invalid_tokens` in response
**Solution**: 
- Tokens automatically cleaned up by the system
- User may have uninstalled/reinstalled app
- Token needs to be refreshed

### Permission Errors
**Problem**: `Service account does not have permission`
**Solution**:
- Go to Firebase Console → Project Settings → Service Accounts
- Verify service account has "Firebase Cloud Messaging Admin" role
- Re-download service account key if necessary

## 📊 Monitoring

### Check FCM Token Statistics
```python
from users.models import CustomUser

total_users = CustomUser.objects.count()
users_with_tokens = CustomUser.objects.filter(fcm_token__isnull=False).count()

print(f"Total users: {total_users}")
print(f"Users with FCM tokens: {users_with_tokens}")
print(f"Percentage: {(users_with_tokens/total_users)*100:.1f}%")
```

### Check Muted Relationships
```python
from users.models import MutedInstructor

total_mutes = MutedInstructor.objects.count()
users_muting = MutedInstructor.objects.values('user').distinct().count()

print(f"Total mute relationships: {total_mutes}")
print(f"Users who muted someone: {users_muting}")
```

## 📦 Files Modified/Created

### New Files
- `utils/fcm_helper.py` - FCM notification utilities
- `users/migrations/0008_customuser_fcm_token_mutedinstructor.py` - Database migration

### Modified Files
- `users/models.py` - Added fcm_token field and MutedInstructor model
- `users/serializers.py` - Added FCM and muting serializers
- `users/views.py` - Added FCM and notification preference views
- `users/urls.py` - Added new API endpoints
- `users/admin.py` - Added MutedInstructor admin and FCM token display
- `feed/signals.py` - Added FCM notification triggers
- `SocialBackend/settings.py` - Added Firebase configuration
- `.gitignore` - Added service account file patterns

## 🎯 Next Steps

1. **Android Integration**: Update your Android app to:
   - Request FCM token on app startup
   - Send token to backend via `/api/users/fcm-token/`
   - Handle incoming notifications
   - Implement "Mute Instructor" UI

2. **Testing**: Test notifications with real devices

3. **Production**: Deploy with proper security measures

4. **Monitoring**: Set up logging/monitoring for FCM success rates

## 💡 Tips

- Firebase Admin SDK automatically handles token caching and refresh
- Notifications are sent in background (won't block API responses)
- Invalid tokens are automatically removed from database
- Use `transaction.on_commit()` to ensure notifications sent after DB commit
- Check Django logs for detailed FCM operation information

## 📞 Support

If you encounter issues:
1. Check Django logs: `tail -f django.log`
2. Check Firebase Console → Cloud Messaging → Reports
3. Test with Firebase Console → Send test message
4. Verify service account permissions in Firebase Console

---

**Implementation Date**: November 7, 2025
**Django Version**: 5.2.3
**Firebase Admin SDK Version**: 7.1.0
**Project**: SocialBackend
