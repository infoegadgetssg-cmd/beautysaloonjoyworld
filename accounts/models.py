from django.db import models

# Create your models here.
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Add fields that match your Firebase user profile
    phone = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True)
    # Remove 'email' from here; it's already in AbstractUser

    def __str__(self):
        return self.email
