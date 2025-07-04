from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from feed.models import PostReaction, Comment, PollVote, UserScore

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
    instance.post.comments_count = instance.post.comments.filter(is_active=True).count()
    instance.post.save(update_fields=['comments_count'])
    
    # Update parent comment reply count
    if instance.parent:
        instance.parent.replies_count = instance.parent.replies.filter(is_active=True).count()
        instance.parent.save(update_fields=['replies_count'])
    
    # Remove points for comment
    with transaction.atomic():
        user_score = UserScore.get_or_create_for_user(instance.author)
        user_score.remove_comment_points()

@receiver(post_save, sender=PostReaction)
def update_reaction_count_on_create(sender, instance, created, **kwargs):
    """Update post reaction count when reaction is created"""
    if created:
        instance.post.reactions_count = instance.post.reactions.count()
        instance.post.save(update_fields=['reactions_count'])
        
        # Add points for reaction
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
