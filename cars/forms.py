from django import forms
from .models import Car, CarImage, CarFeature, CarAvailability

class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ['make', 'model', 'year', 'color', 'license_plate', 'description', 
                  'daily_rate', 'location', 'seats', 'transmission', 'fuel_type', 
                  'auto_approve_bookings']

class CarImageForm(forms.ModelForm):
    class Meta:
        model = CarImage
        fields = ['image', 'is_primary']

class CarFeatureForm(forms.ModelForm):
    class Meta:
        model = CarFeature
        fields = ['name']

class CarAvailabilityForm(forms.ModelForm):
    class Meta:
        model = CarAvailability
        fields = ['start_date', 'end_date']