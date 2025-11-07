# Firebase Cloud Messaging (FCM) Setup Guide

## Part 1: Firebase Console Setup (IMPORTANT - DO THIS FIRST!)

### Step 1: Access Firebase Console
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Sign in with your Google account
3. Find your existing project OR create a new one

### Step 2: Enable Firebase Cloud Messaging
1. Click on your project
2. In the left sidebar, click on **"Build"** → **"Cloud Messaging"**
3. You should see the Cloud Messaging dashboard

### Step 3: Get Your Service Account Key (CRITICAL!) - HTTP v1 API
Since the legacy API is deprecated, we'll use the modern HTTP v1 API which is more secure.

1. Click on the **Settings gear icon** (⚙️) → **Project settings**
2. Go to the **"Service accounts"** tab
3. Click **"Generate new private key"** button
4. Click **"Generate key"** in the confirmation dialog
5. A JSON file will download - **SAVE THIS FILE SECURELY!**
   - File name: `your-project-id-firebase-adminsdk-xxxxx.json`
   - **NEVER commit this to Git!**
   - Contains your private key credentials
6. Also note your **"Project ID"** from General tab (you'll need this!)

#### **🔒 Securing Your Service Account JSON:**

**On Your Server:**
- Upload the JSON file to a directory **outside** your web root (not publicly accessible)
- Example path: `/var/secrets/firebase-service-account.json` (NOT in `/var/www/html/`)
- Set proper file permissions:
  ```bash
  chmod 600 /var/secrets/firebase-service-account.json
  chown www-data:www-data /var/secrets/firebase-service-account.json
  ```

**Never Commit to Git:**
Add to your `.gitignore`:
```gitignore
# Firebase Service Account
firebase-service-account.json
*-firebase-adminsdk-*.json
```

**For Local Development:**
- Store in project root but **outside** public directory
- Use environment variables for the path:
  ```php
  // In your PHP files
  define('SERVICE_ACCOUNT_PATH', 
      getenv('FIREBASE_SERVICE_ACCOUNT_PATH') ?: __DIR__ . '/../firebase-service-account.json'
  );
  ```

### Step 4: Download google-services.json (If not already done)
1. In Project Settings → General tab
2. Scroll down to "Your apps" section
3. If you don't see your Android app:
   - Click "Add app" → Android icon
   - Enter package name: `com.asiradnan.socialwelfare`
   - Register app
4. Download `google-services.json`
5. Place it in: `app/google-services.json` (You already have this!)

---

## Part 2: Database Schema Changes

Run these SQL commands on your MySQL/MariaDB database:

```sql
-- Add FCM token column to users table
ALTER TABLE users ADD COLUMN fcm_token VARCHAR(255) NULL AFTER profile_picture_url;
CREATE INDEX idx_fcm_token ON users(fcm_token);

-- Create muted_instructors table
CREATE TABLE IF NOT EXISTS muted_instructors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    instructor_id INT NOT NULL,
    muted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (instructor_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_mute (user_id, instructor_id)
);

CREATE INDEX idx_user_mutes ON muted_instructors(user_id);
CREATE INDEX idx_instructor_muted ON muted_instructors(instructor_id);
```

---

## Part 3: Backend PHP Scripts

Create these PHP files in your backend:

### 1. `update_fcm_token.php`
```php
<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST");
header("Access-Control-Allow-Headers: Content-Type, Authorization");

require_once 'db_connect.php';

// Get JSON input
$json = file_get_contents('php://input');
$data = json_decode($json, true);

$fcm_token = $data['fcm_token'] ?? null;

// Get user_id from JWT token (assuming you have auth middleware)
// For now, you might pass it as parameter
$user_id = $data['user_id'] ?? null;

if ($user_id && $fcm_token) {
    $stmt = $conn->prepare("UPDATE users SET fcm_token = ? WHERE user_id = ?");
    $stmt->bind_param("si", $fcm_token, $user_id);
    
    if ($stmt->execute()) {
        echo json_encode([
            "success" => true,
            "message" => "FCM token updated successfully"
        ]);
    } else {
        echo json_encode([
            "success" => false,
            "message" => "Failed to update FCM token"
        ]);
    }
    $stmt->close();
} else {
    echo json_encode([
        "success" => false,
        "message" => "Missing user_id or fcm_token"
    ]);
}

$conn->close();
?>
```

### 2. `get_notification_settings.php`
```php
<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once 'db_connect.php';

$user_id = $_GET['user_id'] ?? null;
$instructor_id = $_GET['instructor_id'] ?? null;

if ($user_id && $instructor_id) {
    $stmt = $conn->prepare("SELECT COUNT(*) as is_muted FROM muted_instructors WHERE user_id = ? AND instructor_id = ?");
    $stmt->bind_param("ii", $user_id, $instructor_id);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result->fetch_assoc();
    
    echo json_encode([
        "is_muted" => $row['is_muted'] > 0
    ]);
    $stmt->close();
} else {
    echo json_encode(["is_muted" => false]);
}

$conn->close();
?>
```

### 3. `mute_instructor.php`
```php
<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once 'db_connect.php';

$user_id = $_GET['user_id'] ?? null;
$instructor_id = $_GET['instructor_id'] ?? null;

if ($user_id && $instructor_id) {
    $stmt = $conn->prepare("INSERT IGNORE INTO muted_instructors (user_id, instructor_id) VALUES (?, ?)");
    $stmt->bind_param("ii", $user_id, $instructor_id);
    
    if ($stmt->execute()) {
        echo json_encode([
            "success" => true,
            "message" => "Instructor muted successfully"
        ]);
    } else {
        echo json_encode([
            "success" => false,
            "message" => "Failed to mute instructor"
        ]);
    }
    $stmt->close();
} else {
    echo json_encode([
        "success" => false,
        "message" => "Missing parameters"
    ]);
}

$conn->close();
?>
```

### 4. `unmute_instructor.php`
```php
<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once 'db_connect.php';

$user_id = $_GET['user_id'] ?? null;
$instructor_id = $_GET['instructor_id'] ?? null;

if ($user_id && $instructor_id) {
    $stmt = $conn->prepare("DELETE FROM muted_instructors WHERE user_id = ? AND instructor_id = ?");
    $stmt->bind_param("ii", $user_id, $instructor_id);
    
    if ($stmt->execute()) {
        echo json_encode([
            "success" => true,
            "message" => "Instructor unmuted successfully"
        ]);
    } else {
        echo json_encode([
            "success" => false,
            "message" => "Failed to unmute instructor"
        ]);
    }
    $stmt->close();
} else {
    echo json_encode([
        "success" => false,
        "message" => "Missing parameters"
    ]);
}

$conn->close();
?>
```

### 5. `fcm_helper.php` (Helper functions for sending FCM using HTTP v1 API)
```php
<?php

/**
 * Get OAuth2 Access Token from Service Account JSON
 * This token is needed for Firebase HTTP v1 API
 */
function getAccessToken($serviceAccountPath) {
    // Read service account JSON
    if (!file_exists($serviceAccountPath)) {
        return ['success' => false, 'error' => 'Service account file not found'];
    }
    
    $serviceAccount = json_decode(file_get_contents($serviceAccountPath), true);
    
    if (!$serviceAccount) {
        return ['success' => false, 'error' => 'Invalid service account JSON'];
    }
    
    // JWT header
    $header = json_encode([
        'alg' => 'RS256',
        'typ' => 'JWT'
    ]);
    
    // JWT claims
    $now = time();
    $claims = json_encode([
        'iss' => $serviceAccount['client_email'],
        'scope' => 'https://www.googleapis.com/auth/firebase.messaging',
        'aud' => 'https://oauth2.googleapis.com/token',
        'iat' => $now,
        'exp' => $now + 3600
    ]);
    
    // Create JWT
    $base64UrlHeader = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($header));
    $base64UrlClaims = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($claims));
    
    $signature = '';
    openssl_sign(
        $base64UrlHeader . '.' . $base64UrlClaims,
        $signature,
        $serviceAccount['private_key'],
        'SHA256'
    );
    
    $base64UrlSignature = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($signature));
    $jwt = $base64UrlHeader . '.' . $base64UrlClaims . '.' . $base64UrlSignature;
    
    // Exchange JWT for access token
    $ch = curl_init('https://oauth2.googleapis.com/token');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query([
        'grant_type' => 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion' => $jwt
    ]));
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode !== 200) {
        return ['success' => false, 'error' => 'Failed to get access token', 'response' => $response];
    }
    
    $tokenData = json_decode($response, true);
    return [
        'success' => true,
        'access_token' => $tokenData['access_token'],
        'expires_in' => $tokenData['expires_in']
    ];
}

/**
 * Send FCM notification using HTTP v1 API
 * @param string $projectId Your Firebase Project ID
 * @param string $serviceAccountPath Path to service account JSON file
 * @param array $fcmTokens Array of FCM device tokens
 * @param string $title Notification title
 * @param string $body Notification body
 * @param array $data Additional data payload
 * @return array Response from FCM server
 */
function sendFCMNotificationV1($projectId, $serviceAccountPath, $fcmTokens, $title, $body, $data = []) {
    if (empty($fcmTokens)) {
        return ['success' => false, 'message' => 'No FCM tokens provided'];
    }
    
    // Get access token
    $tokenResult = getAccessToken($serviceAccountPath);
    if (!$tokenResult['success']) {
        return $tokenResult;
    }
    
    $accessToken = $tokenResult['access_token'];
    
    // FCM v1 endpoint
    $url = "https://fcm.googleapis.com/v1/projects/{$projectId}/messages:send";
    
    $successCount = 0;
    $failedCount = 0;
    $invalidTokens = [];
    
    // Send to each token individually (required for v1 API)
    foreach ($fcmTokens as $token) {
        // Build message
        $message = [
            'message' => [
                'token' => $token,
                'notification' => [
                    'title' => $title,
                    'body' => $body
                ],
                'data' => array_map('strval', $data), // All data values must be strings
                'android' => [
                    'priority' => 'high',
                    'notification' => [
                        'sound' => 'default',
                        'color' => '#2196F3',
                        'icon' => 'ic_notification',
                        'click_action' => 'OPEN_POST'
                    ]
                ]
            ]
        ];
        
        // Set headers
        $headers = [
            'Authorization: Bearer ' . $accessToken,
            'Content-Type: application/json'
        ];
        
        // Send request
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($message));
        
        $result = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        
        if (curl_errno($ch)) {
            $failedCount++;
            error_log("FCM cURL Error: " . curl_error($ch));
        } else if ($httpCode === 200) {
            $successCount++;
        } else {
            $failedCount++;
            $response = json_decode($result, true);
            
            // Check if token is invalid and should be removed
            if (isset($response['error']['status']) && 
                ($response['error']['status'] === 'NOT_FOUND' || 
                 $response['error']['status'] === 'INVALID_ARGUMENT')) {
                $invalidTokens[] = $token;
            }
            
            error_log("FCM Error for token: HTTP $httpCode - " . $result);
        }
        
        curl_close($ch);
        
        // Small delay to avoid rate limiting
        usleep(10000); // 10ms
    }
    
    return [
        'success' => $successCount > 0,
        'success_count' => $successCount,
        'failed_count' => $failedCount,
        'invalid_tokens' => $invalidTokens,
        'total' => count($fcmTokens)
    ];
}

/**
 * Clean up invalid FCM tokens from database
 * @param mysqli $conn Database connection
 * @param array $invalidTokens Array of invalid tokens
 */
function removeInvalidFCMTokens($conn, $invalidTokens) {
    if (empty($invalidTokens)) {
        return;
    }
    
    $placeholders = implode(',', array_fill(0, count($invalidTokens), '?'));
    $stmt = $conn->prepare("UPDATE users SET fcm_token = NULL WHERE fcm_token IN ($placeholders)");
    
    $types = str_repeat('s', count($invalidTokens));
    $stmt->bind_param($types, ...$invalidTokens);
    $stmt->execute();
    $stmt->close();
    
    error_log("Removed " . count($invalidTokens) . " invalid FCM tokens");
}

?>
```

### 6. Update your post/poll creation scripts

In your `create_post.php` and `create_poll.php`, add this after successful creation:

```php
// ... existing post/poll creation code ...

if ($post_created_successfully) {
    // IMPORTANT: Set your Firebase Project ID and Service Account path
    define('FIREBASE_PROJECT_ID', 'your-project-id'); // Get from Firebase Console
    define('SERVICE_ACCOUNT_PATH', __DIR__ . '/firebase-service-account.json');
    
    // Include FCM helper
    require_once 'fcm_helper.php';
    
    // Get the author's info
    $author_id = $_POST['user_id']; // or from JWT token
    $author_name = $_POST['author_name'] ?? 'Someone';
    
    // Get all active FCM tokens EXCEPT:
    // 1. The post author
    // 2. Users who muted this instructor
    $stmt = $conn->prepare("
        SELECT u.fcm_token 
        FROM users u
        WHERE u.user_id != ? 
        AND u.fcm_token IS NOT NULL
        AND u.fcm_token != ''
        AND NOT EXISTS (
            SELECT 1 FROM muted_instructors m 
            WHERE m.user_id = u.user_id 
            AND m.instructor_id = ?
        )
    ");
    $stmt->bind_param("ii", $author_id, $author_id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    $tokens = [];
    while ($row = $result->fetch_assoc()) {
        $tokens[] = $row['fcm_token'];
    }
    $stmt->close();
    
    // Send notification if there are tokens
    if (!empty($tokens)) {
        $contentType = $is_poll ? 'poll' : 'post';
        $title = $is_poll ? "New Poll Available! 📊" : "New Post! 📝";
        $body = "$author_name just shared something new";
        
        $data = [
            'postId' => (string)$post_id,
            'type' => $contentType,
            'authorId' => (string)$author_id,
            'authorName' => $author_name,
            'click_action' => 'OPEN_POST'
        ];
        
        // Send notification using HTTP v1 API
        $fcmResult = sendFCMNotificationV1(
            FIREBASE_PROJECT_ID,
            SERVICE_ACCOUNT_PATH,
            $tokens,
            $title,
            $body,
            $data
        );
        
        // Clean up invalid tokens
        if (isset($fcmResult['invalid_tokens']) && !empty($fcmResult['invalid_tokens'])) {
            removeInvalidFCMTokens($conn, $fcmResult['invalid_tokens']);
        }
        
        // Log result (optional)
        error_log("FCM Notification sent: " . json_encode($fcmResult));
    }
}
```

---

## Part 4: Testing Your Setup

### Test FCM using Firebase Console (Composer):
1. Go to Firebase Console → **Engage** → **Messaging**
2. Click **"Create your first campaign"** or **"New campaign"**
3. Select **"Firebase Notification messages"**
4. Enter notification title and text
5. Click **"Send test message"**
6. Enter your device's FCM token (you'll see this in your app's Logcat)
7. Click **"Test"**

### Check if notifications are working:
1. Run your app on a physical device (recommended) or emulator
2. Check Logcat for: `FCM Token: xxxxxxxxxxxxx`
3. Copy that token
4. Use Firebase Console → Messaging → Send test message
5. Paste the token and send
6. You should receive a notification on your device!

### Testing Your PHP Backend:
1. Create a simple test script `test_fcm.php`:
```php
<?php
require_once 'fcm_helper.php';

define('FIREBASE_PROJECT_ID', 'your-project-id');
define('SERVICE_ACCOUNT_PATH', __DIR__ . '/firebase-service-account.json');

// Get test token from your device's Logcat
$testToken = 'YOUR_DEVICE_FCM_TOKEN_HERE';

$result = sendFCMNotificationV1(
    FIREBASE_PROJECT_ID,
    SERVICE_ACCOUNT_PATH,
    [$testToken],
    'Test Notification',
    'If you see this, your backend is working!',
    ['test' => 'true']
);

echo json_encode($result, JSON_PRETTY_PRINT);
?>
```

2. Run: `php test_fcm.php`
3. Check your device for the notification

---

## Part 5: Production Optimizations

### OAuth2 Token Caching (RECOMMENDED!)
Access tokens expire after 1 hour. Generating new ones for every notification is inefficient. Here's how to cache them:

#### File-Based Caching (Simple):
```php
<?php
// Add this to fcm_helper.php

/**
 * Get cached OAuth2 token or generate new one if expired
 */
function getCachedAccessToken($serviceAccountPath) {
    $cacheFile = sys_get_temp_dir() . '/fcm_access_token.cache';
    
    // Check if cache exists and is valid
    if (file_exists($cacheFile)) {
        $cacheData = json_decode(file_get_contents($cacheFile), true);
        $expiresAt = $cacheData['expires_at'] ?? 0;
        
        // If token hasn't expired (with 5-minute buffer)
        if ($expiresAt > time() + 300) {
            return [
                'success' => true,
                'access_token' => $cacheData['access_token'],
                'from_cache' => true
            ];
        }
    }
    
    // Generate new token
    $tokenResult = getAccessToken($serviceAccountPath);
    
    if ($tokenResult['success']) {
        // Cache the token
        $cacheData = [
            'access_token' => $tokenResult['access_token'],
            'expires_at' => time() + ($tokenResult['expires_in'] ?? 3600)
        ];
        file_put_contents($cacheFile, json_encode($cacheData));
        chmod($cacheFile, 0600); // Secure permissions
    }
    
    return $tokenResult;
}

// Update sendFCMNotificationV1() to use cached token:
// Replace this line:
//   $tokenResult = getAccessToken($serviceAccountPath);
// With:
//   $tokenResult = getCachedAccessToken($serviceAccountPath);
```

#### Alternative: Use Google's Official Library
For production, consider using the official `google/apiclient` library:

```bash
composer require google/apiclient
```

Then update `fcm_helper.php`:
```php
<?php
require 'vendor/autoload.php';

use Google\Client as GoogleClient;

function getAccessTokenUsingLibrary($serviceAccountPath) {
    $client = new GoogleClient();
    $client->setAuthConfig($serviceAccountPath);
    $client->addScope('https://www.googleapis.com/auth/firebase.messaging');
    
    $token = $client->fetchAccessTokenWithAssertion();
    
    return [
        'success' => isset($token['access_token']),
        'access_token' => $token['access_token'] ?? null,
        'error' => $token['error'] ?? null
    ];
}
```

This library handles caching automatically!

---

## Important Notes:

1. **FCM HTTP v1 API**: The modern API using OAuth2 with service accounts (more secure than legacy server key)
2. **Service Account Security**: Keep your `firebase-service-account.json` secure, never commit to Git! Add to `.gitignore`
3. **Token Refresh**: FCM tokens can change, always handle `onNewToken()` callback
4. **Notification Permission**: Android 13+ requires `POST_NOTIFICATIONS` runtime permission
5. **Background vs Foreground**: Notifications behave differently:
   - **Background/Killed**: System tray notification automatically shown
   - **Foreground**: Your `onMessageReceived()` handles it
6. **Token Caching**: OAuth2 access tokens expire after 1 hour, implement caching for production
7. **Rate Limiting**: Add small delays between notifications to avoid hitting FCM rate limits

---

## Part 6: Troubleshooting & Migration Guide

### Common Issues & Solutions:

**Issue**: "Failed to get access token"
- **Solution**: Check service account JSON file path is correct
- Verify file permissions (should be readable by PHP: `chmod 600`)
- Ensure JSON file is valid and not corrupted
- Check error logs for detailed OAuth2 errors

**Issue**: "HTTP 401 Unauthorized" when sending notifications
- **Solution**: Access token expired or invalid
- Implement token caching (see Part 5 above)
- Verify service account has "Firebase Cloud Messaging Admin" role in IAM

**Issue**: "HTTP 404 Project Not Found"
- **Solution**: Verify `FIREBASE_PROJECT_ID` matches your actual project ID
- Check Firebase Console → Project Settings → General → "Project ID"
- Common mistake: using Project Name instead of Project ID

**Issue**: Not receiving notifications on device
- **Solution**: Check if FCM token is saved in database correctly
- Verify device has granted notification permission (Android 13+)
- Test with Firebase Console first to isolate backend issues
- Check device has active internet connection
- Review Logcat for error messages

**Issue**: Token not generated in Android app
- **Solution**: Check `google-services.json` is in `app/` directory
- Verify Firebase project is properly configured
- Check app package name matches Firebase project registration
- Rebuild the app after adding/updating `google-services.json`
- Clear app data and reinstall if necessary

**Issue**: Notifications work in foreground but not background
- **Solution**: This is expected FCM behavior!
- **Foreground**: Your `onMessageReceived()` handles display
- **Background/Killed**: System automatically displays notification
- Ensure you're sending BOTH `notification` and `data` payloads

**Issue**: "Invalid registration token" or "NOT_FOUND" error
- **Solution**: FCM token has expired or been invalidated
- User may have uninstalled/reinstalled app
- Token refresh is needed (handled by `onNewToken()`)
- The `removeInvalidFCMTokens()` function auto-removes invalid tokens

**Issue**: "Service account does not have permission"
- **Solution**: Go to Firebase Console → IAM & Admin
- Verify service account email has proper roles
- Should have "Firebase Cloud Messaging Admin" role
- May need to wait a few minutes for permissions to propagate

---

### Migration Guide: Legacy API → HTTP v1

If you have existing code using the **deprecated legacy API**, follow these steps to migrate:

#### Step 1: Download Service Account JSON
- Follow **Part 1, Step 3** above to download your service account key
- Save it securely outside your web root

#### Step 2: Update `fcm_helper.php`
- Replace the old `sendFCMNotification()` function
- Use the new `sendFCMNotificationV1()` function from this guide
- Add the `getAccessToken()` helper function
- Optional: Add `getCachedAccessToken()` for performance

#### Step 3: Update All Function Calls
```php
// ❌ Old way (legacy API - DEPRECATED):
sendFCMNotification($tokens, $title, $body, $data);

// ✅ New way (HTTP v1 API):
sendFCMNotificationV1(
    FIREBASE_PROJECT_ID,
    SERVICE_ACCOUNT_PATH,
    $tokens,
    $title,
    $body,
    $data
);
```

#### Step 4: Add Configuration Constants
At the top of files that send notifications:
```php
define('FIREBASE_PROJECT_ID', 'your-actual-project-id'); // From Firebase Console
define('SERVICE_ACCOUNT_PATH', '/var/secrets/firebase-service-account.json');
```

#### Step 5: Update Include Statements
Make sure all PHP files that send notifications include the updated helper:
```php
require_once 'fcm_helper.php';
```

#### Step 6: Test Thoroughly
1. Use `test_fcm.php` to verify backend works
2. Send test notifications from Firebase Console → Messaging
3. Test with real app usage scenarios
4. Monitor error logs for any issues

#### Step 7: Clean Up Legacy Code
- Remove old `$serverKey` variable references
- Delete legacy API endpoint URL (`https://fcm.googleapis.com/fcm/send`)
- Remove unused authorization headers (`Authorization: key=...`)

---

## Need Help?

- **Firebase HTTP v1 API Migration**: https://firebase.google.com/docs/cloud-messaging/migrate-v1
- **Android FCM Client Setup**: https://firebase.google.com/docs/cloud-messaging/android/client
- **Service Account Authentication**: https://firebase.google.com/docs/admin/setup#initialize-sdk
- **FCM Server Reference**: https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages
