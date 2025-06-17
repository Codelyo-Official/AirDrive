from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CarViewSet, BookingViewSet, ReviewViewSet,
    RegisterView, LoginView, LogoutView, ProfileView,
    BecomeOwnerView, DashboardView,
    CarManagementView
)
from cars.views import (CarCreateAPIView,OwnerCarListAPIView
                        ,AvailableCarsAPIView,AdminCarListAPIView,
                        AdminCarUpdateAPIView,AdminCarDeleteAPIView,
                        )
from bookings.views import(OwnerBookingsAPIView,ReportCreateAPIView,
                           BookingApprovalAPIView,BookingCreateAPIView,
                           MyBookingsAPIView,AdminBookingListAPIView,
                           AdminBookingUpdateAPIView,AdminReportListAPIView,
                           AdminReportUpdateAPIView,
                           )
from users.views import (AdminUserListAPIView,AdminUserDetailAPIView,AdminRevenueReportAPIView)
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
    
    path('become-owner/', BecomeOwnerView.as_view(), name='become-owner'),
    # Car-related endpoints
    
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('create/', CarCreateAPIView.as_view(), name='create-car'),
    path('owner-cars/', OwnerCarListAPIView.as_view(), name='owner-cars'),

    path('owner-bookings/', OwnerBookingsAPIView.as_view(), name='owner-bookings'),
    path('booking-approval/<int:booking_id>/', BookingApprovalAPIView.as_view(), name='booking-approval'),
    path('reports/', ReportCreateAPIView.as_view(), name='create-report'),
    path('bookings/', BookingCreateAPIView.as_view(), name='booking-create'),
    path('available-cars/', AvailableCarsAPIView.as_view(), name='available-cars'),
    path('my-bookings/', MyBookingsAPIView.as_view(), name='my-bookings'),

    path('admin/users/', AdminUserListAPIView.as_view(), name='admin-user-list'),
    path('admin/users/<int:user_id>/', AdminUserDetailAPIView.as_view(), name='admin-user-detail'),

    path('admin/cars/', AdminCarListAPIView.as_view()),
    path('admin/cars/<int:id>/', AdminCarUpdateAPIView.as_view()),
    path('admin/cars/<int:id>/delete/', AdminCarDeleteAPIView.as_view()),

    # Booking admin
    path('admin/bookings/', AdminBookingListAPIView.as_view()),
    path('admin/bookings/<int:id>/', AdminBookingUpdateAPIView.as_view()),

    # Reports admin
    path('admin/reports/', AdminReportListAPIView.as_view()),
    path('admin/reports/<int:report_id>/', AdminReportUpdateAPIView.as_view()),

    # Revenue
    path('admin/revenue-report/', AdminRevenueReportAPIView.as_view()),
   ]
