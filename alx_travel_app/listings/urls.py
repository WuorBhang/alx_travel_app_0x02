# listings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet
from . import views

router = DefaultRouter()
router.register(r'listings', ListingViewSet)
router.register(r'bookings', BookingViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('', views.home_view, name='home'),  # ← this is crucial
    path("initiate-payment/", views.initiate_payment, name="initiate_payment"),
    path("verify-payment/<str:tx_ref>/", views.verify_payment, name="verify_payment"),
    
]
