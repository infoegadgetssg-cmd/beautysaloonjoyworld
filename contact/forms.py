# contact/forms.py
from django import forms
from django.core.validators import RegexValidator
from .models import ContactMessage, NewsletterSubscriber


class ContactForm(forms.ModelForm):
    """Contact form matching your original design"""
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    phone = forms.CharField(
        validators=[phone_regex],
        max_length=17,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Phone Number (Optional)'
        })
    )
    
    # Additional validation for name
    name = forms.CharField(
        min_length=2,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Full Name *'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control form-textarea',
            'rows': 5,
            'placeholder': 'Tell us how we can help you...'
        })
    )
    
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'topic', 'message', 'subscribe_newsletter']
        
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email Address *'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject *'
            }),
            'topic': forms.Select(attrs={
                'class': 'form-select'
            }),
            'subscribe_newsletter': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default topic choices
        self.fields['topic'].choices = [
            ('', 'Select a subject'),
            ('general', 'General Inquiry'),
            ('booking', 'Booking Question'),
            ('service', 'Service Information'),
            ('product', 'Product Question'),
            ('complaint', 'Complaint'),
            ('other', 'Other'),
        ]


class NewsletterSignupForm(forms.ModelForm):
    """Simplified newsletter signup form"""
    class Meta:
        model = NewsletterSubscriber
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Name (Optional)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email Address *'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if NewsletterSubscriber.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("This email is already subscribed to our newsletter.")
        return email


class QuickContactForm(forms.Form):
    """Form for quick contact options"""
    contact_method = forms.ChoiceField(
        choices=[
            ('call', 'Call Us'),
            ('whatsapp', 'WhatsApp'),
            ('directions', 'Get Directions'),
        ],
        widget=forms.HiddenInput()
    )
    
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Name'
        })
    )
    
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Your message...',
            'rows': 3
        })
    )