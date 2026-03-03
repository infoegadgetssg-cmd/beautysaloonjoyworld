# booking/forms.py
from django import forms
from django.utils import timezone
from .models import Booking, AdditionalService
from services.models import Service, Stylist
from django.core.exceptions import ValidationError
import datetime

class BookingForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_available=True),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'serviceType'})
    )
    
    stylist = forms.ModelChoiceField(
        queryset=Stylist.objects.filter(is_available=True),
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'stylist-option'}),
        empty_label="Any Available Stylist"
    )
    
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'appointmentDate'
        })
    )
    
    time = forms.TimeField(
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'selectedTime'})
    )
    
    additional_services = forms.ModelMultipleChoiceField(
        queryset=AdditionalService.objects.filter(is_available=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Add Additional Services"
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'id': 'notes',
            'placeholder': 'Any allergies, skin conditions, or special requirements we should know about?'
        })
    )
    
    class Meta:
        model = Booking
        fields = ['service', 'stylist', 'date', 'time', 'notes']
        widgets = {
            'time': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date < timezone.now().date():
            raise ValidationError("Appointment date cannot be in the past.")
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        
        if date and time:
            # Check if the appointment time is within business hours (9am-7pm)
            appointment_datetime = datetime.datetime.combine(date, time)
            business_start = datetime.time(9, 0)
            business_end = datetime.time(19, 0)
            
            if time < business_start or time > business_end:
                raise ValidationError("Appointments must be between 9:00 AM and 7:00 PM.")
            
            # Check if appointment is at least 2 hours from now
            if datetime.datetime.combine(date, time) < timezone.now() + datetime.timedelta(hours=2):
                raise ValidationError("Appointments must be booked at least 2 hours in advance.")
        
        return cleaned_data