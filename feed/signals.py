from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from feed.models import PostReaction, Comment, PollVote, UserScore, Post, Poll
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Comment)
def update_comment_count_on_create(sender, instance, created, **kwargs):
    if created:
        instance.post.comments_count = instance.post.comments.filter(is_active=True).count()
        instance.post.save(update_fields=['comments_count'])
        
        if instance.parent:
            instance.parent.replies_count = instance.parent.replies.filter(is_active=True).count()
            instance.parent.save(update_fields=['replies_count'])
        
        # Add points for comment
        with transaction.atomic():
            user_score = UserScore.get_or_create_for_user(instance.author)
            user_score.add_comment_points()

@receiver(post_delete, sender=Comment)
def update_comment_count_on_delete(sender, instance, **kwargs):
    """Update post comment count when comment is deleted"""
    try:
        # Update post comment count (only if post still exists)
        if hasattr(instance, 'post') and instance.post:
            instance.post.comments_count = instance.post.comments.filter(is_active=True).count()
            instance.post.save(update_fields=['comments_count'])
        
        # Update parent comment reply count (only if parent still exists)
        if hasattr(instance, 'parent') and instance.parent:
            # Check if parent still exists in database (might be deleted in cascade)
            try:
                parent_comment = Comment.objects.get(id=instance.parent.id)
                parent_comment.replies_count = parent_comment.replies.filter(is_active=True).count()
                parent_comment.save(update_fields=['replies_count'])
            except Comment.DoesNotExist:
                # Parent was deleted in cascade, no need to update count
                pass
        
        # Remove points for comment
        with transaction.atomic():
            user_score = UserScore.get_or_create_for_user(instance.author)
            user_score.remove_comment_points()
    except Exception as e:
        # Log the error but don't raise it to avoid breaking the deletion
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating comment counts on delete: {str(e)}")

@receiver(post_save, sender=PostReaction)
def update_reaction_count_on_save(sender, instance, created, **kwargs):
    """Update post reaction count when reaction is created or updated"""
    # Always recalculate the count to be safe
    instance.post.reactions_count = instance.post.reactions.count()
    instance.post.save(update_fields=['reactions_count'])
    
    # Only add points for newly created reactions
    if created:
        with transaction.atomic():
            user_score = UserScore.get_or_create_for_user(instance.user)
            user_score.add_reaction_points()

@receiver(post_delete, sender=PostReaction)  
def update_reaction_count_on_delete(sender, instance, **kwargs):
    """Update post reaction count when reaction is deleted"""
    instance.post.reactions_count = instance.post.reactions.count()
    instance.post.save(update_fields=['reactions_count'])
    
    # Remove points for reaction
    with transaction.atomic():
        user_score = UserScore.get_or_create_for_user(instance.user)
        user_score.remove_reaction_points()


# NEW SIGNALS FOR POLL VOTES
@receiver(post_save, sender=PollVote)
def handle_poll_vote_created(sender, instance, created, **kwargs):
    """Add points when a user votes on a poll"""
    if created:
        with transaction.atomic():
            user_score = UserScore.get_or_create_for_user(instance.user)
            user_score.add_poll_vote_points()

@receiver(post_delete, sender=PollVote)
def handle_poll_vote_deleted(sender, instance, **kwargs):
    """Remove points when a poll vote is deleted"""
    with transaction.atomic():
        user_score = UserScore.get_or_create_for_user(instance.user)
        user_score.remove_poll_vote_points()


# FCM NOTIFICATION SIGNALS
@receiver(post_save, sender=Post)
def send_post_notification(sender, instance, created, **kwargs):
    """Send FCM notification when a new post is created"""
    if created:
        try:
            from utils.fcm_helper import send_post_notification as send_fcm_post
            # Send notification in background (don't block post creation)
            transaction.on_commit(lambda: send_fcm_post(instance, instance.author))
        except Exception as e:
            logger.error(f"Failed to send FCM notification for post {instance.id}: {str(e)}")


@receiver(post_save, sender=Poll)
def send_poll_notification(sender, instance, created, **kwargs):
    """Send FCM notification when a new poll is created"""
    if created:
        try:
            from utils.fcm_helper import send_poll_notification as send_fcm_poll
            # Send notification in background (don't block poll creation)
            transaction.on_commit(lambda: send_fcm_poll(instance, instance.author))
        except Exception as e:
            logger.error(f"Failed to send FCM notification for poll {instance.id}: {str(e)}")
