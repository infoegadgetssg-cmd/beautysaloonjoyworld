# gallery/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator

from .models import GalleryCategory, GalleryImage, BeforeAfterImage, ImageLike
from contact.models import Testimonial

class GalleryView(TemplateView):
    """Main gallery page view"""
    template_name = 'gallery/gallery.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all active categories
        categories = GalleryCategory.objects.filter(is_active=True).order_by('order', 'name')
        
        # Get all published images (initial load - JavaScript will handle filtering)
        gallery_images = GalleryImage.objects.filter(
            is_published=True
        ).select_related('category').order_by('display_order', '-created_at')
        
        # Get before/after images
        before_after_images = BeforeAfterImage.objects.filter(
            is_active=True
        ).order_by('display_order')[:3]  # Limit to 3
        
        # Get testimonials
        testimonials = Testimonial.objects.filter(
            is_active=True
        ).order_by('-created_at')[:3]
        
        # Get image count by category for filter
        category_counts = {}
        for category in categories:
            count = gallery_images.filter(category=category).count()
            if count > 0:
                category_counts[category.slug] = count
        
        context.update({
            'categories': categories,
            'gallery_images': gallery_images,
            'before_after_images': before_after_images,
            'testimonials': testimonials,
            'category_counts': category_counts,
            'total_images': gallery_images.count(),
        })
        
        return context

class GalleryCategoryView(ListView):
    """View for a specific gallery category"""
    template_name = 'gallery/category.html'
    context_object_name = 'images'
    paginate_by = 12
    
    def get_queryset(self):
        self.category = get_object_or_404(GalleryCategory, slug=self.kwargs['slug'], is_active=True)
        return GalleryImage.objects.filter(
            category=self.category,
            is_published=True
        ).select_related('category').order_by('display_order', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = GalleryCategory.objects.filter(is_active=True).order_by('order')
        return context

class ImageDetailView(DetailView):
    """View for individual image details"""
    template_name = 'gallery/image_detail.html'
    model = GalleryImage
    context_object_name = 'image'
    
    def get_object(self, queryset=None):
        image = get_object_or_404(GalleryImage, slug=self.kwargs['slug'], is_published=True)
        # Increment view count
        image.increment_views()
        return image
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        image = self.object
        
        # Check if user has liked this image
        user_liked = False
        if self.request.user.is_authenticated:
            user_liked = ImageLike.objects.filter(
                user=self.request.user,
                image=image
            ).exists()
        
        # Get related images (same category)
        related_images = GalleryImage.objects.filter(
            category=image.category,
            is_published=True
        ).exclude(id=image.id).order_by('display_order')[:6]
        
        # Get next and previous images for navigation
        next_image = image.get_next_image()
        prev_image = image.get_previous_image()
        
        context.update({
            'user_liked': user_liked,
            'related_images': related_images,
            'next_image': next_image,
            'prev_image': prev_image,
            'categories': GalleryCategory.objects.filter(is_active=True).order_by('order'),
        })
        
        return context

@require_GET
def gallery_filter_view(request):
    """AJAX view for filtering gallery images"""
    category_slug = request.GET.get('category', 'all')
    page = request.GET.get('page', 1)
    
    # Build queryset
    if category_slug == 'all':
        images = GalleryImage.objects.filter(is_published=True)
    else:
        category = get_object_or_404(GalleryCategory, slug=category_slug, is_active=True)
        images = GalleryImage.objects.filter(category=category, is_published=True)
    
    # Order and paginate
    images = images.select_related('category').order_by('display_order', '-created_at')
    
    paginator = Paginator(images, 12)  # 12 images per page
    from django.core.paginator import PageNotAnInteger, EmptyPage
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    
    # Convert to JSON
    image_data = []
    for img in page_obj:
        image_data.append({
            'id': img.id,
            'title': img.title,
            'description': img.description,
            'image_url': img.image.url,
            'thumbnail_url': img.thumbnail.url if img.thumbnail else img.image.url,
            'category': img.category.name,
            'category_slug': img.category.slug,
            'category_color': img.category.color,
            'image_type': img.image_type,
            'likes': img.likes,
            'views': img.views,
            'created_at': img.created_at.strftime('%B %d, %Y'),
        })
    
    response_data = {
        'images': image_data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_images': paginator.count,
    }
    
    return JsonResponse(response_data)

@login_required
@require_POST
def toggle_image_like(request, image_id):
    """Toggle like on an image"""
    try:
        image = GalleryImage.objects.get(id=image_id, is_published=True)
        
        # Check if user already liked this image
        like, created = ImageLike.objects.get_or_create(
            user=request.user,
            image=image
        )
        
        if not created:
            # Unlike
            like.delete()
            image.likes = max(0, image.likes - 1)
            liked = False
        else:
            # Like
            image.likes += 1
            liked = True
        
        image.save(update_fields=['likes'])
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'total_likes': image.likes,
            'message': 'Image liked!' if liked else 'Image unliked!'
        })
        
    except GalleryImage.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Image not found.'
        })

@require_GET
def before_after_data(request):
    """Get before/after images data for slider"""
    images = BeforeAfterImage.objects.filter(
        is_active=True
    ).order_by('display_order')
    
    image_data = []
    for img in images:
        image_data.append({
            'id': img.id,
            'title': img.title,
            'description': img.description,
            'before_image': img.before_image.url,
            'after_image': img.after_image.url,
            'before_caption': img.before_caption,
            'after_caption': img.after_caption,
            'service': img.service,
            'duration': img.duration,
            'result': img.result,
        })
    
    return JsonResponse({
        'images': image_data,
        'count': len(image_data)
    })

class GalleryImageView(TemplateView):
    """Handle gallery image requests"""
    
    def get(self, request, *args, **kwargs):
        # Return gallery page
        return GalleryView.as_view()(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            action = request.POST.get('action')
            
            if action == 'filter':
                category_slug = request.POST.get('category', 'all')
                # Return filtered images
                images = GalleryImage.objects.filter(is_published=True)
                
                if category_slug != 'all':
                    images = images.filter(category__slug=category_slug)
                
                images = images.select_related('category').order_by('display_order', '-created_at')[:50]
                
                image_data = []
                for img in images:
                    image_data.append({
                        'id': img.id,
                        'title': img.title,
                        'description': img.description,
                        'image_url': img.image.url,
                        'category': img.category.name,
                        'category_slug': img.category.slug,
                        'image_type': img.image_type,
                    })
                
                return JsonResponse({'images': image_data})
        
        return JsonResponse({'error': 'Invalid request'}, status=400)