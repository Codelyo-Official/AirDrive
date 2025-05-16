from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_verified', 'is_suspended')
    list_filter = ('user_type', 'is_verified', 'is_suspended', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('user_type', 'phone_number', 'profile_picture', 'address', 'is_verified', 'is_suspended')}),
    )

admin.site.register(User, CustomUserAdmin)
