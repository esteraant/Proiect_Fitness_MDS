from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from datetime import timedelta

class User(AbstractUser):
    IS_INSTRUCTOR = 'INS'
    IS_CLIENT = 'CLI'
    IS_ADMIN = 'ADM'
    ROLE_CHOICES = [
        (IS_INSTRUCTOR, 'Instructor'),
        (IS_CLIENT, 'Client'),
        (IS_ADMIN, 'Admin'),
    ]
    role = models.CharField(max_length=3, choices=ROLE_CHOICES, default=IS_CLIENT)
    gender = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Feminin')], blank=True)
    is_child = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    referral_count = models.IntegerField(default=0)
    referral_discount_available = models.IntegerField(default=0)
    
    fitness_goal = models.TextField(blank=True) 
    frequency_per_week = models.IntegerField(default=0)

    experience_years = models.PositiveIntegerField(default=0, null=True, blank=True) 
    bio_short = models.CharField(max_length=150, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='instructors/', null=True, blank=True)


# tabelul pentru sali
class Room(models.Model):
    ROOM_TYPES = [
        ('GYM', 'Sala Mare'),
        ('GROUP', 'Sala Grup'),
    ]
    name = models.CharField(max_length=100)     # "Sala Mare", "Sala 1", "Sala 2"
    room_type = models.CharField(max_length=5, choices=ROOM_TYPES)
    capacity = models.PositiveIntegerField() 

    def __str__(self):
        return self.name



# tabelul pentru abonamente, cu sistem de inghetare
class Subscription(models.Model):
    # un user poate avea un singur abonament activ
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    is_frozen = models.BooleanField(default=False)
    freeze_start_date = models.DateField(null=True, blank=True)
    is_first_session_free_used = models.BooleanField(default=False)

    SUBSCRIPTION_TYPES = [
        ('1M', 'Lunar'),
        ('3M', 'Trimestrial'),
        ('6M', 'Semestrial'),
        ('12M', 'Anual'),
    ]
    plan = models.CharField(max_length=3, choices=SUBSCRIPTION_TYPES, default='1M')
    price = models.DecimalField(max_digits=6, decimal_places=2)
    discount_applied = models.DecimalField(max_digits=5, decimal_places=2, default=0)


# tabelul pentru clase, cu limita de persoane si categorii
class FitnessClass(models.Model):
    CLASS_TYPES = [
        ('1TO1', 'Personal Training'),
        ('GRP', 'Grup'),
        ('IND', 'Individual (fără antrenor)'),
    ]
    type = models.CharField(max_length=4, choices=CLASS_TYPES, default='GRP')
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, limit_choices_to={'role': 'INS'})
    name = models.CharField(max_length=100)

    room = models.ForeignKey(
        Room, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    max_capacity = models.PositiveIntegerField()
    is_for_women_only = models.BooleanField(default=False)
    is_for_children = models.BooleanField(default=False)
    start_time = models.DateTimeField()
    price = models.DecimalField(max_digits=6, decimal_places=2, default=30.00)
    duration_minutes = models.PositiveIntegerField(default=60)

    @property
    def available_spots(self):
        return self.max_capacity - self.booking_set.count()
    
    def __str__(self):
        instructor_name = self.instructor.last_name if self.instructor else "Fără antrenor"
        return f"{self.name} - {instructor_name}"
    
    def clean(self):
        super().clean()
        if self.is_for_women_only and self.instructor:
            if self.instructor.gender != 'F':
                raise ValidationError({
                    'instructor': 'O clasă destinată exclusiv femeilor trebuie să aibă un instructor de gen feminin.'
                })



# tabelul pentru rezervari, early bird si check-in
class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fitness_class = models.ForeignKey(FitnessClass, on_delete=models.CASCADE)
    booking_time = models.DateTimeField(auto_now_add=True)
    is_early_bird = models.BooleanField(default=False)
    attended = models.BooleanField(default=False) 
    check_in_time = models.DateTimeField(null=True, blank=True)
    child_name = models.CharField(max_length=100, blank=True, null=True)

    
# tabelul pentru recenzii
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fitness_class = models.ForeignKey(FitnessClass, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'fitness_class')

class InstructorReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', limit_choices_to={'role': 'INS'})
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'instructor')


class FAQ(models.Model):
    question = models.TextField()
    answer = models.TextField()


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    is_from_ai = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    NOTIF_TYPES = [
        ('REMINDER', 'Reminder abonament'),
        ('RECOMMEND', 'Recomandare clasă'),
        ('OCCUPANCY', 'Grad ocupare'),
        ('GENERAL', 'General'),
    ]
    notification_type = models.CharField(max_length=10, choices=NOTIF_TYPES, default='GENERAL')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


# tabelul cu sesiunea
class GymSession(models.Model):
    SESSION_TYPES = [
        ('FREE', 'Liber'),
        ('1TO1', 'Personal Training'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instructor = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pt_sessions',
        limit_choices_to={'role': 'INS'}
    )
    session_type = models.CharField(max_length=4, choices=SESSION_TYPES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    attended = models.BooleanField(default=False, verbose_name="Prezent la ședință")

    def save(self, *args, **kwargs):
        # sesiunea 1-la-1 dureaza 90 de minute, accesul liber 60 de minute
        duration = 90 if self.session_type == '1TO1' else 60
        self.end_time = self.start_time + timedelta(minutes=duration)
        super().save(*args, **kwargs)