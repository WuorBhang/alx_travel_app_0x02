#from rest_framework import serializers
#from .models import Listing, Booking

#class ListingSerializer(serializers.ModelSerializer):
#    class Meta:
#        model = Listing
#        fields = '__all__'


#class BookingSerializer(serializers.ModelSerializer):
#    class Meta:
#        model = Booking
#        fields = '__all__'


from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Listing, Booking, Review, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'created_at']


class ReviewSerializer(serializers.ModelSerializer):
    comment = serializers.CharField(max_length=500)

    class Meta:
        model = Review
        fields = ['id', 'user_name', 'listing', 'rating', 'comment', 'created_at']



class ListingSerializer(serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "description", "location", "price_per_night",
            "reviews", "average_rating", "created_at"
        ]

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return None
        return round(sum([r.rating for r in reviews]) / len(reviews), 1)



class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'listing', 'user_name', 'user_email', 'check_in', 'check_out', 'created_at']

    def validate(self, data):
        if 'check_in' in data and 'check_out' in data:
            if data['check_in'] > data['check_out']:
                raise ValidationError("Check-out must be after check-in.")
        return data
