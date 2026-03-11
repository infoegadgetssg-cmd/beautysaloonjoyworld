# booking/forms.py
from django import forms
from django.utils import timezone
from .models import Booking, AdditionalService, StylistAvailability
from services.models import Service, Stylist
from django.core.exceptions import ValidationError
import datetime

class BookingForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_available=True),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'serviceType'})
    )
    
    stylist = forms.ModelChoiceField(
        queryset=Stylist.objects.filter(is_active=True, is_available=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_stylist'}),
        empty_label="No preference"
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

    agree_cancellation_policy = forms.BooleanField(
        required=True,
        label="I agree to the Cancellation Policy",
        error_messages={'required': 'You must agree to the Cancellation Policy to continue.'}
    )
    
    class Meta:
        model = Booking
        fields = ['service', 'stylist', 'date', 'time', 'notes']
        widgets = {
            'time': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['stylist'].queryset = Stylist.objects.filter(is_active=True, is_available=True)
    
    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date < timezone.now().date():
            raise ValidationError("Appointment date cannot be in the past.")
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        stylist = cleaned_data.get('stylist')
        
        if date and time:
            # Check if the appointment time is within business hours (9am-7pm)
            business_start = datetime.time(9, 0)
            business_end = datetime.time(19, 0)
            
            if time < business_start or time > business_end:
                raise ValidationError("Appointments must be between 9:00 AM and 7:00 PM.")
            
            # Check if appointment is at least 2 hours from now
            selected_datetime = datetime.datetime.combine(date, time)
            if timezone.is_naive(selected_datetime):
                selected_datetime = timezone.make_aware(selected_datetime, timezone.get_current_timezone())

            current_time = timezone.now()
            if selected_datetime < current_time + datetime.timedelta(hours=2):
                raise ValidationError("Appointments must be booked at least 2 hours in advance.")

            # Prevent double-booking the same stylist for the same slot.
            if stylist:
                # Ensure stylist is available for selected day/time.
                day_of_week = date.weekday()
                is_available_slot = StylistAvailability.objects.filter(
                    stylist=stylist,
                    day_of_week=day_of_week,
                    start_time__lte=time,
                    end_time__gte=time,
                    is_available=True
                ).exists()
                if not is_available_slot:
                    raise ValidationError("This stylist is not available at the selected time.")

                conflicting_bookings = Booking.objects.filter(
                    stylist=stylist,
                    date=date,
                    time=time,
                    status__in=[
                        Booking.STATUS_PENDING,
                        Booking.STATUS_AWAITING_PAYMENT,
                        Booking.STATUS_CONFIRMED,
                    ]
                )
                if self.instance and self.instance.pk:
                    conflicting_bookings = conflicting_bookings.exclude(pk=self.instance.pk)

                if conflicting_bookings.exists():
                    raise ValidationError("Stylist is already booked for this time slot.")
        
        return cleaned_data
