from django.contrib import admin
from .models import Car, CarImage, CarFeature, CarAvailability

class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 1

class CarFeatureInline(admin.TabularInline):
    model = CarFeature
    extra = 1

class CarAvailabilityInline(admin.TabularInline):
    model = CarAvailability
    extra = 1

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'year', 'owner', 'daily_rate', 'status')
    list_filter = ('status', 'make', 'year')
    search_fields = ('make', 'model', 'owner__username')
    inlines = [CarImageInline, CarFeatureInline, CarAvailabilityInline]
    actions = ['approve_cars', 'reject_cars']
    
    def approve_cars(self, request, queryset):
        queryset.update(status='available')
    approve_cars.short_description = "Approve selected cars"
    
    def reject_cars(self, request, queryset):
        queryset.update(status='rejected')
    reject_cars.short_description = "Reject selected cars"
