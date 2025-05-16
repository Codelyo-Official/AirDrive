from django.contrib import admin
from .models import Booking, Review

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'car', 'start_date', 'end_date', 'total_cost', 'status')
    list_filter = ('status', 'start_date')
    search_fields = ('user__username', 'car__make', 'car__model')
    inlines = [ReviewInline]
    actions = ['approve_bookings', 'reject_bookings', 'mark_as_completed']
    
    def approve_bookings(self, request, queryset):
        queryset.update(status='approved')
    approve_bookings.short_description = "Approve selected bookings"
    
    def reject_bookings(self, request, queryset):
        queryset.update(status='rejected')
    reject_bookings.short_description = "Reject selected bookings"
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
    mark_as_completed.short_description = "Mark selected bookings as completed"
