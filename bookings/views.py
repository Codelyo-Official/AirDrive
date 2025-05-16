from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from .models import Booking, Review
from .forms import BookingForm, ReviewForm
from cars.models import Car

@login_required
def booking_list(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'bookings/booking_list.html', {'bookings': bookings})

@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    
    # Check if user is the booking owner or the car owner
    if request.user != booking.user and request.user != booking.car.owner:
        messages.error(request, "You don't have permission to view this booking.")
        return redirect('booking_list')
    
    return render(request, 'bookings/booking_detail.html', {'booking': booking})

@login_required
def booking_create(request, car_id):
    car = get_object_or_404(Car, pk=car_id, status='available')
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Calculate number of days
            days = (end_date - start_date).days + 1
            
            # Calculate costs
            total_cost = car.daily_rate * Decimal(days)
            platform_fee = total_cost * Decimal('0.10')  # 10% platform fee
            owner_payout = total_cost - platform_fee
            
            booking = form.save(commit=False)
            booking.user = request.user
            booking.car = car
            booking.total_cost = total_cost
            booking.platform_fee = platform_fee
            booking.owner_payout = owner_payout
            
            # Auto-approve if car owner has enabled it
            if car.auto_approve_bookings:
                booking.status = 'approved'
            
            booking.save()
            
            messages.success(request, 'Booking created successfully!')
            return redirect('booking_detail', pk=booking.pk)
    else:
        form = BookingForm()
    
    return render(request, 'bookings/booking_form.html', {'form': form, 'car': car})

@login_required
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    
    # Check if user is the booking owner
    if request.user != booking.user:
        messages.error(request, "You don't have permission to cancel this booking.")
        return redirect('booking_list')
    
    if request.method == 'POST':
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Booking cancelled successfully!')
        return redirect('booking_list')
    
    return render(request, 'bookings/booking_confirm_cancel.html', {'booking': booking})

@login_required
def booking_approve(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    
    # Check if user is the car owner
    if request.user != booking.car.owner:
        messages.error(request, "You don't have permission to approve this booking.")
        return redirect('booking_list')
    
    if request.method == 'POST':
        booking.status = 'approved'
        booking.save()
        messages.success(request, 'Booking approved successfully!')
        return redirect('booking_list')
    
    return render(request, 'bookings/booking_confirm_approve.html', {'booking': booking})

@login_required
def booking_reject(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    
    # Check if user is the car owner
    if request.user != booking.car.owner:
        messages.error(request, "You don't have permission to reject this booking.")
        return redirect('booking_list')
    
    if request.method == 'POST':
        booking.status = 'rejected'
        booking.save()
        messages.success(request, 'Booking rejected successfully!')
        return redirect('booking_list')
    
    return render(request, 'bookings/booking_confirm_reject.html', {'booking': booking})

@login_required
def review_create(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user, status='completed')
    
    # Check if review already exists
    if hasattr(booking, 'review'):
        messages.error(request, 'You have already reviewed this booking.')
        return redirect('booking_detail', pk=booking.pk)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.save()
            messages.success(request, 'Review submitted successfully!')
            return redirect('booking_detail', pk=booking.pk)
    else:
        form = ReviewForm()
    
    return render(request, 'bookings/review_form.html', {'form': form, 'booking': booking})
