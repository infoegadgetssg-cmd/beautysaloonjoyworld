# shop/forms.py
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import ProductReview

class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter review title'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience with this product...'
            }),
        }


class CheckoutForm(forms.Form):
    PAYMENT_METHODS = [
        ('paystack', 'Pay with Card (Paystack)'),
        ('paypal', 'Pay with PayPal'),
        ('walk_in', 'Pay at Salon (Walk-in)'),
    ]

    shipping_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your shipping address'
        }),
        label="Shipping Address"
    )

    billing_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your billing address (if different)'
        }),
        required=False,
        label="Billing Address"
    )

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='paystack'
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any special instructions or notes...'
        }),
        required=False,
        label="Order Notes"
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        label="I agree to the terms and conditions"
    )