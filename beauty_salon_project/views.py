# beauty_salon_project/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Home page is already handled by TemplateView in urls.py

def index_view(request):
    return render(request, 'index.html')

def services_view(request):
    return render(request, 'services.html')

def booking_view(request):
    return render(request, 'booking.html')

def shop_view(request):
    return render(request, 'shop.html')

def gallery_view(request):
    return render(request, 'gallery.html')

def contact_view(request):
    return render(request, 'contact.html')

# Add user dashboard view
@login_required
def user_dashboard_view(request):
    return render(request, 'dashboard.html')
