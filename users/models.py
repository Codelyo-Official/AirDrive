from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('regular', 'Regular User'),
        ('owner', 'Car Owner'),
        ('admin', 'Admin'),
        ('support', 'Support'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='regular')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    points = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return self.username

class Offer(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    points_required = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
