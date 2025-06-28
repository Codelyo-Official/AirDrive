from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Car, CarImage, CarFeature, CarAvailability
from .forms import CarForm, CarImageForm, CarFeatureForm, CarAvailabilityForm
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import CarSerializer,AdminCarUpdateSerializer
from rest_framework.permissions import IsAdminUser
from rest_framework import generics
from rest_framework.permissions import AllowAny

from rest_framework.permissions import BasePermission

class IsAdminOrSupport(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.user_type in ['admin', 'support']
class IsAdminOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.user_type == 'admin'



class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class AdminCarDeleteAPIView(generics.DestroyAPIView):
    queryset = Car.objects.all()
    permission_classes = [IsAdminUser]
    lookup_field = 'id'

class AdminCarUpdateAPIView(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, car_id):
        car = get_object_or_404(Car, id=car_id)
        serializer = AdminCarUpdateSerializer(car, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Car updated successfully.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, car_id):
        car = get_object_or_404(Car, id=car_id)
        car.delete()
        return Response({"message": "Car deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class AdminCarListAPIView(generics.ListAPIView):
    serializer_class = CarSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = Car.objects.all()
        status = self.request.query_params.get('status')
        owner_id = self.request.query_params.get('owner_id')
        search = self.request.query_params.get('search')

        if status:
            qs = qs.filter(status=status)
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
        if search:
            qs = qs.filter(
                models.Q(make__icontains=search) |
                models.Q(model__icontains=search) |
                models.Q(license_plate__icontains=search) |
                models.Q(owner__username__icontains=search)
            )
        return qs

class AvailableCarsAPIView(APIView):
    authentication_classes = []  # Public access
    permission_classes = []      # Public access

    def get(self, request):
        cars = Car.objects.filter(status='available').order_by('-created_at')
        data = []

        for car in cars:
            # Get primary image or first image
            primary_image = car.images.filter(is_primary=True).first() or car.images.first()
            image_url = (
                request.build_absolute_uri(primary_image.image.url)
                if primary_image and primary_image.image
                else None
            )

            # Get availability list
            availability_list = [
                {
                    "start_date": a.start_date.strftime('%Y-%m-%d'),
                    "end_date": a.end_date.strftime('%Y-%m-%d'),
                }
                for a in car.availability.all()
            ]

            # Get features list
            features_list = [f.name for f in car.features.all()]

            data.append({
                "id": car.id,
                "make": car.make,
                "model": car.model,
                "year": car.year,
                "color": car.color,
                "license_plate": car.license_plate,
                "daily_rate": str(car.daily_rate),
                "location": car.location,
                "seats": car.seats,
                'status':car.status,
                "transmission": car.transmission,
                "fuel_type": car.fuel_type,
                "image": image_url,
                "availability": availability_list,
                "features": features_list,
            })

        return Response(data)



import json

class CarCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Convert request.data to a normal dict
        data = request.data.dict()

        # Parse features and availability
        try:
            data['features'] = json.loads(request.data.get('features', '[]'))
        except json.JSONDecodeError:
            return Response({'features': 'Invalid JSON'}, status=400)

        try:
            data['availability'] = json.loads(request.data.get('availability', '[]'))
        except json.JSONDecodeError:
            return Response({'availability': 'Invalid JSON'}, status=400)

        serializer = CarSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            car = serializer.save()

            # Handle image files
            for img in request.FILES.getlist('images'):
                CarImage.objects.create(car=car, image=img)

            return Response({'message': 'Car created successfully'}, status=201)

        return Response(serializer.errors, status=400)
class OwnerCarListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cars = Car.objects.filter(owner=user)
        serializer = CarSerializer(cars, many=True)
        return Response(serializer.data)

@login_required
def car_list(request):
    cars = Car.objects.filter(owner=request.user)
    return render(request, 'cars/car_list.html', {'cars': cars})

@login_required
def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)
    return render(request, 'cars/car_detail.html', {'car': car})

@login_required
def car_create(request):
    if request.method == 'POST':
        form = CarForm(request.POST)
        if form.is_valid():
            car = form.save(commit=False)
            car.owner = request.user
            car.save()
            messages.success(request, 'Car listing created successfully!')
            return redirect('car_detail', pk=car.pk)
    else:
        form = CarForm()
    
    return render(request, 'cars/car_form.html', {'form': form})

@login_required
def car_update(request, pk):
    car = get_object_or_404(Car, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = CarForm(request.POST, instance=car)
        if form.is_valid():
            form.save()
            messages.success(request, 'Car listing updated successfully!')
            return redirect('car_detail', pk=car.pk)
    else:
        form = CarForm(instance=car)
    
    return render(request, 'cars/car_form.html', {'form': form})

@login_required
def car_delete(request, pk):
    car = get_object_or_404(Car, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        car.delete()
        messages.success(request, 'Car listing deleted successfully!')
        return redirect('car_list')
    
    return render(request, 'cars/car_confirm_delete.html', {'car': car})
