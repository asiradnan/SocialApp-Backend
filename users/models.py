from django.contrib.auth.models import AbstractUser
from django.db import models
import os
from django.utils import timezone

def user_profile_picture_path(instance, filename):
    """Generate file path for user profile pictures"""
    # Get file extension
    ext = filename.split('.')[-1]
    # Create filename with user id and timestamp
    filename = f'profile_pictures/user_{instance.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.{ext}'
    return filename

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('instructor', 'Instructor'),
        ('standard', 'Standard'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')], null=True, blank=True)
    profile_picture = models.ImageField(upload_to=user_profile_picture_path, null=True, blank=True)

    username = None  # remove the default username field
    email = models.EmailField(unique=True)  
    first_name = models.CharField(max_length=150)  
    last_name = models.CharField(max_length=150)   

    USERNAME_FIELD = 'email'  # set email as the username
    REQUIRED_FIELDS = ['first_name', 'last_name','date_of_birth', 'user_type']  
    
    def __str__(self):
        return self.email
    
    def get_profile_picture_url(self):
        """Get the full URL for the profile picture"""
        if self.profile_picture:
            return self.profile_picture.url
        return None
    
    def delete_old_profile_picture(self):
        """Delete the old profile picture file when updating"""
        if self.profile_picture:
            if os.path.isfile(self.profile_picture.path):
                os.remove(self.profile_picture.path)
    
    def delete(self, *args, **kwargs):
        """Custom delete method to handle all user data properly"""
        from django.db import transaction
        
        with transaction.atomic():
            # Delete profile picture files
            if self.profile_picture:
                self.delete_old_profile_picture()
            
            # Delete all profile picture files from ProfilePicture model
            for pic in self.profile_pictures.all():
                if pic.image and os.path.isfile(pic.image.path):
                    os.remove(pic.image.path)
            
            # Hard delete soft-deleted comments to avoid constraint issues
            from feed.models import Comment, Post
            
            # Get all user's comments (including soft-deleted ones)
            user_comments = Comment.objects.filter(author=self)
            user_comments.delete()  # Hard delete
            
            # Get all user's posts (including soft-deleted ones)  
            user_posts = Post.objects.filter(author=self)
            
            # Delete media files from posts
            for post in user_posts:
                if post.image and os.path.isfile(post.image.path):
                    os.remove(post.image.path)
            
            user_posts.delete()  # Hard delete
            
            # Now delete the user (CASCADE will handle the rest)
            super().delete(*args, **kwargs)


class ProfilePicture(models.Model):
    """Model to track profile picture history and metadata"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='profile_pictures')
    image = models.ImageField(upload_to=user_profile_picture_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=False)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # in bytes
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.user.email} - Profile Picture ({self.uploaded_at})"
    
    def save(self, *args, **kwargs):
        # Calculate file size if not set
        if self.image and not self.file_size:
            self.file_size = self.image.size
        
        # Set this as current profile picture
        if self.is_current:
            # Set all other profile pictures for this user as not current
            ProfilePicture.objects.filter(user=self.user, is_current=True).update(is_current=False)
            # Update the user's profile_picture field
            self.user.profile_picture = self.image
            self.user.save(update_fields=['profile_picture'])
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete the image file when deleting the model instance
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)
