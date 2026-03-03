# gallery/models.py
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from cloudinary.models import CloudinaryField
import cloudinary

User = get_user_model()

class GalleryCategory(models.Model):
    """Categories for gallery images"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    color = models.CharField(max_length=7, default="#a86ba3", help_text="Hex color for category")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Gallery Category"
        verbose_name_plural = "Gallery Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('gallery:category', kwargs={'slug': self.slug})

class GalleryImage(models.Model):
    """Gallery images with categories and display options"""
    IMAGE_TYPES = [
        ('standard', 'Standard'),
        ('featured', 'Featured'),
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = CloudinaryField('image', folder='joyworld/gallery/')
    thumbnail = CloudinaryField('image', folder='joyworld/gallery/thumbnails/', blank=True, null=True)
    
    # Category and display
    category = models.ForeignKey(GalleryCategory, on_delete=models.CASCADE, related_name='images')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default='standard')
    
    # Metadata
    display_order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = "Gallery Image"
        verbose_name_plural = "Gallery Images"
        indexes = [
            models.Index(fields=['is_published', 'image_type']),
            models.Index(fields=['category', 'is_published']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('gallery:image_detail', kwargs={'slug': self.slug})
    
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])
    
    def get_next_image(self):
        next_image = GalleryImage.objects.filter(
            category=self.category,
            display_order__gt=self.display_order,
            is_published=True
        ).order_by('display_order').first()
        
        if not next_image:
            next_image = GalleryImage.objects.filter(
                category=self.category,
                is_published=True
            ).order_by('display_order').first()
        
        return next_image
    
    def get_previous_image(self):
        prev_image = GalleryImage.objects.filter(
            category=self.category,
            display_order__lt=self.display_order,
            is_published=True
        ).order_by('-display_order').first()
        
        if not prev_image:
            prev_image = GalleryImage.objects.filter(
                category=self.category,
                is_published=True
            ).order_by('-display_order').first()
        
        return prev_image

class BeforeAfterImage(models.Model):
    """Before and after comparison images"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    before_image = CloudinaryField('image', folder='joyworld/before_after/')
    after_image = CloudinaryField('image', folder='joyworld/before_after/')
    before_caption = models.CharField(max_length=200, default="Before")
    after_caption = models.CharField(max_length=200, default="After")
    
    # Display
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    service = models.CharField(max_length=100, blank=True, help_text="Related service")
    duration = models.CharField(max_length=50, blank=True, help_text="Treatment duration")
    result = models.CharField(max_length=200, blank=True, help_text="Treatment result")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = "Before/After Image"
        verbose_name_plural = "Before/After Images"
    
    def __str__(self):
        return self.title

class ImageLike(models.Model):
    """Track user likes for images"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ForeignKey(GalleryImage, on_delete=models.CASCADE, related_name='image_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'image']
        verbose_name = "Image Like"
        verbose_name_plural = "Image Likes"
    
    def __str__(self):
        return f"{self.user.username} likes {self.image.title}"