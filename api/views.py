from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import  Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.shortcuts import get_object_or_404
from users.models import User
from cars.models import Car, CarImage, CarFeature, CarAvailability
from bookings.models import Booking, Review, Report
from .serializers import (
    UserSerializer, CarSerializer, BookingSerializer, ReviewSerializer,
    CarImageSerializer, CarFeatureSerializer, CarAvailabilitySerializer,
    RegisterSerializer, LoginSerializer, ReportSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    
    def get_queryset(self):
        queryset = Car.objects.all()
        
        # Filter by status for non-admin users
        if not self.request.user.is_staff:
            queryset = queryset.filter(status='available')
        
        # Filter by owner if requested
        owner_id = self.request.query_params.get('owner', None)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        
        # Filter by location
        location = self.request.query_params.get('location', None)
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin can see all bookings
        if user.is_staff:
            return Booking.objects.all()
        
        # Car owners can see bookings for their cars
        if user.user_type == 'owner':
            return Booking.objects.filter(car__owner=user)
        
        # Regular users can see their own bookings
        return Booking.objects.filter(user=user)
    
    def perform_create(self, serializer):
        user = self.request.user
        car = Car.objects.get(pk=self.request.data.get('car'))
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        
        # Calculate number of days
        days = (end_date - start_date).days
        
        # Calculate costs
        total_cost = car.daily_rate * days
        platform_fee = total_cost * Decimal('0.10')  # 10% platform fee
        owner_payout = total_cost - platform_fee
        
        # Set status based on auto_approve_bookings
        status = 'approved' if car.auto_approve_bookings else 'pending'
        
        booking = serializer.save(
            user=user,
            total_cost=total_cost,
            platform_fee=platform_fee,
            owner_payout=owner_payout,
            status=status
        )
        
        # Send confirmation email to user
        self.send_booking_confirmation_email(booking)
        
        # If booking is pending, notify car owner
        if status == 'pending':
            self.send_booking_request_email(booking)
    
    def send_booking_confirmation_email(self, booking):
        """Send booking confirmation email to user"""
        subject = f'Booking Confirmation - {booking.car}'
        html_message = render_to_string('bookings/email/booking_confirmation.html', {
            'booking': booking,
            'user': booking.user,
            'car': booking.car
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = booking.user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
    
    def send_booking_request_email(self, booking):
        """Send booking request email to car owner"""
        subject = f'New Booking Request - {booking.car}'
        html_message = render_to_string('bookings/email/booking_request.html', {
            'booking': booking,
            'user': booking.user,
            'car': booking.car,
            'owner': booking.car.owner
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = booking.car.owner.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    
    def perform_create(self, serializer):
        booking_id = self.request.data.get('booking')
        booking = Booking.objects.get(id=booking_id)
        
        # Check if user is the booking owner
        if self.request.user != booking.user:
            return Response({"error": "You can only review your own bookings."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer.save()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token.key
        })

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "user": UserSerializer(user).data,
                "token": token.key
            })
        
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ProfileView(APIView):
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CarImageView(APIView):
    def post(self, request):
        serializer = CarImageSerializer(data=request.data)
        if serializer.is_valid():
            # Check if user is the car owner
            car = Car.objects.get(id=request.data.get('car'))
            if request.user != car.owner:
                return Response({"error": "You can only add images to your own cars."}, status=status.HTTP_403_FORBIDDEN)
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CarFeatureView(APIView):
    def post(self, request):
        serializer = CarFeatureSerializer(data=request.data)
        if serializer.is_valid():
            # Check if user is the car owner
            car = Car.objects.get(id=request.data.get('car'))
            if request.user != car.owner:
                return Response({"error": "You can only add features to your own cars."}, status=status.HTTP_403_FORBIDDEN)
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CarAvailabilityView(APIView):
    def post(self, request):
        serializer = CarAvailabilitySerializer(data=request.data)
        if serializer.is_valid():
            # Check if user is the car owner
            car = Car.objects.get(id=request.data.get('car'))
            if request.user != car.owner:
                return Response({"error": "You can only add availability to your own cars."}, status=status.HTTP_403_FORBIDDEN)
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DashboardView(APIView):
    def get(self, request):
        user = request.user
        
        if user.is_staff:
            # Admin dashboard
            total_users = User.objects.count()
            total_cars = Car.objects.count()
            total_bookings = Booking.objects.count()
            total_revenue = Booking.objects.filter(status='completed').aggregate(Sum('platform_fee'))['platform_fee__sum'] or 0
            
            # Recent activity
            recent_users = User.objects.order_by('-date_joined')[:5]
            recent_cars = Car.objects.order_by('-created_at')[:5]
            recent_bookings = Booking.objects.order_by('-created_at')[:5]
            
            # Pending approvals
            pending_cars = Car.objects.filter(status='pending_approval').count()
            pending_bookings = Booking.objects.filter(status='pending').count()
            
            # Additional analytics
            user_growth = User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count()
            revenue_growth = Booking.objects.filter(
                status='completed', 
                updated_at__gte=timezone.now() - timedelta(days=30)
            ).aggregate(Sum('platform_fee'))['platform_fee__sum'] or 0
            
            # User statistics
            regular_users = User.objects.filter(user_type='regular').count()
            car_owners = User.objects.filter(user_type='owner').count()
            suspended_users = User.objects.filter(is_suspended=True).count()
            
            # Car statistics
            available_cars = Car.objects.filter(status='available').count()
            booked_cars = Car.objects.filter(status='booked').count()
            maintenance_cars = Car.objects.filter(status='maintenance').count()
            
            # Booking statistics by month (last 6 months)
            months = []
            bookings_by_month = []
            revenue_by_month = []
            
            for i in range(5, -1, -1):
                month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
                month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                
                month_bookings = Booking.objects.filter(
                    created_at__gte=month_start,
                    created_at__lte=month_end
                ).count()
                
                month_revenue = Booking.objects.filter(
                    status='completed',
                    updated_at__gte=month_start,
                    updated_at__lte=month_end
                ).aggregate(Sum('platform_fee'))['platform_fee__sum'] or 0
                
                months.append(month_start.strftime('%b %Y'))
                bookings_by_month.append(month_bookings)
                revenue_by_month.append(float(month_revenue))
            
            return Response({
                'total_users': total_users,
                'total_cars': total_cars,
                'total_bookings': total_bookings,
                'total_revenue': total_revenue,
                'recent_users': UserSerializer(recent_users, many=True).data,
                'recent_cars': CarSerializer(recent_cars, many=True).data,
                'recent_bookings': BookingSerializer(recent_bookings, many=True).data,
                'pending_cars': pending_cars,
                'pending_bookings': pending_bookings,
                'analytics': {
                    'user_growth': user_growth,
                    'revenue_growth': revenue_growth,
                    'user_statistics': {
                        'regular_users': regular_users,
                        'car_owners': car_owners,
                        'suspended_users': suspended_users
                    },
                    'car_statistics': {
                        'available_cars': available_cars,
                        'booked_cars': booked_cars,
                        'maintenance_cars': maintenance_cars
                    },
                    'monthly_data': {
                        'months': months,
                        'bookings': bookings_by_month,
                        'revenue': revenue_by_month
                    }
                }
            })
        
        # Rest of the method remains unchanged for non-admin users
        elif user.user_type == 'owner':
            # Car owner dashboard
            user_cars = Car.objects.filter(owner=user)
            total_cars = user_cars.count()
            
            # Booking statistics
            upcoming_bookings = Booking.objects.filter(
                car__owner=user, 
                status='approved',
                start_date__gte=timezone.now().date()
            ).count()
            
            completed_bookings = Booking.objects.filter(
                car__owner=user, 
                status='completed'
            ).count()
            
            pending_bookings = Booking.objects.filter(
                car__owner=user, 
                status='pending'
            ).count()
            
            # Revenue
            total_revenue = Booking.objects.filter(
                car__owner=user, 
                status='completed'
            ).aggregate(Sum('owner_payout'))['owner_payout__sum'] or 0
            
            # Recent bookings
            recent_bookings = Booking.objects.filter(
                car__owner=user
            ).order_by('-created_at')[:5]
            
            return Response({
                'total_cars': total_cars,
                'upcoming_bookings': upcoming_bookings,
                'completed_bookings': completed_bookings,
                'pending_bookings': pending_bookings,
                'total_revenue': total_revenue,
                'recent_bookings': BookingSerializer(recent_bookings, many=True).data,
            })
        
        else:
            # Regular user dashboard
            upcoming_bookings = Booking.objects.filter(
                user=user, 
                status='approved',
                start_date__gte=timezone.now().date()
            ).count()
            
            past_bookings = Booking.objects.filter(
                user=user, 
                status='completed'
            ).count()
            
            pending_bookings = Booking.objects.filter(
                user=user, 
                status='pending'
            ).count()
            
            # Recent bookings
            recent_bookings = Booking.objects.filter(
                user=user
            ).order_by('-created_at')[:5]
            
            return Response({
                'upcoming_bookings': upcoming_bookings,
                'past_bookings': past_bookings,
                'pending_bookings': pending_bookings,
                'recent_bookings': BookingSerializer(recent_bookings, many=True).data,
            })

class BecomeOwnerView(APIView):
    def post(self, request):
        user = request.user
        
        # Check if user is already an owner
        if user.user_type == 'owner':
            return Response({"message": "You are already registered as a car owner."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update user type to owner
        user.user_type = 'owner'
        user.save()
        
        return Response({
            "message": "You have successfully registered as a car owner.",
            "user": UserSerializer(user).data
        })

class CarCreateView(APIView):
    def post(self, request):
        # Check if user is a car owner
        if request.user.user_type != 'owner':
            return Response({"error": "Only car owners can list cars."}, status=status.HTTP_403_FORBIDDEN)
        
        # Create car
        car_data = {
            'make': request.data.get('make'),
            'model': request.data.get('model'),
            'year': request.data.get('year'),
            'color': request.data.get('color'),
            'license_plate': request.data.get('license_plate'),
            'description': request.data.get('description'),
            'daily_rate': request.data.get('daily_rate'),
            'location': request.data.get('location'),
            'latitude': request.data.get('latitude'),
            'longitude': request.data.get('longitude'),
            'seats': request.data.get('seats'),
            'transmission': request.data.get('transmission'),
            'fuel_type': request.data.get('fuel_type'),
            'auto_approve_bookings': request.data.get('auto_approve_bookings', False)
        }
        
        car_serializer = CarSerializer(data=car_data)
        if not car_serializer.is_valid():
            return Response(car_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        car = car_serializer.save(owner=request.user)
        
        # Process images if provided
        images = request.FILES.getlist('images')
        primary_image_index = request.data.get('primary_image_index', 0)
        
        for i, image in enumerate(images):
            is_primary = (i == int(primary_image_index))
            CarImage.objects.create(car=car, image=image, is_primary=is_primary)
        
        # Process features if provided
        features = request.data.get('features', [])
        if isinstance(features, str):
            features = features.split(',')
            
        for feature in features:
            CarFeature.objects.create(car=car, name=feature.strip())
        
        # Process availability if provided
        availability_data = request.data.get('availability', [])
        if availability_data:
            for period in availability_data:
                CarAvailability.objects.create(
                    car=car,
                    start_date=period.get('start_date'),
                    end_date=period.get('end_date')
                )
        
        return Response(CarSerializer(car).data, status=status.HTTP_201_CREATED)

class OwnerCarsView(APIView):
    def get(self, request):
        # Check if user is a car owner
        if request.user.user_type != 'owner':
            return Response({"error": "Only car owners can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
        
        cars = Car.objects.filter(owner=request.user)
        serializer = CarSerializer(cars, many=True)
        return Response(serializer.data)

class OwnerBookingsView(APIView):
    def get(self, request):
        # Check if user is a car owner
        if request.user.user_type != 'owner':
            return Response({"error": "Only car owners can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
        
        status_filter = request.query_params.get('status', None)
        
        bookings = Booking.objects.filter(car__owner=request.user)
        
        if status_filter:
            bookings = bookings.filter(status=status_filter)
        
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

class BookingApprovalView(APIView):
    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is the car owner
        if request.user != booking.car.owner:
            return Response({"error": "You can only approve bookings for your own cars."}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if booking is in pending status
        if booking.status != 'pending':
            return Response({"error": f"Cannot change status. Booking is already {booking.status}."}, status=status.HTTP_400_BAD_REQUEST)
        
        booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user)
        action = request.data.get('action')
        
        if action == 'approve':
            booking.status = 'approved'
            booking.save()
            # Send approval email
            self.send_booking_approval_email(booking)
            return Response({"message": "Booking approved successfully."}, status=status.HTTP_200_OK)
        elif action == 'reject':
            booking.status = 'rejected'
            booking.save()
            # Send rejection email
            self.send_booking_rejection_email(booking)
            return Response({"message": "Booking rejected successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid action. Use 'approve' or 'reject'."}, 
                           status=status.HTTP_400_BAD_REQUEST)
    
    def send_booking_approval_email(self, booking):
        """Send booking approval email to user"""
        subject = f'Booking Approved - {booking.car}'
        html_message = render_to_string('bookings/email/booking_approved.html', {
            'booking': booking,
            'user': booking.user,
            'car': booking.car
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = booking.user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
    
    def send_booking_rejection_email(self, booking):
        """Send booking rejection email to user"""
        subject = f'Booking Rejected - {booking.car}'
        html_message = render_to_string('bookings/email/booking_rejected.html', {
            'booking': booking,
            'user': booking.user,
            'car': booking.car
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = booking.user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

class AdminBookingManagementView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        # Get query parameters for filtering
        status_filter = request.query_params.get('status', None)
        user_id = request.query_params.get('user_id', None)
        car_id = request.query_params.get('car_id', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        
        # Start with all bookings
        bookings = Booking.objects.all()
        
        # Apply filters
        if status_filter:
            bookings = bookings.filter(status=status_filter)
        
        if user_id:
            bookings = bookings.filter(user_id=user_id)
        
        if car_id:
            bookings = bookings.filter(car_id=car_id)
        
        if start_date:
            bookings = bookings.filter(start_date__gte=start_date)
        
        if end_date:
            bookings = bookings.filter(end_date__lte=end_date)
        
        # Paginate results
        page = self.paginate_queryset(bookings)
        if page is not None:
            serializer = BookingSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)
    
    def put(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = BookingSerializer(booking, data=request.data, partial=True)
        if serializer.is_valid():
            booking = serializer.save()
            
            # If status is changed, send appropriate notifications
            if 'status' in request.data:
                if booking.status == 'approved':
                    self.send_booking_approval_email(booking)
                elif booking.status == 'rejected':
                    self.send_booking_rejection_email(booking)
                elif booking.status == 'completed':
                    self.send_booking_completion_email(booking)
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Helper methods for pagination and email sending
    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from rest_framework.pagination import PageNumberPagination
            self._paginator = PageNumberPagination()
        return self._paginator
    
    def paginate_queryset(self, queryset):
        return self.paginator.paginate_queryset(queryset, self.request, view=self)
    
    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)
    
    def send_booking_approval_email(self, booking):
        """Send booking approval email to user"""
        subject = f'Booking Approved - {booking.car}'
        html_message = render_to_string('bookings/email/booking_approved.html', {
            'booking': booking,
            'user': booking.user,
            'car': booking.car
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = booking.user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
    
    def send_booking_rejection_email(self, booking):
        """Send booking rejection email to user"""
        subject = f'Booking Rejected - {booking.car}'
        html_message = render_to_string('bookings/email/booking_rejected.html', {
            'booking': booking,
            'user': booking.user,
            'car': booking.car
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = booking.user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
    
    def send_booking_completion_email(self, booking):
        """Send booking completion email to user"""
        subject = f'Booking Completed - {booking.car}'
        html_message = render_to_string('bookings/email/booking_completed.html', {
            'booking': booking,
            'user': booking.user,
            'car': booking.car
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = booking.user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

class AdminRevenueReportView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        report_type = request.query_params.get('type', 'monthly')
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            # Default to last 6 months
            start_date = (timezone.now() - timedelta(days=180)).date()
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
        
        if report_type == 'daily':
            return self.get_daily_report(start_date, end_date)
        elif report_type == 'weekly':
            return self.get_weekly_report(start_date, end_date)
        elif report_type == 'monthly':
            return self.get_monthly_report(start_date, end_date)
        elif report_type == 'yearly':
            return self.get_yearly_report(start_date, end_date)
        else:
            return Response({"error": "Invalid report type. Use 'daily', 'weekly', 'monthly', or 'yearly'"}, 
                           status=status.HTTP_400_BAD_REQUEST)
    
    def get_daily_report(self, start_date, end_date):
        # Generate a list of all days in the range
        days = []
        bookings_data = []
        revenue_data = []
        platform_fee_data = []
        owner_payout_data = []
        
        current_date = start_date
        while current_date <= end_date:
            # Get bookings for this day
            day_bookings = Booking.objects.filter(
                created_at__date=current_date
            )
            
            # Get completed bookings for revenue calculation
            completed_bookings = Booking.objects.filter(
                status='completed',
                updated_at__date=current_date
            )
            
            # Calculate metrics
            booking_count = day_bookings.count()
            total_revenue = completed_bookings.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
            platform_fee = completed_bookings.aggregate(Sum('platform_fee'))['platform_fee__sum'] or 0
            owner_payout = completed_bookings.aggregate(Sum('owner_payout'))['owner_payout__sum'] or 0
            
            # Append to data lists
            days.append(current_date.strftime('%Y-%m-%d'))
            bookings_data.append(booking_count)
            revenue_data.append(float(total_revenue))
            platform_fee_data.append(float(platform_fee))
            owner_payout_data.append(float(owner_payout))
            
            # Move to next day
            current_date += timedelta(days=1)
        
        return Response({
            'report_type': 'daily',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'labels': days,
            'bookings': bookings_data,
            'revenue': revenue_data,
            'platform_fee': platform_fee_data,
            'owner_payout': owner_payout_data,
            'totals': {
                'bookings': sum(bookings_data),
                'revenue': sum(revenue_data),
                'platform_fee': sum(platform_fee_data),
                'owner_payout': sum(owner_payout_data)
            }
        })
    
    def get_weekly_report(self, start_date, end_date):
        # Similar implementation to daily report but grouped by week
        # Implementation details omitted for brevity
        pass
    
    def get_monthly_report(self, start_date, end_date):
        # Generate a list of all months in the range
        months = []
        bookings_data = []
        revenue_data = []
        platform_fee_data = []
        owner_payout_data = []
        
        # Get the first day of the start month
        current_month = start_date.replace(day=1)
        
        # Get the last day of the end month
        if end_date.month == 12:
            end_month = end_date.replace(year=end_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_month = end_date.replace(month=end_date.month + 1, day=1) - timedelta(days=1)
        
        while current_month <= end_month:
            # Calculate the last day of the current month
            if current_month.month == 12:
                last_day = current_month.replace(year=current_month.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = current_month.replace(month=current_month.month + 1, day=1) - timedelta(days=1)
            
            # Get bookings for this month
            month_bookings = Booking.objects.filter(
                created_at__gte=current_month,
                created_at__lte=last_day
            )
            
            # Get completed bookings for revenue calculation
            completed_bookings = Booking.objects.filter(
                status='completed',
                updated_at__gte=current_month,
                updated_at__lte=last_day
            )
            
            # Calculate metrics
            booking_count = month_bookings.count()
            total_revenue = completed_bookings.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
            platform_fee = completed_bookings.aggregate(Sum('platform_fee'))['platform_fee__sum'] or 0
            owner_payout = completed_bookings.aggregate(Sum('owner_payout'))['owner_payout__sum'] or 0
            
            # Append to data lists
            months.append(current_month.strftime('%b %Y'))
            bookings_data.append(booking_count)
            revenue_data.append(float(total_revenue))
            platform_fee_data.append(float(platform_fee))
            owner_payout_data.append(float(owner_payout))
            
            # Move to next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)
        
        return Response({
            'report_type': 'monthly',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'labels': months,
            'bookings': bookings_data,
            'revenue': revenue_data,
            'platform_fee': platform_fee_data,
            'owner_payout': owner_payout_data,
            'totals': {
                'bookings': sum(bookings_data),
               'revenue': sum(revenue_data),
                'platform_fee': sum(platform_fee_data),
                'owner_payout': sum(owner_payout_data)
            }
        })
class ReportCreateView(APIView):
    def post(self, request):
        report_type = request.data.get('report_type')
        reason = request.data.get('reason')
        reported_user_id = request.data.get('reported_user_id', None)
        reported_car_id = request.data.get('reported_car_id', None)
        
        if not reason:
            return Response({"error": "Reason is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if report_type == 'user' and not reported_user_id:
            return Response({"error": "Reported user ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if report_type == 'car' and not reported_car_id:
            return Response({"error": "Reported car ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create report
        report_data = {
            'reporter': request.user,
            'report_type': report_type,
            'reason': reason
        }
        
        if report_type == 'user':
            try:
                reported_user = User.objects.get(id=reported_user_id)
                report_data['reported_user'] = reported_user
            except User.DoesNotExist:
                return Response({"error": "Reported user not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                reported_car = Car.objects.get(id=reported_car_id)
                report_data['reported_car'] = reported_car
            except Car.DoesNotExist:
                return Response({"error": "Reported car not found"}, status=status.HTTP_404_NOT_FOUND)
        
        report = Report.objects.create(**report_data)
        
        # Notify admin about new report
        self.send_new_report_notification(report)
        
        return Response({"message": "Report submitted successfully"}, status=status.HTTP_201_CREATED)
    
    def send_new_report_notification(self, report):
        """Send notification to admins about new report"""
        admin_emails = User.objects.filter(is_staff=True).values_list('email', flat=True)
        
        if report.report_type == 'user':
            subject = f'New User Report: {report.reported_user.username}'
        else:
            subject = f'New Car Report: {report.reported_car}'
        
        html_message = render_to_string('reports/email/new_report.html', {
            'report': report
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        
        send_mail(
            subject,
            plain_message,
            from_email,
            list(admin_emails),
            html_message=html_message,
            fail_silently=False,
        )

class AdminReportManagementView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        # Get query parameters for filtering
        report_type = request.query_params.get('report_type', None)
        status_filter = request.query_params.get('status', None)
        
        # Start with all reports
        reports = Report.objects.all().order_by('-created_at')
        
        # Apply filters
        if report_type:
            reports = reports.filter(report_type=report_type)
        
        if status_filter:
            reports = reports.filter(status=status_filter)
        
        # Paginate results
        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = ReportSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)
    
    def put(self, request, report_id):
        try:
            report = Report.objects.get(id=report_id)
        except Report.DoesNotExist:
            return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ReportSerializer(report, data=request.data, partial=True)
        if serializer.is_valid():
            report = serializer.save()
            
            # If status changed to resolved, take action based on report type
            if 'status' in request.data and request.data['status'] == 'resolved':
                if report.report_type == 'user' and report.reported_user:
                    # Option to suspend user
                    suspend_user = request.data.get('suspend_user', False)
                    if suspend_user:
                        user = report.reported_user
                        user.is_suspended = True
                        user.save()
                        self.send_suspension_email(user)
                
                elif report.report_type == 'car' and report.reported_car:
                    # Option to remove car listing
                    remove_car = request.data.get('remove_car', False)
                    if remove_car:
                        car = report.reported_car
                        car.status = 'rejected'
                        car.save()
                        self.send_car_removal_email(car)
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Helper methods for pagination and email sending
    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from rest_framework.pagination import PageNumberPagination
            self._paginator = PageNumberPagination()
        return self._paginator
    
    def paginate_queryset(self, queryset):
        return self.paginator.paginate_queryset(queryset, self.request, view=self)
    
    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)
    
    def send_suspension_email(self, user):
        """Send account suspension email to user"""
        subject = 'Your Account Has Been Suspended'
        html_message = render_to_string('users/email/account_suspended.html', {
            'user': user,
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
    
    def send_car_removal_email(self, car):
        """Send car removal email to owner"""
        subject = f'Your Car Listing Has Been Removed - {car}'
        html_message = render_to_string('cars/email/car_removed.html', {
            'car': car,
            'owner': car.owner
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = car.owner.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

class AdminUserManagementView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        # Get query parameters for filtering
        user_type = request.query_params.get('user_type', None)
        is_verified = request.query_params.get('is_verified', None)
        is_suspended = request.query_params.get('is_suspended', None)
        search_query = request.query_params.get('search', None)
        
        # Start with all users
        users = User.objects.all()
        
        # Apply filters
        if user_type:
            users = users.filter(user_type=user_type)
        
        if is_verified is not None:
            is_verified = is_verified.lower() == 'true'
            users = users.filter(is_verified=is_verified)
        
        if is_suspended is not None:
            is_suspended = is_suspended.lower() == 'true'
            users = users.filter(is_suspended=is_suspended)
        
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Paginate results
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = UserSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            
            # If suspension status changed, send notification
            if 'is_suspended' in request.data and request.data['is_suspended'] != user.is_suspended:
                if user.is_suspended:
                    self.send_suspension_email(user)
                else:
                    self.send_unsuspension_email(user)
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Store username for response
        username = user.username
        
        # Delete user
        user.delete()
        
        return Response({"message": f"User {username} has been deleted"}, status=status.HTTP_200_OK)
    
    # Helper methods for pagination and email sending
    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from rest_framework.pagination import PageNumberPagination
            self._paginator = PageNumberPagination()
        return self._paginator
    
    def paginate_queryset(self, queryset):
        return self.paginator.paginate_queryset(queryset, self.request, view=self)
    
    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)
    
    def send_suspension_email(self, user):
        """Send account suspension email to user"""
        subject = 'Your Account Has Been Suspended'
        html_message = render_to_string('users/email/account_suspended.html', {
            'user': user,
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
    
    def send_unsuspension_email(self, user):
        """Send account unsuspension email to user"""
        subject = 'Your Account Has Been Restored'
        html_message = render_to_string('users/email/account_restored.html', {
            'user': user,
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = user.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )

class AdminCarApprovalView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        # Get query parameters for filtering
        status_filter = request.query_params.get('status', None)
        owner_id = request.query_params.get('owner_id', None)
        search_query = request.query_params.get('search', None)
        
        # Start with all cars
        cars = Car.objects.all()
        
        # Apply filters
        if status_filter:
            cars = cars.filter(status=status_filter)
        
        if owner_id:
            cars = cars.filter(owner_id=owner_id)
        
        if search_query:
            cars = cars.filter(
                models.Q(make__icontains=search_query) |
                models.Q(model__icontains=search_query) |
                models.Q(license_plate__icontains=search_query) |
                models.Q(owner__username__icontains=search_query)
            )
        
        # Paginate results
        page = self.paginate_queryset(cars)
        if page is not None:
            serializer = CarSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CarSerializer(cars, many=True)
        return Response(serializer.data)
    
    def put(self, request, car_id):
        try:
            car = Car.objects.get(id=car_id)
        except Car.DoesNotExist:
            return Response({"error": "Car not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CarSerializer(car, data=request.data, partial=True)
        if serializer.is_valid():
            car = serializer.save()
            
            # If status changed, send notification
            if 'status' in request.data and request.data['status'] != car.status:
                if car.status == 'available':
                    self.send_car_approval_email(car)
                elif car.status == 'rejected':
                    self.send_car_rejection_email(car)
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, car_id):
        try:
            car = Car.objects.get(id=car_id)
        except Car.DoesNotExist:
            return Response({"error": "Car not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Store car info for response
        car_info = f"{car.year} {car.make} {car.model}"
        
        # Delete car
        car.delete()
        
        return Response({"message": f"Car {car_info} has been deleted"}, status=status.HTTP_200_OK)
    
    # Helper methods for pagination and email sending
    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from rest_framework.pagination import PageNumberPagination
            self._paginator = PageNumberPagination()
        return self._paginator
    
    def paginate_queryset(self, queryset):
        return self.paginator.paginate_queryset(queryset, self.request, view=self)
    
    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)
    
    def send_car_approval_email(self, car):
        """Send car approval email to owner"""
        subject = f'Your Car Listing Has Been Approved - {car}'
        html_message = render_to_string('cars/email/car_approved.html', {
            'car': car,
            'owner': car.owner
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = car.owner.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
    
    def send_car_rejection_email(self, car):
        """Send car rejection email to owner"""
        subject = f'Your Car Listing Has Been Rejected - {car}'
        html_message = render_to_string('cars/email/car_rejected.html', {
            'car': car,
            'owner': car.owner
        })
        plain_message = strip_tags(html_message)
        from_email = 'noreply@turo-clone.com'
        to_email = car.owner.email
        
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
