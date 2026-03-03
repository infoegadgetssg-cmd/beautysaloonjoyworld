# gallery/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import GalleryCategory, GalleryImage, BeforeAfterImage, ImageLike

@admin.register(GalleryCategory)
class GalleryCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color_display', 'icon', 'order', 'is_active', 'image_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    
    def color_display(self, obj):
        return format_html(
            '<span style="color: {};">⬤</span> {}',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Color'
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Images'

@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'image_type', 'display_order', 'thumbnail_preview', 'views', 'likes', 'is_published', 'created_at']
    list_filter = ['category', 'image_type', 'is_published', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['image_type', 'is_published', 'display_order']
    readonly_fields = ['views', 'likes', 'thumbnail_preview', 'image_preview']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'slug', 'description', 'category', 'created_by')
        }),
        ('Images', {
            'fields': ('image', 'thumbnail', 'image_preview', 'thumbnail_preview')
        }),
        ('Display', {
            'fields': ('image_type', 'display_order', 'is_published')
        }),
        ('Statistics', {
            'fields': ('views', 'likes'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = 'Image Preview'
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.thumbnail.url
            )
        elif obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.image.url
            )
        return "-"
    thumbnail_preview.short_description = 'Thumbnail Preview'
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(BeforeAfterImage)
class BeforeAfterImageAdmin(admin.ModelAdmin):
    list_display = ['title', 'before_preview', 'after_preview', 'display_order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description', 'service']
    list_editable = ['display_order', 'is_active']
    readonly_fields = ['before_preview', 'after_preview']
    
    def before_preview(self, obj):
        if obj.before_image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.before_image.url
            )
        return "-"
    before_preview.short_description = 'Before'
    
    def after_preview(self, obj):
        if obj.after_image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.after_image.url
            )
        return "-"
    after_preview.short_description = 'After'

admin.site.register(ImageLike)