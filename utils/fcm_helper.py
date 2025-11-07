"""
Firebase Cloud Messaging (FCM) Utilities
Handles sending push notifications to Android devices
"""

import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
_firebase_app = None


def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials"""
    global _firebase_app
    
    if _firebase_app is None:
        try:
            cred = credentials.Certificate(str(settings.FIREBASE_CONFIG['SERVICE_ACCOUNT_KEY_PATH']))
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
            raise
    
    return _firebase_app


def send_fcm_notification(tokens, title, body, data=None):
    """
    Send FCM notification to multiple devices
    
    Args:
        tokens (list): List of FCM device tokens
        title (str): Notification title
        body (str): Notification body
        data (dict): Additional data payload (optional)
    
    Returns:
        dict: Result with success/failure counts and invalid tokens
    """
    if not tokens:
        return {
            'success': False,
            'message': 'No FCM tokens provided',
            'success_count': 0,
            'failed_count': 0,
            'invalid_tokens': []
        }
    
    # Ensure Firebase is initialized
    try:
        initialize_firebase()
    except Exception as e:
        logger.error(f"Firebase initialization failed: {str(e)}")
        return {
            'success': False,
            'message': f'Firebase initialization failed: {str(e)}',
            'success_count': 0,
            'failed_count': len(tokens),
            'invalid_tokens': []
        }
    
    # Prepare notification data
    if data is None:
        data = {}
    
    # Convert all data values to strings (FCM requirement)
    data = {k: str(v) for k, v in data.items()}
    
    # Build notification
    notification = messaging.Notification(
        title=title,
        body=body
    )
    
    # Android-specific configuration
    android_config = messaging.AndroidConfig(
        priority='high',
        notification=messaging.AndroidNotification(
            sound='default',
            color='#2196F3',
            icon='ic_notification',
            click_action='OPEN_POST'
        )
    )
    
    success_count = 0
    failed_count = 0
    invalid_tokens = []
    
    # Send to each token (FCM v1 API requires individual sends for multicast)
    for token in tokens:
        try:
            message = messaging.Message(
                token=token,
                notification=notification,
                data=data,
                android=android_config
            )
            
            response = messaging.send(message)
            success_count += 1
            logger.info(f"Successfully sent FCM notification: {response}")
            
        except messaging.UnregisteredError:
            # Token is invalid or unregistered
            invalid_tokens.append(token)
            failed_count += 1
            logger.warning(f"Invalid FCM token (unregistered): {token}")
            
        except messaging.SenderIdMismatchError:
            # Token belongs to different project
            invalid_tokens.append(token)
            failed_count += 1
            logger.warning(f"Invalid FCM token (sender ID mismatch): {token}")
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send FCM notification to {token}: {str(e)}")
    
    result = {
        'success': success_count > 0,
        'success_count': success_count,
        'failed_count': failed_count,
        'invalid_tokens': invalid_tokens,
        'total': len(tokens)
    }
    
    logger.info(f"FCM notification batch result: {result}")
    return result


def send_post_notification(post, author):
    """
    Send notification for new post
    
    Args:
        post: Post model instance
        author: CustomUser model instance (post author)
    
    Returns:
        dict: Result from send_fcm_notification
    """
    from users.models import CustomUser, MutedInstructor
    
    # Get all users with FCM tokens except:
    # 1. The post author
    # 2. Users who muted this instructor
    users_with_tokens = CustomUser.objects.filter(
        fcm_token__isnull=False
    ).exclude(
        fcm_token=''
    ).exclude(
        id=author.id
    ).exclude(
        muted_instructors__instructor=author
    ).values_list('fcm_token', flat=True)
    
    tokens = list(users_with_tokens)
    
    if not tokens:
        logger.info("No FCM tokens found for post notification")
        return {'success': False, 'message': 'No recipients'}
    
    # Prepare notification
    title = "New Post! 📝"
    body = f"{author.first_name} {author.last_name} just shared something new"
    data = {
        'postId': str(post.id),
        'type': 'post',
        'authorId': str(author.id),
        'authorName': f"{author.first_name} {author.last_name}",
        'click_action': 'OPEN_POST'
    }
    
    result = send_fcm_notification(tokens, title, body, data)
    
    # Clean up invalid tokens
    if result.get('invalid_tokens'):
        _remove_invalid_tokens(result['invalid_tokens'])
    
    return result


def send_poll_notification(poll, author):
    """
    Send notification for new poll
    
    Args:
        poll: Poll model instance
        author: CustomUser model instance (poll author)
    
    Returns:
        dict: Result from send_fcm_notification
    """
    from users.models import CustomUser, MutedInstructor
    
    # Get all users with FCM tokens except:
    # 1. The poll author
    # 2. Users who muted this instructor
    users_with_tokens = CustomUser.objects.filter(
        fcm_token__isnull=False
    ).exclude(
        fcm_token=''
    ).exclude(
        id=author.id
    ).exclude(
        muted_instructors__instructor=author
    ).values_list('fcm_token', flat=True)
    
    tokens = list(users_with_tokens)
    
    if not tokens:
        logger.info("No FCM tokens found for poll notification")
        return {'success': False, 'message': 'No recipients'}
    
    # Prepare notification
    title = "New Poll Available! 📊"
    body = f"{author.first_name} {author.last_name} just shared something new"
    data = {
        'postId': str(poll.id),
        'type': 'poll',
        'authorId': str(author.id),
        'authorName': f"{author.first_name} {author.last_name}",
        'click_action': 'OPEN_POST'
    }
    
    result = send_fcm_notification(tokens, title, body, data)
    
    # Clean up invalid tokens
    if result.get('invalid_tokens'):
        _remove_invalid_tokens(result['invalid_tokens'])
    
    return result


def _remove_invalid_tokens(invalid_tokens):
    """Remove invalid FCM tokens from database"""
    from users.models import CustomUser
    
    if not invalid_tokens:
        return
    
    count = CustomUser.objects.filter(fcm_token__in=invalid_tokens).update(fcm_token=None)
    logger.info(f"Removed {count} invalid FCM tokens from database")


def test_fcm_notification(token, title="Test Notification", body="This is a test notification"):
    """
    Send a test notification to a specific device
    
    Args:
        token (str): FCM device token
        title (str): Notification title
        body (str): Notification body
    
    Returns:
        dict: Result from send_fcm_notification
    """
    data = {
        'test': 'true',
        'timestamp': str(timezone.now())
    }
    
    return send_fcm_notification([token], title, body, data)
