# booking/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from services.models import Service, Stylist


class Booking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_AWAITING_PAYMENT = 'awaiting_payment'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_AWAITING_PAYMENT, 'Awaiting Payment'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    REFUND_NOT_REQUIRED = 'NOT_REQUIRED'
    REFUND_PENDING = 'PENDING'
    REFUND_REFUNDED = 'REFUNDED'

    REFUND_STATUS_CHOICES = [
        (REFUND_NOT_REQUIRED, 'Not Required'),
        (REFUND_PENDING, 'Pending'),
        (REFUND_REFUNDED, 'Refunded'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    stylist = models.ForeignKey(Stylist, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    time = models.TimeField()
    duration = models.IntegerField(help_text="Duration in minutes")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_deadline = models.DateTimeField(blank=True, null=True)
    approval_time = models.DateTimeField(blank=True, null=True)
    deposit_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default=REFUND_NOT_REQUIRED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-time']
    
    def __str__(self):
        return f"{self.user.email} - {self.service.name} - {self.date}"

    @property
    def payment_status(self):
        return "PAID" if self.deposit_paid else "UNPAID"

    def save(self, *args, **kwargs):
        if self.total_price and (not self.deposit_amount or self.deposit_amount <= 0):
            self.deposit_amount = (Decimal(self.total_price) * Decimal('0.5')).quantize(Decimal('0.01'))

        if self.status == self.STATUS_AWAITING_PAYMENT:
            if not self.approval_time:
                self.approval_time = timezone.now()
            if not self.payment_deadline:
                self.payment_deadline = self.approval_time + timedelta(hours=48)

        if self.deposit_paid and self.status == self.STATUS_AWAITING_PAYMENT:
            self.status = self.STATUS_CONFIRMED

        if self.status == self.STATUS_CANCELLED:
            if self.payment_status == "PAID" and self.refund_status != self.REFUND_REFUNDED:
                self.refund_status = self.REFUND_PENDING
        elif self.refund_status == self.REFUND_PENDING:
            self.refund_status = self.REFUND_NOT_REQUIRED

        super().save(*args, **kwargs)

class AdditionalService(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - £{self.price}"

class BookingAdditionalService(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='additional_services')
    additional_service = models.ForeignKey(AdditionalService, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.additional_service.name} for Booking #{self.booking.id}"


class StylistAvailability(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    stylist = models.ForeignKey(Stylist, on_delete=models.CASCADE, related_name='availability_slots')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['stylist', 'day_of_week', 'start_time']
        verbose_name_plural = "Stylist Availabilities"

    def __str__(self):
        return f"{self.stylist.name} - {self.get_day_of_week_display()} {self.start_time} to {self.end_time}"
