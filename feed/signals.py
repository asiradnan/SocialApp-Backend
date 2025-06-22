from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from feed.models import PostReaction, Comment

@receiver(post_save, sender=Comment)
def update_comment_count_on_create(sender, instance, created, **kwargs):
    if created:
        instance.post.comments_count = instance.post.comments.filter(is_active=True).count()
        instance.post.save(update_fields=['comments_count'])
        
        if instance.parent:
            instance.parent.replies_count = instance.parent.replies.filter(is_active=True).count()
            instance.parent.save(update_fields=['replies_count'])

@receiver(post_delete, sender=Comment)
def update_comment_count_on_delete(sender, instance, **kwargs):
    """Update post comment count when comment is deleted"""
    instance.post.comments_count = instance.post.comments.filter(is_active=True).count()
    instance.post.save(update_fields=['comments_count'])
    
    # Update parent comment reply count
    if instance.parent:
        instance.parent.replies_count = instance.parent.replies.filter(is_active=True).count()
        instance.parent.save(update_fields=['replies_count'])

@receiver(post_save, sender=PostReaction)
def update_reaction_count_on_create(sender, instance, created, **kwargs):
    """Update post reaction count when reaction is created"""
    if created:
        instance.post.reactions_count = instance.post.reactions.count()
        instance.post.save(update_fields=['reactions_count'])

@receiver(post_delete, sender=PostReaction)  
def update_reaction_count_on_delete(sender, instance, **kwargs):
    """Update post reaction count when reaction is deleted"""
    instance.post.reactions_count = instance.post.reactions.count()
    instance.post.save(update_fields=['reactions_count'])