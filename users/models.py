from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('instructor', 'Instructor'),
        ('standard', 'Standard'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')], null=True, blank=True)

    username = None  # remove the default username field
    email = models.EmailField(unique=True)  # make email required and unique

    USERNAME_FIELD = 'email'  # set email as the username
    REQUIRED_FIELDS = []  # removes username from required fields
    def __str__(self):
        return self.email
