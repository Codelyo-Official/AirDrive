from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from users.models import User,Offer
from .serializers import AdminUserSerializer,OfferSerializer
from rest_framework.permissions import IsAdminUser
from bookings.models import Booking
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated








from django.db.models import Sum
from django.utils.dateparse import parse_date
from rest_framework.views import APIView
from rest_framework import generics


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeem_offer(request, offer_id):
    user = request.user
    try:
        offer = Offer.objects.get(id=offer_id, is_active=True)
    except Offer.DoesNotExist:
        return Response({"error": "Offer not found or inactive."}, status=404)

    if user.points < offer.points_required:
        return Response({"error": "Not enough points to redeem this offer."}, status=400)

    user.points -= offer.points_required
    user.save()

    Redemption.objects.create(user=user, offer=offer)

    return Response({
        "message": f"Successfully redeemed {offer.title}.",
        "remaining_points": user.points
    })


class AdminOfferListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer

class AdminOfferUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    lookup_field = 'id'


class AdminRevenueReportAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        report_type = request.GET.get('type', 'monthly')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        bookings = Booking.objects.filter(status='completed')

        if start_date:
            bookings = bookings.filter(start_date__gte=parse_date(start_date))
        if end_date:
            bookings = bookings.filter(end_date__lte=parse_date(end_date))

        total_earned = bookings.aggregate(Sum('platform_fee'))['platform_fee__sum'] or 0

        return Response({
            "report_type": report_type,
            "total_platform_revenue": float(total_earned),
            "start_date": start_date,
            "end_date": end_date,
            "total_bookings": bookings.count()
        })


class AdminUserListAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = User.objects.all()
        
        # Filters
        user_type = request.query_params.get('user_type')
        is_verified = request.query_params.get('is_verified')
        is_suspended = request.query_params.get('is_suspended')
        search = request.query_params.get('search')
        
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        if is_verified in ['true', 'false']:
            queryset = queryset.filter(is_verified=(is_verified.lower() == 'true'))
        if is_suspended in ['true', 'false']:
            queryset = queryset.filter(is_suspended=(is_suspended.lower() == 'true'))
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | 
                Q(email__icontains=search) | 
                Q(first_name__icontains=search) | 
                Q(last_name__icontains=search)
            )
        
        serializer = AdminUserSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminUserDetailAPIView(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User updated successfully', 'user': serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        user.delete()
        return Response({'message': 'User deleted successfully'}, status=status.HTTP_204_NO_CONTENT)



def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'users/profile.html', {'form': form})
