from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CarViewSet, BookingViewSet, ReviewViewSet,
    RegisterView, LoginView, LogoutView, ProfileView,
    CarImageView, CarFeatureView
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
]