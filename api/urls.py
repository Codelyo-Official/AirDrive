from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CarViewSet, BookingViewSet, ReviewViewSet,
    RegisterView, LoginView, LogoutView, ProfileView,
    CarImageView, CarFeatureView, CarAvailabilityView, DashboardView,
    BecomeOwnerView, CarCreateView, OwnerCarsView, OwnerBookingsView, BookingApprovalView,
    # Add new imports
    AdminBookingManagementView, AdminRevenueReportView,
    AdminUserManagementView, AdminCarApprovalView,
    ReportCreateView, AdminReportManagementView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'cars', CarViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'reviews', ReviewViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Remove or replace this line:
    # path('auth/', include('rest_framework.authtoken.urls')),
    
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Car-related endpoints
    path('car-images/', CarImageView.as_view(), name='car-images'),
    path('car-features/', CarFeatureView.as_view(), name='car-features'),
    
    # Car owner endpoints
    path('become-owner/', BecomeOwnerView.as_view(), name='become-owner'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('car-availability/', CarAvailabilityView.as_view(), name='car-availability'),
    path('car-create/', CarCreateView.as_view(), name='car-create'),
    path('owner-cars/', OwnerCarsView.as_view(), name='owner-cars'),
    path('owner-bookings/', OwnerBookingsView.as_view(), name='owner-bookings'),
    path('booking-approval/<int:booking_id>/', BookingApprovalView.as_view(), name='booking-approval'),
    
    # Password reset endpoints
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), 
         name='password_reset_complete'),
    
    # Admin endpoints
    path('admin/bookings/', AdminBookingManagementView.as_view(), name='admin-bookings'),
    path('admin/bookings/<int:booking_id>/', AdminBookingManagementView.as_view(), name='admin-booking-detail'),
    path('admin/revenue-report/', AdminRevenueReportView.as_view(), name='admin-revenue-report'),
    path('admin/users/', AdminUserManagementView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/', AdminUserManagementView.as_view(), name='admin-user-detail'),
    path('admin/cars/', AdminCarApprovalView.as_view(), name='admin-cars'),
    path('admin/cars/<int:car_id>/', AdminCarApprovalView.as_view(), name='admin-car-detail'),
    path('admin/reports/', AdminReportManagementView.as_view(), name='admin-reports'),
    path('admin/reports/<int:report_id>/', AdminReportManagementView.as_view(), name='admin-report-detail'),
    
    # User reporting
    path('reports/', ReportCreateView.as_view(), name='create-report'),
]