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
        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            if 'data:' in data and ';base64,' in data:
                header, data = data.split(';base64,')
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail('invalid_image')

            file_name = str(uuid.uuid4())[:12]  # Random name
            file_extension = "jpg"
            complete_file_name = f"{file_name}.{file_extension}"
            return ContentFile(decoded_file, name=complete_file_name)

        return super().to_internal_value(data)



class CarImageSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = CarImage
        fields = ['image', 'is_primary']

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
    features = CarFeatureSerializer(many=True, read_only=True)
    availability = CarAvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = Car
        fields = [
            'id', 'make', 'model', 'year', 'color', 'license_plate', 'description',
            'daily_rate', 'location', 'latitude', 'longitude', 'seats', 'transmission',
            'fuel_type', 'status', 'auto_approve_bookings', 'images', 'features', 'availability'
        ]

    def create(self, validated_data):
        images_data = validated_data.pop('images')
        features_data = validated_data.pop('features')
        availability_data = validated_data.pop('availability')
        
        car = Car.objects.create(**validated_data)

        for image in images_data:
            CarImage.objects.create(car=car, **image)

        for feature in features_data:
            CarFeature.objects.create(car=car, **feature)

        for availability in availability_data:
            CarAvailability.objects.create(car=car, **availability)

        return car
