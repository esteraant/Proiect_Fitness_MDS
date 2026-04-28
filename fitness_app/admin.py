from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Subscription, FitnessClass, Booking, Review, InstructorReview, FAQ, ChatMessage, Notification

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Info Instructor (Doar pentru rol INS)', {
            'fields': ('experience_years', 'bio_short', 'profile_picture'),
        }),
    )

admin.site.register(User, CustomUserAdmin)


admin.site.register(Subscription)
admin.site.register(FitnessClass)
admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(InstructorReview)
admin.site.register(FAQ)
admin.site.register(ChatMessage)
admin.site.register(Notification)