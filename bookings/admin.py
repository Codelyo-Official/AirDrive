from django.contrib import admin
from .models import Booking, Review, Report

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

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'reporter', 'reported_user', 'reported_car', 'status', 'created_at')
    list_filter = ('report_type', 'status')
    search_fields = ('reporter__username', 'reported_user__username', 'reason')
    readonly_fields = ('reporter', 'reported_user', 'reported_car', 'report_type', 'reason', 'created_at')
    
    actions = ['mark_as_resolved', 'mark_as_dismissed']
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
    mark_as_resolved.short_description = "Mark selected reports as resolved"
    
    def mark_as_dismissed(self, request, queryset):
        queryset.update(status='dismissed')
    mark_as_dismissed.short_description = "Mark selected reports as dismissed"
