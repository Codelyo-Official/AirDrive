from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from .models import Booking, Review,Report
from .forms import BookingForm, ReviewForm
from cars.models import Car
from rest_framework.permissions import IsAuthenticated
from .serializers import BookingSerializer,ReportSerializer,BookingCreateSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import api_view, permission_classes


class AdminReportListAPIView(generics.ListAPIView):
    serializer_class = ReportSerializer

    def get_queryset(self):
        queryset = Report.objects.all()
        report_type = self.request.query_params.get("report_type")
        status = self.request.query_params.get("status")

        if report_type:
            queryset = queryset.filter(report_type=report_type)
        if status:
            queryset = queryset.filter(status=status)

        return queryset
class AdminReportUpdateAPIView(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        status = request.data.get('status')
        notes = request.data.get('admin_notes', '')
        suspend_user = request.data.get('suspend_user', False)
        remove_car = request.data.get('remove_car', False)

        report.status = status
        report.admin_notes = notes
        report.save()

        if status == 'resolved':
            if report.report_type == 'user' and suspend_user:
                report.reported_user.is_suspended = True
                report.reported_user.save()
            elif report.report_type == 'car' and remove_car:
                report.reported_car.delete()

        return Response({'message': 'Report updated successfully'})

class AdminBookingUpdateAPIView(generics.UpdateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'


class AdminBookingListAPIView(generics.ListAPIView):
    serializer_class = BookingSerializer

    def get_queryset(self):
        queryset = Booking.objects.all()
        status = self.request.query_params.get("status")
        user_id = self.request.query_params.get("user_id")
        car_id = self.request.query_params.get("car_id")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if status:
            queryset = queryset.filter(status=status)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if car_id:
            queryset = queryset.filter(car_id=car_id)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        return queryset


class MyBookingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')

        data = []
        for booking in bookings:
            data.append({
                "booking_id": booking.id,
                "car": {
                    "id": booking.car.id,
                    "make": booking.car.make,
                    "model": booking.car.model,
                    "year": booking.car.year,
                    "license_plate": booking.car.license_plate,
                },
                "start_date": booking.start_date,
                "end_date": booking.end_date,
                "status": booking.status,
                "total_cost": str(booking.total_cost),
                "platform_fee": str(booking.platform_fee),
                "owner_payout": str(booking.owner_payout),
                "created_at": booking.created_at,
            })

        return Response(data)


class BookingCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            booking = serializer.save()
            return Response({
                "message": "Booking created successfully.",
                "booking_id": booking.id,
                "status": booking.status,
                "total_cost": str(booking.total_cost),
                "platform_fee": str(booking.platform_fee),
                "owner_payout": str(booking.owner_payout)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReportCreateAPIView(APIView):
    def post(self, request):
        data = request.data
        report_type = data.get('report_type')
        reason = data.get('reason')
        reported_user_id = data.get('reported_user_id')
        reported_car_id = data.get('reported_car_id')

        if report_type not in ['user', 'car']:
            return Response({'error': 'Invalid report_type'}, status=status.HTTP_400_BAD_REQUEST)

        if not reason:
            return Response({'error': 'Reason is required'}, status=status.HTTP_400_BAD_REQUEST)

        if report_type == 'user':
            if not reported_user_id:
                return Response({'error': 'reported_user_id is required for user reports'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                reported_user = User.objects.get(id=reported_user_id)
            except User.DoesNotExist:
                return Response({'error': 'Reported user does not exist'}, status=status.HTTP_404_NOT_FOUND)
            
            report = Report.objects.create(
                report_type='user',
                reason=reason,
                reported_user=reported_user
            )
        else:  # report_type == 'car'
            if not reported_car_id:
                return Response({'error': 'reported_car_id is required for car reports'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                reported_car = Car.objects.get(id=reported_car_id)
            except Car.DoesNotExist:
                return Response({'error': 'Reported car does not exist'}, status=status.HTTP_404_NOT_FOUND)
            
            report = Report.objects.create(
                report_type='car',
                reporter=request.user,
                reason=reason,
                reported_car=reported_car
            )

        return Response({'message': 'Report created successfully'}, status=status.HTTP_201_CREATED)


class BookingApprovalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        action = request.data.get("action")
        if action not in ["approve", "reject"]:
            return Response(
                {"error": "Invalid action. Must be 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking = Booking.objects.select_related('car').get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if the logged-in user is the car owner
        if booking.car.owner != request.user:
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        # Only allow approval or rejection if booking is still pending
        if booking.status != 'pending':
            return Response({"error": "Only pending bookings can be updated."}, status=status.HTTP_400_BAD_REQUEST)

        # Update status
        booking.status = 'approved' if action == 'approve' else 'rejected'
        booking.save()

        return Response({"message": f"Booking {action}d successfully."}, status=status.HTTP_200_OK)


class OwnerBookingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all bookings for cars owned by the current user
        bookings = Booking.objects.filter(car__owner=request.user)

        # Optional status filter
        status_filter = request.query_params.get('status')
        if status_filter:
            bookings = bookings.filter(status=status_filter)

        bookings = bookings.order_by('-created_at')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_booking(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

    # Only owner of car or admin can mark it completed
    if booking.car.owner != request.user and not request.user.is_staff:
        return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    if booking.status != 'approved':
        return Response({"error": "Only approved bookings can be marked as completed."}, status=status.HTTP_400_BAD_REQUEST)

    booking.status = 'completed'
    booking.save()

    # Award points if regular user
    if booking.user.user_type == 'regular':
        booking.user.points += 50  # You can change this logic if you want
        booking.user.save()

    return Response({
        "message": "Booking marked as completed. Points awarded.",
        "awarded_points": 50,
        "total_user_points": booking.user.points
    }, status=status.HTTP_200_OK)








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
