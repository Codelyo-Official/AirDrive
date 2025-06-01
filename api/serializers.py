from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import User
from cars.models import Car, CarImage, CarFeature, CarAvailability
from bookings.models import Booking, Review,Report

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'user_type', 
                  'phone_number', 'profile_picture', 'address', 'is_verified']
        read_only_fields = ['is_verified']

class CarImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarImage
        fields = ['id', 'car', 'image', 'is_primary']

class CarFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarFeature
        fields = ['id', 'car', 'name']

class CarAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CarAvailability
        fields = ['id', 'car', 'start_date', 'end_date']

class CarSerializer(serializers.ModelSerializer):
    images = CarImageSerializer(many=True, read_only=True)
    features = CarFeatureSerializer(many=True, read_only=True)
    availability = CarAvailabilitySerializer(many=True, read_only=True)
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Car
        fields = ['id', 'owner', 'owner_name', 'make', 'model', 'year', 'color', 
                  'license_plate', 'description', 'daily_rate', 'location', 
                  'latitude', 'longitude', 'seats', 'transmission', 'fuel_type', 
                  'status', 'auto_approve_bookings', 'images', 'features', 'availability']
        read_only_fields = ['owner', 'status']
    
    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    car = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = ['id', 'booking', 'user', 'car', 'rating', 'comment', 'created_at']
        read_only_fields = ['user', 'car']
    
    def get_user(self, obj):
        return obj.booking.user.username
    
    def get_car(self, obj):
        return str(obj.booking.car)

class BookingSerializer(serializers.ModelSerializer):
    car_details = CarSerializer(source='car', read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = Booking
        fields = ['id', 'user', 'user_details', 'car', 'car_details', 'start_date', 
                  'end_date', 'total_cost', 'platform_fee', 'owner_payout', 
                  'status', 'created_at', 'updated_at']
        read_only_fields = ['user', 'total_cost', 'platform_fee', 'owner_payout', 'status']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name', 'user_type']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class ReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    reported_user_username = serializers.CharField(source='reported_user.username', read_only=True, allow_null=True)
    reported_car_details = serializers.CharField(source='reported_car.__str__', read_only=True, allow_null=True)
    
    class Meta:
        model = Report
        fields = ['id', 'reporter', 'reporter_username', 'reported_user', 'reported_user_username', 
                 'reported_car', 'reported_car_details', 'report_type', 'reason', 'status', 
                 'admin_notes', 'created_at', 'updated_at']
        read_only_fields = ['reporter', 'reported_user', 'reported_car', 'report_type', 'reason', 'created_at']