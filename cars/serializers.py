# cars/serializers.py
from rest_framework import serializers
from .models import Car, CarImage, CarFeature, CarAvailability

import base64
import six
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers
from .models import CarImage

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            file_name = f"{uuid.uuid4()}.{ext}"
            data = ContentFile(base64.b64decode(imgstr), name=file_name)
        return super().to_internal_value(data)



class CarImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()  # for file uploads

    class Meta:
        model = CarImage
        fields = ['id', 'image', 'is_primary']

class CarFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarFeature
        fields = ['name']

class CarAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CarAvailability
        fields = ['start_date', 'end_date']


class CarSerializer(serializers.ModelSerializer):
    images = CarImageSerializer(many=True, read_only=True)

    # Remove images from here because handled separately
    features = CarFeatureSerializer(many=True)
    availability = CarAvailabilitySerializer(many=True)

    class Meta:
        model = Car
        fields = [
            'id', 'make', 'model', 'year', 'color', 'license_plate', 'description',
            'daily_rate', 'location', 'latitude', 'longitude', 'seats', 'transmission',
            'fuel_type', 'status', 'auto_approve_bookings', 'features', 'availability',  # derived primary image URL
            'images',
        ]
    def get_image(self, obj):
        request = self.context.get('request')
        primary = obj.images.filter(is_primary=True).first() or obj.images.first()
        return request.build_absolute_uri(primary.image.url) if primary else None
    def create(self, validated_data):
        features_data = validated_data.pop('features', [])
        availability_data = validated_data.pop('availability', [])

        owner = self.context['request'].user
        car = Car.objects.create(owner=owner, **validated_data)

        for feature_data in features_data:
            CarFeature.objects.create(car=car, **feature_data)

        for availability_item in availability_data:
            CarAvailability.objects.create(car=car, **availability_item)

        return car

class AdminCarUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = '__all__'  # or list explicitly