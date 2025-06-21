from rest_framework import serializers
from users.models import User,Offer

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'user_type', 'is_verified', 'is_suspended']
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name']  # Allow only status/type updates by default
class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = '__all__'