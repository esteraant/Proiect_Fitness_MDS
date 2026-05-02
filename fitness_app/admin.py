from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Subscription, FitnessClass, Booking, Review, InstructorReview, FAQ, ChatMessage, Notification

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informații Adiționale', {
            'fields': ('role', 'gender', 'fitness_goal'), 
        }),
        ('Info Instructor (Doar pentru INS)', {
            'fields': ('experience_years', 'bio_short', 'profile_picture'),
        }),
    )
    list_display = ('username', 'email', 'role', 'is_staff')

@admin.register(FitnessClass)
class FitnessClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'instructor', 'start_time', 'is_for_women_only')
    list_filter = ('is_for_women_only', 'type')

admin.site.register(User, CustomUserAdmin)

admin.site.register(Subscription)
admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(InstructorReview)
admin.site.register(FAQ)
admin.site.register(ChatMessage)
admin.site.register(Notification)