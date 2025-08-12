# listings/views.py


import requests
import json

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from decouple import config

from .models import Booking, Listing, Review, Payment
from .serializers import BookingSerializer, ListingSerializer, ReviewSerializer


class ListingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows listings to be viewed or edited.
    """

    queryset = Listing.objects.all().order_by("-created_at")
    serializer_class = ListingSerializer
    lookup_field = "id"

    def get_queryset(self):
        """
        Optionally filter listings by various parameters.
        """
        queryset = super().get_queryset()
        # Example of filtering by query parameters
        max_price = self.request.query_params.get("max_price")
        if max_price is not None:
            queryset = queryset.filter(price_per_night__lte=max_price)
        return queryset

    @action(detail=True, methods=["get"])
    def reviews(self, request, id=None):
        """
        Retrieve all reviews for a specific listing.
        """
        listing = self.get_object()
        reviews = Review.objects.filter(listing=listing)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows bookings to be viewed or edited.
    """

    serializer_class = BookingSerializer
    lookup_field = "id"

    def get_queryset(self):
        """
        Optionally filter bookings by listing_id or user.
        """
        queryset = Booking.objects.all().order_by("-created_at")
        listing_id = self.request.GET.get("listing_id")
        user_id = self.request.GET.get("user_id")

        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def perform_create(self, serializer):
        """
        Automatically set the user to the current user when creating a booking.
        """
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to prevent deletion of confirmed bookings.
        """
        instance = self.get_object()
        if instance.status == "confirmed":
            return Response(
                {"detail": "Cannot delete a confirmed booking."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Handle PATCH requests for updating a booking.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Save the updated instance
        self.perform_update(serializer)

        # Refresh the instance from the database to get the updated status
        instance.refresh_from_db()

        return Response(serializer.data)


CHAPA_API_URL = "https://api.chapa.co/v1/transaction/initialize"
CHAPA_SECRET_KEY = config('CHAPA_SECRET_KEY')


@api_view(['POST'])
def initiate_payment(request):
    booking_id = request.data.get('booking_id')
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

    # Create or get existing payment
    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            'amount': booking.total_price,
        }
    )

    if payment.status == 'Success':
        return Response({"message": "Payment already completed"}, status=status.HTTP_400_BAD_REQUEST)

    # Payload for Chapa
    payload = {
        "amount": str(payment.amount),
        "currency": "ETB",
        "email": booking.user.email,
        "first_name": booking.user.first_name,
        "last_name": booking.user.last_name,
        "tx_ref": f"booking-{booking.id}-{payment.id}",
        "callback_url": "https://yourdomain.com/payment/callback/",
        "return_url": "https://yourdomain.com/payment/verify/",
        "customization": {
            "title": "Travel Booking Payment",
            "description": f"Payment for booking {booking.id}"
        }
    }

    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(CHAPA_API_URL, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success":
            # Save transaction ID
            payment.transaction_id = data["data"]["tx_ref"]
            payment.status = "Pending"
            payment.save()

            return Response({
                "checkout_url": data["data"]["checkout_url"],
                "tx_ref": data["data"]["tx_ref"],
                "message": "Payment initiated"
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": data.get("message", "Initialization failed")}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"error": "Network error with Chapa"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def verify_payment(request):
    tx_ref = request.GET.get("tx_ref")

    if not tx_ref:
        return Response({"error": "tx_ref is required"}, status=status.HTTP_400_BAD_REQUEST)

    verification_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
    }

    response = requests.get(verification_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success":
            try:
                payment = Payment.objects.get(transaction_id=tx_ref)
                payment.status = "Success"
                payment.save()

                # TODO: Trigger email via Celery (bonus)
                return Response({"status": "Payment verified and updated"}, status=status.HTTP_200_OK)
            except Payment.DoesNotExist:
                return Response({"error": "Transaction not found in system"}, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                payment = Payment.objects.get(transaction_id=tx_ref)
                payment.status = "Failed"
                payment.save()
            except Payment.DoesNotExist:
                pass
            return Response({"status": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"error": "Verification failed due to external error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)