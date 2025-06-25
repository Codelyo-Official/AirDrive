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
                           AdminReportUpdateAPIView,complete_booking
                           )
from users.views import (AdminUserListAPIView,AdminUserDetailAPIView,AdminRevenueReportAPIView,
AdminOfferListCreateAPIView,AdminOfferUpdateDeleteAPIView,redeem_offer,CreateSupportUserView)

from support.views import (CreateTicketView,MyTicketsView,AllTicketsAdminSupportView,
                           ReplyToTicketView,UpdateTicketStatusView,TicketRepliesView)

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
    path('admin/cars/<int:car_id>/', AdminCarUpdateAPIView.as_view(), name='admin-car-update'),

    #path('admin/cars/<int:id>/', AdminCarUpdateAPIView.as_view()),

    # Booking admin
    path('admin/bookings/', AdminBookingListAPIView.as_view()),
    path('admin/bookings/<int:id>/', AdminBookingUpdateAPIView.as_view()),

    # Reports admin
    path('admin/reports/', AdminReportListAPIView.as_view()),
    path('admin/reports/<int:report_id>/', AdminReportUpdateAPIView.as_view()),

    # Revenue
    path('admin/revenue-report/', AdminRevenueReportAPIView.as_view()),


    path('bookings/<int:booking_id>/complete/', complete_booking, name='complete-booking'),
    path('admin/offers/', AdminOfferListCreateAPIView.as_view(), name='admin-offers'),
    path('admin/offers/<int:id>/', AdminOfferUpdateDeleteAPIView.as_view(), name='admin-offer-detail'),
    path('offers/<int:offer_id>/redeem/', redeem_offer, name='redeem-offer'),

    path("admin/create-support-user/", CreateSupportUserView.as_view(), name="create-support-user"),

    # Tickets
    path("tickets/", CreateTicketView.as_view(), name="create-ticket"),
    path("tickets/user/", MyTicketsView.as_view(), name="my-tickets"),
    path("admin/tickets/", AllTicketsAdminSupportView.as_view(), name="all-tickets"),
    path("tickets/<int:ticket_id>/reply/", ReplyToTicketView.as_view(), name="reply-ticket"),
    path("tickets/<int:pk>/", UpdateTicketStatusView.as_view(), name="update-ticket-status"),

    path('tickets/<int:ticket_id>/replies/', TicketRepliesView.as_view(), name='ticket-replies'),

   ]
