from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
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
    fcm_token = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="Firebase Cloud Messaging token for push notifications")

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


class MutedInstructor(models.Model):
    """Model to track users who have muted notifications from specific instructors"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='muted_instructors')
    instructor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='muted_by_users')
    muted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'instructor')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['instructor']),
        ]
    
    def __str__(self):
        return f"{self.user.email} muted {self.instructor.email}"


class Rating(models.Model):
    """Model to track user ratings for instructors"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ratings_given')
    instructor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ratings_received')
    rating = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        help_text="Rating value from 1 to 5"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'instructor')
        indexes = [
            models.Index(fields=['instructor']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} rated {self.instructor.email}: {self.rating}/5"

