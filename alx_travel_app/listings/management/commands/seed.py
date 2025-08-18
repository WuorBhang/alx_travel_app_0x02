from django.core.management.base import BaseCommand
from listings.models import Listing
import random

class Command(BaseCommand):
    help = 'Seed the database with sample listings'

    def handle(self, *args, **kwargs):
        sample_data = [
            {
                "title": "Ocean View Apartment",
                "description": "Beautiful apartment with a view of the ocean.",
                "location": "Lagos",
                "price_per_night": 150.00
            },
            {
                "title": "Mountain Cabin",
                "description": "Cozy cabin near the mountainside.",
                "location": "Jos",
                "price_per_night": 90.00
            },
            {
                "title": "City Center Studio",
                "description": "Studio apartment in the heart of the city.",
                "location": "Abuja",
                "price_per_night": 120.00
            }
        ]

        for item in sample_data:
            listing, created = Listing.objects.get_or_create(
                title=item['title'],
                defaults={
                    "description": item['description'],
                    "location": item['location'],
                    "price_per_night": item['price_per_night'],
                    "available": True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {listing.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"Already exists: {listing.title}"))
