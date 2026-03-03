# services/forms.py
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import ServiceReview

class ServiceReviewForm(forms.ModelForm):
    """Form for submitting service reviews"""
    rating = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'min': '1',
            'max': '5',
            'step': '1',
            'class': 'form-range'
        }),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Share your experience with this service...'
        })
    )

    class Meta:
        model = ServiceReview
        fields = ['rating', 'comment']

class ServiceSearchForm(forms.Form):
    """Form for searching services"""
    category = forms.CharField(required=False, widget=forms.HiddenInput())
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search services...'
        })
    )
    price_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price'
        })
    )
    price_max = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price'
        })
    )
    duration_min = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min duration'
        })
    )
    duration_max = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max duration'
        })
    )