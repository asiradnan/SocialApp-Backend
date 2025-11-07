# FCM Quick Reference - API Endpoints

## Authentication
All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

## FCM Token Management

### Update FCM Token
```http
POST /api/users/fcm-token/
Content-Type: application/json

{
  "fcm_token": "your_device_fcm_token_here"
}
```

**Response (200 OK):**
```json
{
  "message": "FCM token updated successfully"
}
```

---

### Remove FCM Token (Logout)
```http
DELETE /api/users/fcm-token/
```

**Response (200 OK):**
```json
{
  "message": "FCM token removed successfully"
}
```

---

## Notification Preferences

### Get Muted Instructors
```http
GET /api/users/muted-instructors/
```

**Response (200 OK):**
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

---

### Mute an Instructor
```http
POST /api/users/muted-instructors/
Content-Type: application/json

{
  "instructor_id": 5
}
```

**Response (201 Created):**
```json
{
  "message": "Instructor muted successfully"
}
```

**Error (400 Bad Request) - Not an instructor:**
```json
{
  "instructor_id": ["This user is not an instructor"]
}
```

**Error (400 Bad Request) - Trying to mute self:**
```json
{
  "error": "You cannot mute yourself"
}
```

---

### Unmute an Instructor
```http
DELETE /api/users/muted-instructors/5/
```

**Response (200 OK):**
```json
{
  "message": "Instructor unmuted successfully"
}
```

**Error (404 Not Found):**
```json
{
  "error": "Instructor is not muted"
}
```

---

### Check Muted Status
```http
GET /api/users/muted-instructors/5/status/
```

**Response (200 OK):**
```json
{
  "is_muted": true,
  "instructor_id": 5
}
```

---

## Automatic Notifications

### When Post is Created
Automatic notification sent to all users who:
- Have FCM tokens
- Haven't muted the post author
- Are not the post author

**Notification Payload:**
```json
{
  "title": "New Post! 📝",
  "body": "John Doe just shared something new",
  "data": {
    "postId": "123",
    "type": "post",
    "authorId": "5",
    "authorName": "John Doe",
    "click_action": "OPEN_POST"
  }
}
```

### When Poll is Created
Automatic notification sent to eligible users

**Notification Payload:**
```json
{
  "title": "New Poll Available! 📊",
  "body": "John Doe just shared something new",
  "data": {
    "postId": "456",
    "type": "poll",
    "authorId": "5",
    "authorName": "John Doe",
    "click_action": "OPEN_POST"
  }
}
```

---

## Testing

### Using cURL

**Update FCM Token:**
```bash
curl -X POST http://localhost:8000/api/users/fcm-token/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fcm_token": "test_token_12345"}'
```

**Mute Instructor:**
```bash
curl -X POST http://localhost:8000/api/users/muted-instructors/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"instructor_id": 5}'
```

**Unmute Instructor:**
```bash
curl -X DELETE http://localhost:8000/api/users/muted-instructors/5/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Check Muted Status:**
```bash
curl -X GET http://localhost:8000/api/users/muted-instructors/5/status/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Android Integration Example

### Store FCM Token
```kotlin
// Get FCM token
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (task.isSuccessful) {
        val token = task.result
        
        // Send to backend
        apiService.updateFCMToken(FCMTokenRequest(token))
            .enqueue(object : Callback<ApiResponse> {
                override fun onResponse(call: Call<ApiResponse>, response: Response<ApiResponse>) {
                    if (response.isSuccessful) {
                        Log.d("FCM", "Token updated successfully")
                    }
                }
                
                override fun onFailure(call: Call<ApiResponse>, t: Throwable) {
                    Log.e("FCM", "Failed to update token", t)
                }
            })
    }
}
```

### Handle Token Refresh
```kotlin
class MyFirebaseMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        
        // Send new token to backend
        apiService.updateFCMToken(FCMTokenRequest(token))
    }
    
    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        
        // Handle notification
        val data = message.data
        val postId = data["postId"]
        val type = data["type"]
        
        // Navigate to post/poll
        when (type) {
            "post" -> navigateToPost(postId)
            "poll" -> navigateToPoll(postId)
        }
    }
}
```

---

## Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created (resource created successfully) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid/missing token) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Error Handling

All error responses follow this format:
```json
{
  "error": "Error message here"
}
```

Or for validation errors:
```json
{
  "field_name": ["Error message for this field"]
}
```
