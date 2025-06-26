from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from users.models import User
from cars.models import Car, CarImage, CarFeature, CarAvailability
from bookings.models import Booking, Review
from .serializers import (
    UserSerializer, CarSerializer, BookingSerializer, ReviewSerializer,
    CarImageSerializer, CarFeatureSerializer, CarAvailabilitySerializer,
    RegisterSerializer, LoginSerializer
)
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
import json

class CarCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        print(request)
        serializer = CarSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()  # owner is set in serializer.create()
            return Response({'message': 'Car created successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BecomeCarOwnerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.user_type == 'owner' or user.user_type == 'car-owner':
            return Response({'detail': 'You are already a car owner.'}, status=status.HTTP_400_BAD_REQUEST)

        user.user_type = 'car-owner'  # or 'owner' if you want to keep that terminology
        user.save()

        return Response({'detail': 'You have become a car owner successfully.'}, status=status.HTTP_200_OK)
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
        car_id = self.request.data.get('car')
        start_date = self.request.data.get('start_date')
        end_date = self.request.data.get('end_date')
        
        car = Car.objects.get(id=car_id)
        
        # Calculate number of days
        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        days = (end - start).days + 1
        
        # Calculate costs
        total_cost = car.daily_rate * Decimal(days)
        platform_fee = total_cost * Decimal('0.10')  # 10% platform fee
        owner_payout = total_cost - platform_fee
        
        # Set status based on auto-approve setting
        status = 'approved' if car.auto_approve_bookings else 'pending'
        
        serializer.save(
            user=self.request.user,
            total_cost=total_cost,
            platform_fee=platform_fee,
            owner_payout=owner_payout,
            status=status
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

class CarManagementView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        action = request.data.get('action')
        if not action:
            return Response({'error': 'Action is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'create_car':
            serializer = CarSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(owner=request.user)
                return Response({'message': 'Car created.', 'car': serializer.data}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'add_image':
            car_id = request.data.get('car')
            try:
                car = Car.objects.get(id=car_id)
            except Car.DoesNotExist:
                return Response({'error': 'Car not found.'}, status=status.HTTP_404_NOT_FOUND)
            if car.owner != request.user:
                return Response({'error': 'You can only add images to your own cars.'}, status=status.HTTP_403_FORBIDDEN)
            serializer = CarImageSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({'message': 'Image added.', 'image': serializer.data}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'add_feature':
            car_id = request.data.get('car')
            try:
                car = Car.objects.get(id=car_id)
            except Car.DoesNotExist:
                return Response({'error': 'Car not found.'}, status=status.HTTP_404_NOT_FOUND)
            if car.owner != request.user:
                return Response({'error': 'You can only add features to your own cars.'}, status=status.HTTP_403_FORBIDDEN)
            serializer = CarFeatureSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({'message': 'Feature added.', 'feature': serializer.data}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif action == 'add_availability':
            car_id = request.data.get('car')
            try:
                car = Car.objects.get(id=car_id)
            except Car.DoesNotExist:
                return Response({'error': 'Car not found.'}, status=status.HTTP_404_NOT_FOUND)
            if car.owner != request.user:
                return Response({'error': 'You can only add availability to your own cars.'}, status=status.HTTP_403_FORBIDDEN)
            serializer = CarAvailabilitySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({'message': 'Availability added.', 'availability': serializer.data}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({'error': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

class BecomeOwnerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        # Check if the user is already an owner or car-owner
        if user.user_type == 'owner' or user.user_type == 'car-owner':
            return Response({"detail": "You are already a car owner or owner."},
                            status=status.HTTP_400_BAD_REQUEST)

        user.user_type = 'owner'  # Change user_type to 'owner'
        user.save()
        return Response({"message": "User type updated to owner successfully."},
                        status=status.HTTP_200_OK)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'username': user.username,
            'email': user.email,
            'user_type': user.user_type,
        }

        if user.user_type == 'owner':
            cars = Car.objects.filter(owner=user)
            data['cars'] = CarSerializer(cars, many=True).data
        elif user.user_type == 'admin':
            # Add admin specific data here
            pass

        return Response(data)
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
            })
        
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

class CarFullCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def post(self, request):
        car_data = request.data.copy()
        images = request.FILES.getlist('images')
        features = request.data.getlist('features')
        availability = request.data.getlist('availability')

        # Parse features and availability if sent as JSON strings
        try:
            features = json.loads(features[0]) if features else []
        except Exception:
            features = []
        try:
            availability = json.loads(availability[0]) if availability else []
        except Exception:
            availability = []

        # Remove related fields from car_data
        car_data.pop('images', None)
        car_data.pop('features', None)
        car_data.pop('availability', None)

        car_serializer = CarSerializer(data=car_data)
        if car_serializer.is_valid():
            car = car_serializer.save(owner=request.user)
        else:
            return Response({'errors': car_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Save images
        image_objs = []
        for img in images:
            img_data = {'car': car.id, 'is_primary': False}
            img_serializer = CarImageSerializer(data=img_data, files={'image': img})
            if img_serializer.is_valid():
                image_objs.append(img_serializer.save())
            else:
                transaction.set_rollback(True)
                return Response({'errors': img_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Save features
        feature_objs = []
        for feat in features:
            feat_data = {'car': car.id, 'name': feat.get('name')}
            feat_serializer = CarFeatureSerializer(data=feat_data)
            if feat_serializer.is_valid():
                feature_objs.append(feat_serializer.save())
            else:
                transaction.set_rollback(True)
                return Response({'errors': feat_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Save availability
        avail_objs = []
        for avail in availability:
            avail_data = {
                'car': car.id,
                'start_date': avail.get('start_date'),
                'end_date': avail.get('end_date')
            }
            avail_serializer = CarAvailabilitySerializer(data=avail_data)
            if avail_serializer.is_valid():
                avail_objs.append(avail_serializer.save())
            else:
                transaction.set_rollback(True)
                return Response({'errors': avail_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Car and related data created successfully.',
            'car': CarSerializer(car).data,
            'images': [CarImageSerializer(img).data for img in image_objs],
            'features': [CarFeatureSerializer(f).data for f in feature_objs],
            'availability': [CarAvailabilitySerializer(a).data for a in avail_objs],
        }, status=status.HTTP_201_CREATED)
