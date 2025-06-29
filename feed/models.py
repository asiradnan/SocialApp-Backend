from django.db import models
from django.conf import settings
from django.core.validators import MinLengthValidator, FileExtensionValidator
from django.utils import timezone
from datetime import datetime, timedelta
import os


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
    # Rename to 'media' but keep the field name as 'image' for backward compatibility
    image = models.FileField(
        upload_to='posts/media/', 
        blank=True, 
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'webm']
            )
        ]
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
    
    @property
    def media_type(self):
        """Determine if the uploaded file is an image or video"""
        if not self.image:
            return None
        
        file_extension = os.path.splitext(self.image.name)[1].lower()
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        video_extensions = ['.mp4', '.mov', '.avi', '.webm']
        
        if file_extension in image_extensions:
            return 'image'
        elif file_extension in video_extensions:
            return 'video'
        return 'unknown'
    
    @property
    def is_image(self):
        """Check if the media is an image"""
        return self.media_type == 'image'
    
    @property
    def is_video(self):
        """Check if the media is a video"""
        return self.media_type == 'video'


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


class UserScore(models.Model):
    """Model to track user scores for leaderboard"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='score'
    )
    total_points = models.PositiveIntegerField(default=0)
    weekly_points = models.PositiveIntegerField(default=0)
    monthly_points = models.PositiveIntegerField(default=0)
    
    # Track when weekly/monthly points were last reset
    last_weekly_reset = models.DateTimeField(default=timezone.now)
    last_monthly_reset = models.DateTimeField(default=timezone.now)
    
    # Activity counts
    total_reactions = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    weekly_reactions = models.PositiveIntegerField(default=0)
    weekly_comments = models.PositiveIntegerField(default=0)
    monthly_reactions = models.PositiveIntegerField(default=0)
    monthly_comments = models.PositiveIntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-total_points']
        indexes = [
            models.Index(fields=['-total_points']),
            models.Index(fields=['-weekly_points']),
            models.Index(fields=['-monthly_points']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.total_points} points"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create UserScore for a user"""
        score, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'last_weekly_reset': cls.get_week_start(),
                'last_monthly_reset': cls.get_month_start(),
            }
        )
        return score
    
    @staticmethod
    def get_week_start():
        """Get the start of current week (Monday)"""
        today = timezone.now().date()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        return timezone.make_aware(datetime.combine(week_start, datetime.min.time()))
    
    @staticmethod
    def get_month_start():
        """Get the start of current month"""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        return timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
    
    def reset_weekly_if_needed(self):
        """Reset weekly points if a new week has started"""
        current_week_start = self.get_week_start()
        if self.last_weekly_reset < current_week_start:
            self.weekly_points = 0
            self.weekly_reactions = 0
            self.weekly_comments = 0
            self.last_weekly_reset = current_week_start
            self.save(update_fields=[
                'weekly_points', 'weekly_reactions', 'weekly_comments', 
                'last_weekly_reset'
            ])
    
    def reset_monthly_if_needed(self):
        """Reset monthly points if a new month has started"""
        current_month_start = self.get_month_start()
        if self.last_monthly_reset < current_month_start:
            self.monthly_points = 0
            self.monthly_reactions = 0
            self.monthly_comments = 0
            self.last_monthly_reset = current_month_start
            self.save(update_fields=[
                'monthly_points', 'monthly_reactions', 'monthly_comments',
                'last_monthly_reset'
            ])
    
    def add_reaction_points(self):
        """Add points for a reaction (10 points)"""
        self.reset_weekly_if_needed()
        self.reset_monthly_if_needed()
        
        self.total_points += 10
        self.weekly_points += 10
        self.monthly_points += 10
        self.total_reactions += 1
        self.weekly_reactions += 1
        self.monthly_reactions += 1
        
        self.save()
    
    def remove_reaction_points(self):
        """Remove points for a deleted reaction (10 points)"""
        self.reset_weekly_if_needed()
        self.reset_monthly_if_needed()
        
        self.total_points = max(0, self.total_points - 10)
        self.weekly_points = max(0, self.weekly_points - 10)
        self.monthly_points = max(0, self.monthly_points - 10)
        self.total_reactions = max(0, self.total_reactions - 1)
        self.weekly_reactions = max(0, self.weekly_reactions - 1)
        self.monthly_reactions = max(0, self.monthly_reactions - 1)
        
        self.save()
    
    def add_comment_points(self):
        """Add points for a comment (30 points)"""
        self.reset_weekly_if_needed()
        self.reset_monthly_if_needed()
        
        self.total_points += 30
        self.weekly_points += 30
        self.monthly_points += 30
        self.total_comments += 1
        self.weekly_comments += 1
        self.monthly_comments += 1
        
        self.save()
    
    def remove_comment_points(self):
        """Remove points for a deleted comment (30 points)"""
        self.reset_weekly_if_needed()
        self.reset_monthly_if_needed()
        
        self.total_points = max(0, self.total_points - 30)
        self.weekly_points = max(0, self.weekly_points - 30)
        self.monthly_points = max(0, self.monthly_points - 30)
        self.total_comments = max(0, self.total_comments - 1)
        self.weekly_comments = max(0, self.weekly_comments - 1)
        self.monthly_comments = max(0, self.monthly_comments - 1)
        
        self.save()


class LeaderboardEntry(models.Model):
    """Model to store historical leaderboard data"""
    PERIOD_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leaderboard_entries'
    )
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    points = models.PositiveIntegerField()
    rank = models.PositiveIntegerField()
    reactions_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    # Period identification
    year = models.PositiveIntegerField()
    week_number = models.PositiveIntegerField(null=True, blank=True)  # For weekly
    month_number = models.PositiveIntegerField(null=True, blank=True)  # For monthly
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['rank']
        unique_together = [
            ('user', 'period_type', 'year', 'week_number'),
            ('user', 'period_type', 'year', 'month_number'),
        ]
        indexes = [
            models.Index(fields=['period_type', 'year', 'week_number', 'rank']),
            models.Index(fields=['period_type', 'year', 'month_number', 'rank']),
        ]
    
    def __str__(self):
        period_str = f"{self.year}-W{self.week_number}" if self.week_number else f"{self.year}-{self.month_number:02d}"
        return f"{self.user.email} - Rank {self.rank} ({self.period_type} {period_str})"
