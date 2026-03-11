# services/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.utils.text import slugify
from .models import ServiceCategory, Service, ServiceReview, ServiceFAQ, Stylist
from .forms import ServiceReviewForm, ServiceSearchForm

DEFAULT_SERVICE_CATEGORIES = ["Hair", "Nails", "Facial", "Massage", "Spa"]
DEFAULT_FAQS = [
    ("How far in advance should I book my appointment?", "We recommend booking at least 48 hours in advance to secure your preferred time."),
    ("What is your cancellation policy?", "Please cancel or reschedule at least 24 hours before your appointment to avoid cancellation fees."),
    ("Do you use cruelty-free products?", "Yes. We prioritize cruelty-free and skin-friendly products across our services."),
    ("Can I bring my own products?", "Yes, you can bring your preferred products and our team will use them where suitable."),
    ("Do you offer packages or memberships?", "Yes, we offer selected treatment packages and periodic membership-style offers. Please contact us for current options."),
]


def _staff_dashboard_guard(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please login to access admin dashboard.")
        return redirect("account_login")
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("index")
    return None


def _ensure_default_service_categories():
    if not ServiceCategory.objects.exists():
        for name in DEFAULT_SERVICE_CATEGORIES:
            ServiceCategory.objects.get_or_create(
                slug=slugify(name),
                defaults={'name': name, 'is_active': True}
            )


def _ensure_default_faqs():
    general_faqs = ServiceFAQ.objects.filter(service__isnull=True, category__isnull=True)
    if general_faqs.exists():
        return

    for index, (question, answer) in enumerate(DEFAULT_FAQS, start=1):
        ServiceFAQ.objects.create(
            question=question,
            answer=answer,
            display_order=index,
            is_active=True
        )


def services_list(request, category_slug=None):
    """Main services page with filtering"""
    _ensure_default_service_categories()
    _ensure_default_faqs()
    categories = ServiceCategory.objects.filter(is_active=True)

    import logging
    logger = logging.getLogger(__name__)
    total_services = Service.objects.count()
    active_services = Service.objects.filter(is_active=True).count()
    logger.warning("services_list debug -> total_services=%s, active_services=%s", total_services, active_services)

    # If page is empty, check active_services count in logs.
    services = Service.objects.filter(is_active=True).select_related('category').prefetch_related('reviews')
    if not services.exists():
        # Backward-compatible fallback for legacy records created before active flag handling was fixed.
        services = Service.objects.all().select_related('category').prefetch_related('reviews')
    
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
    service = get_object_or_404(Service.objects.select_related('category'), slug=slug)
    
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


def stylist_management(request):
    guard_response = _staff_dashboard_guard(request)
    if guard_response:
        return guard_response

    if request.method == "POST":
        try:
            name = (request.POST.get("name") or "").strip()
            bio = (request.POST.get("bio") or "").strip()
            title = (request.POST.get("title") or "").strip()
            work_days = (request.POST.get("work_days") or "").strip()
            shift_start = request.POST.get("shift_start") or None
            shift_end = request.POST.get("shift_end") or None
            is_active = request.POST.get("is_active") == "on"
            is_available = request.POST.get("is_available") == "on"

            if not name or not bio:
                return JsonResponse(
                    {"success": False, "message": "Name and bio are required."},
                    status=400
                )

            base_slug = slugify(name) or "stylist"
            slug = base_slug
            counter = 1
            while Stylist.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            stylist = Stylist.objects.create(
                name=name,
                slug=slug,
                bio=bio,
                title=title,
                work_days=work_days,
                shift_start=shift_start,
                shift_end=shift_end,
                is_active=is_active,
                is_available=is_available,
            )

            specialty_ids = request.POST.getlist("specialties")
            if specialty_ids:
                stylist.specialties.set(Service.objects.filter(id__in=specialty_ids))

            return JsonResponse({"success": True, "message": "Stylist added successfully."})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    stylists = Stylist.objects.prefetch_related("specialties").all().order_by("name")
    services = Service.objects.filter(is_active=True).order_by("name")
    return render(
        request,
        "admin_dashboard/stylists.html",
        {"stylists": stylists, "services": services}
    )


def update_stylist(request, stylist_id):
    guard_response = _staff_dashboard_guard(request)
    if guard_response:
        return guard_response

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    stylist = get_object_or_404(Stylist, id=stylist_id)
    try:
        stylist.name = (request.POST.get("name") or stylist.name).strip()
        stylist.bio = (request.POST.get("bio") or stylist.bio).strip()
        stylist.title = (request.POST.get("title") or stylist.title).strip()
        stylist.work_days = (request.POST.get("work_days") or "").strip()
        stylist.shift_start = request.POST.get("shift_start") or None
        stylist.shift_end = request.POST.get("shift_end") or None
        stylist.is_active = request.POST.get("is_active") == "on"
        stylist.is_available = request.POST.get("is_available") == "on"
        stylist.save()

        specialty_ids = request.POST.getlist("specialties")
        stylist.specialties.set(Service.objects.filter(id__in=specialty_ids))

        return JsonResponse({"success": True, "message": "Stylist updated successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


def delete_stylist(request, stylist_id):
    guard_response = _staff_dashboard_guard(request)
    if guard_response:
        return guard_response

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

    stylist = get_object_or_404(Stylist, id=stylist_id)
    stylist.delete()
    return JsonResponse({"success": True, "message": "Stylist deleted successfully."})

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
    """AJAX endpoint for service search and category filtering."""
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', 'all').strip()
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    services = Service.objects.filter(is_active=True).select_related('category')
    if not services.exists():
        # Backward-compatible fallback for legacy records created before active flag handling was fixed.
        services = Service.objects.all().select_related('category')

    if query:
        services = services.filter(
            Q(name__icontains=query) |
            Q(short_description__icontains=query) |
            Q(full_description__icontains=query)
        )

    if category_slug and category_slug != 'all':
        services = services.filter(category__slug=category_slug)

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

    services_data = []
    for service in services:
        services_data.append({
            'id': service.id,
            'name': service.name,
            'category': service.category.name,
            'price': float(service.current_price),
            'regular_price': float(service.price),
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
