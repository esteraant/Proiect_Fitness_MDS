from django.contrib import admin
from .models import User, Subscription, FitnessClass, Booking, Review, InstructorReview, FAQ, ChatMessage, Notification

admin.site.register(User)
admin.site.register(Subscription)
admin.site.register(FitnessClass)
admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(InstructorReview)
admin.site.register(FAQ)
admin.site.register(ChatMessage)
admin.site.register(Notification)