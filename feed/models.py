from django.db import models
from django.conf import settings
from django.core.validators import MinLengthValidator
from django.utils import timezone


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='posts'
    )
    content = models.TextField(
        max_length=2000,
        validators=[MinLengthValidator(1)]
    )
    image = models.ImageField(
        upload_to='posts/images/', 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Denormalized fields for performance
    reactions_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.author.email} - {self.content[:50]}"


class Comment(models.Model):
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    content = models.TextField(
        max_length=1000,
        validators=[MinLengthValidator(1)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Denormalized field for nested comments
    replies_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.author.email} on {self.post.id} - {self.content[:30]}"
    
    def save(self, *args, **kwargs):
        if self.parent and self.parent.parent:
            raise ValueError("Comments can only be nested 2 levels deep")
        super().save(*args, **kwargs)


class PostReaction(models.Model):    
    REACTION_CHOICES = [
        ('love', '❤️'),
        ('haha', '😂'),
        ('sad', '😢'),
        ('angry', '😠'),
    ]
    
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='reactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='post_reactions'
    )
    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('post', 'user')  # One reaction per user per post
        indexes = [
            models.Index(fields=['post', 'reaction_type']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} {self.get_reaction_type_display()} on post {self.post.id}"
    
    @property
    def emoji(self):
        """Get emoji for the reaction type"""
        return dict(self.REACTION_CHOICES).get(self.reaction_type, '')
