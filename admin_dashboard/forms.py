# dashboard/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from services.models import Stylist
from booking.models import AdditionalService
from shop.models import Product, ProductCategory
from contact.models import ContactMessage, FAQ, SalonLocation, BusinessHours, Testimonial
from .models import AdminDashboard
from services.models import Service, ServiceCategory

class AdminLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'id': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'password'
        })
    )

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'short_description', 'full_description', 'category', 
                 'price', 'duration', 'image', 'is_active', 'is_on_special', 
                 'special_price', 'special_end_date', 'display_order', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'id': 'serviceName',
                'placeholder': 'Enter service name'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'id': 'serviceShortDescription', 
                'rows': 2,
                'placeholder': 'Short description...'
            }),
            'full_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'id': 'serviceDescription', 
                'rows': 4,
                'placeholder': 'Full description...'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select', 
                'id': 'serviceCategory'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'id': 'servicePrice', 
                'min': '0', 
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control', 
                'id': 'serviceDuration', 
                'min': '15', 
                'step': '15',
                'placeholder': 'Duration in minutes'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 
                'id': 'serviceAvailable',
                'checked': 'checked'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'serviceImage'
            }),
            'is_on_special': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 
                'id': 'serviceOnSpecial'
            }),
            'special_price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'id': 'serviceSpecialPrice', 
                'min': '0', 
                'step': '0.01',
                'placeholder': 'Special price...'
            }),
            'special_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'serviceSpecialEndDate'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'serviceDisplayOrder'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 
                'id': 'serviceActive',
                'checked': 'checked'
            }),
        }

class ProductForm(forms.ModelForm):
    # Add image field manually since your model uses main_image
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-control',
        'id': 'productImage'
    }))
    
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'short_description', 'price', 
                 'compare_at_price', 'stock_quantity', 'sku', 'brand', 'is_featured', 
                 'is_bestseller', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'id': 'productName'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'productCategory'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'id': 'productDescription', 'rows': 3}),
            'short_description': forms.TextInput(attrs={'class': 'form-control', 'id': 'productShortDescription'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'id': 'productPrice', 'min': '0', 'step': '0.01'}),
            'compare_at_price': forms.NumberInput(attrs={'class': 'form-control', 'id': 'productComparePrice', 'min': '0', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'id': 'productStock', 'min': '0'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'id': 'productSKU'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'id': 'productBrand'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'productFeatured'}),
            'is_bestseller': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'productBestseller'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'productActive'}),
        }
    
    def save(self, commit=True):
        product = super().save(commit=False)
        # Handle image upload - map to main_image field
        if 'image' in self.cleaned_data and self.cleaned_data['image']:
            product.main_image = self.cleaned_data['image']
        if commit:
            product.save()
        return product

class DashboardSettingsForm(forms.ModelForm):
    class Meta:
        model = AdminDashboard
        fields = '__all__'
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'business_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'business_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'working_hours': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'booking_policy': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ContactMessageReplyForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['admin_response']
        widgets = {
            'admin_response': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Type your response here...'
            }),
        }

class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['question', 'answer', 'category', 'order', 'is_active']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ['name', 'content', 'rating', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5,
                'step': 1
            }),
        }


class StylistForm(forms.ModelForm):
    class Meta:
        model = Stylist
        fields = ['name', 'title', 'bio', 'image', 'is_available', 'rating', 'experience_years']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'id': 'stylistName'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'id': 'stylistTitle'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'id': 'stylistBio', 'rows': 3}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'id': 'stylistRating', 'min': '0', 'max': '5', 'step': '0.1'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'id': 'stylistExperience', 'min': '0'}),
        }

class AdditionalServiceForm(forms.ModelForm):
    class Meta:
        model = AdditionalService
        fields = ['name', 'description', 'price', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'id': 'addonName'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'id': 'addonDescription', 'rows': 2}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'id': 'addonPrice', 'min': '0', 'step': '0.01'}),
        }

