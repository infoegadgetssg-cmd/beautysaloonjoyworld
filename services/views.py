# services/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from .models import ServiceCategory, Service, ServiceReview, ServiceFAQ, Stylist
from .forms import ServiceReviewForm, ServiceSearchForm

def services_list(request, category_slug=None):
    """Main services page with filtering"""
    categories = ServiceCategory.objects.filter(is_active=True)
    
    # Get active services with prefetch related data
    services = Service.objects.filter(is_active=True).select_related('category').prefetch_related('reviews')
    
    # Initialize search form with GET data
    form = ServiceSearchForm(request.GET) 

    # Handle category filter
    current_category = None
    if category_slug and category_slug != 'all':
        try:
            current_category = ServiceCategory.objects.get(slug=category_slug, is_active=True)
            services = services.filter(category=current_category)
        except ServiceCategory.DoesNotExist:
            pass
    
    search_query = request.GET.get('search', '')
    if search_query:
        services = services.filter(
            Q(name__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(full_description__icontains=search_query)
        )
    
    # Price filter
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        try:
            services = services.filter(price__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            services = services.filter(price__lte=float(price_max))
        except ValueError:
            pass
    
    # Duration filter
    duration_min = request.GET.get('duration_min')
    duration_max = request.GET.get('duration_max')
    if duration_min:
        try:
            services = services.filter(duration__gte=int(duration_min))
        except ValueError:
            pass
    if duration_max:
        try:
            services = services.filter(duration__lte=int(duration_max))
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(services, 9)  # Show 9 services per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get general FAQs (not service-specific)
    general_faqs = ServiceFAQ.objects.filter(service__isnull=True, category__isnull=True, is_active=True)
    
    context = {
        'categories': categories,
        'services': page_obj,
        'current_category': current_category.slug if current_category else 'all',
        'form': form,
        'faqs': general_faqs,
        'total_services': services.count(),
    }
    
    return render(request, 'services/services.html', context)

def service_detail(request, slug):
    """Service detail page with reviews"""
    service = get_object_or_404(Service.objects.select_related('category'), slug=slug, is_active=True)
    
    # Get reviews for this service
    reviews = ServiceReview.objects.filter(service=service, is_approved=True).select_related('user')
    
    # Get average rating
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Get related services (same category)
    related_services = Service.objects.filter(
        category=service.category,
        is_active=True
    ).exclude(id=service.id)[:3]
    
    # Get service-specific FAQs
    service_faqs = ServiceFAQ.objects.filter(
        Q(service=service) | Q(category=service.category),
        is_active=True
    ).distinct()
    
    # Review form handling
    review_form = None
    user_review = None
    
    if request.user.is_authenticated:
        user_review = ServiceReview.objects.filter(service=service, user=request.user).first()
        
        if not user_review and request.method == 'POST' and 'submit_review' in request.POST:
            review_form = ServiceReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.service = service
                review.user = request.user
                review.save()
                messages.success(request, 'Thank you for your review!')
                return redirect('service_detail', slug=slug)
        else:
            review_form = ServiceReviewForm()
    
    context = {
        'service': service,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1) if avg_rating else 0,
        'review_count': reviews.count(),
        'related_services': related_services,
        'faqs': service_faqs,
        'review_form': review_form,
        'user_review': user_review,
        'is_user_reviewed': user_review is not None,
    }
    
    return render(request, 'services/service_detail.html', context)

@login_required
def add_review(request, slug):
    """Add or update review for a service"""
    service = get_object_or_404(Service, slug=slug)
    
    # Check if user already reviewed
    existing_review = ServiceReview.objects.filter(service=service, user=request.user).first()
    
    if request.method == 'POST':
        if existing_review:
            form = ServiceReviewForm(request.POST, instance=existing_review)
        else:
            form = ServiceReviewForm(request.POST)
        
        if form.is_valid():
            review = form.save(commit=False)
            if not existing_review:
                review.service = service
                review.user = request.user
            review.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Review submitted successfully!',
                    'rating': review.rating,
                    'comment': review.comment,
                    'user_name': request.user.get_full_name() or request.user.username,
                    'created_at': review.created_at.strftime('%b %d, %Y')
                })
            else:
                messages.success(request, 'Review submitted successfully!')
                return redirect('service_detail', slug=slug)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    return redirect('service_detail', slug=slug)

def stylists_list(request):
    """List of all stylists"""
    stylists = Stylist.objects.filter(is_active=True).prefetch_related('specialties')
    
    context = {
        'stylists': stylists,
    }
    
    return render(request, 'services/stylists.html', context)

def stylist_detail(request, slug):
    """Stylist detail page"""
    stylist = get_object_or_404(Stylist, slug=slug, is_active=True)
    
    # Get services this stylist specializes in
    specialties = stylist.specialties.filter(is_active=True)
    
    context = {
        'stylist': stylist,
        'specialties': specialties,
    }
    
    return render(request, 'services/stylist_detail.html', context)

def get_services_by_category(request):
    """AJAX endpoint to get services by category"""
    category_slug = request.GET.get('category', 'all')
    
    if category_slug == 'all':
        services = Service.objects.filter(is_active=True)
    else:
        services = Service.objects.filter(category__slug=category_slug, is_active=True)
    
    # Format services data
    services_data = []
    for service in services:
        services_data.append({
            'id': service.id,
            'name': service.name,
            'category': service.category.name,
            'price': float(service.current_price),
            'formatted_price': f"£{service.current_price}",
            'duration': service.formatted_duration,
            'short_description': service.short_description,
            'image_url': service.image.url if service.image else service.image_url,
            'slug': service.slug,
            'is_on_special': service.is_on_special,
            'special_price': float(service.special_price) if service.special_price else None,
        })
    
    return JsonResponse({
        'success': True,
        'services': services_data,
        'count': len(services_data)
    })