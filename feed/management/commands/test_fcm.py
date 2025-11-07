"""
Management command to test FCM notification logging
"""
from django.core.management.base import BaseCommand
from users.models import CustomUser
from utils.fcm_helper import test_fcm_notification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test FCM notification with logging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--token',
            type=str,
            help='FCM token to test (if not provided, will use first available user token)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to get FCM token from',
        )

    def handle(self, *args, **options):
        token = options.get('token')
        user_id = options.get('user_id')

        # Get token from user if specified
        if user_id and not token:
            try:
                user = CustomUser.objects.get(id=user_id)
                token = user.fcm_token
                if not token:
                    self.stdout.write(self.style.ERROR(f'User {user_id} has no FCM token'))
                    return
                self.stdout.write(self.style.SUCCESS(f'Using token from user: {user.email}'))
            except CustomUser.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {user_id} not found'))
                return

        # Get first available token if none specified
        if not token:
            user = CustomUser.objects.filter(fcm_token__isnull=False).exclude(fcm_token='').first()
            if not user:
                self.stdout.write(self.style.ERROR('No users with FCM tokens found'))
                return
            token = user.fcm_token
            self.stdout.write(self.style.SUCCESS(f'Using token from user: {user.email}'))

        self.stdout.write(self.style.WARNING(f'Sending test notification to token: {token[:20]}...'))
        
        # Send test notification
        try:
            result = test_fcm_notification(
                token=token,
                title="Test Notification 🧪",
                body="This is a test notification from Django backend"
            )
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Notification sent successfully!\n'
                    f'   Success: {result["success_count"]}\n'
                    f'   Failed: {result["failed_count"]}'
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f'❌ Notification failed!\n'
                    f'   Message: {result.get("message", "Unknown error")}'
                ))
                
            self.stdout.write(self.style.WARNING(
                '\nCheck logs for details:\n'
                '  - fcm_notifications.log (FCM-specific logs)\n'
                '  - django.log (all logs)'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            logger.error(f'Test FCM notification failed: {str(e)}', exc_info=True)
