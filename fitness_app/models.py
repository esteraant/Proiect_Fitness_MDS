from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from datetime import timedelta, date
import uuid

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
    
    fitness_goal = models.TextField(blank=True) 
    frequency_per_week = models.IntegerField(default=0)

    experience_years = models.PositiveIntegerField(default=0, null=True, blank=True) 
    bio_short = models.CharField(max_length=150, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='instructors/', null=True, blank=True)

    referral_code = models.CharField(max_length=15, unique=True, blank=True, null=True)
    discounts_available = models.IntegerField(default=0) # cate reduceri de 10% are
    first_free_session_used = models.BooleanField(default=False)

    # generam codul automat cand se creeaza contul
    def save(self, *args, **kwargs):
        if not self.referral_code:
            # va genera un cod de tipul ALGO-A1B2C3
            unique_id = str(uuid.uuid4())[:6].upper()
            self.referral_code = f"ALGO-{unique_id}"
        super().save(*args, **kwargs)


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
    PLAN_TYPES = [
        ('1M', 'Lunar'),
        ('3M', 'Trimestrial'),
        ('6M', 'Semestrial'),
        ('12M', 'Anual'),
    ]
    # durata in zile + pret de baza pentru fiecare plan (o singura sursa de adevar)
    PLAN_CONFIG = {
        '1M':  {'days': 30,  'price': 150.00,  'label': 'Lunar'},
        '3M':  {'days': 90,  'price': 405.00,  'label': 'Trimestrial'}, # 10% reducere
        '6M':  {'days': 180, 'price': 750.00,  'label': 'Semestrial'}, # economisesti o luna
        '12M': {'days': 365, 'price': 1400.00, 'label': 'Anual'},
    }
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    is_frozen = models.BooleanField(default=False)
    freeze_start_date = models.DateField(null=True, blank=True)

    plan = models.CharField(max_length=3, choices=PLAN_TYPES, default='1M')
    price = models.DecimalField(max_digits=7, decimal_places=2)
    discount_applied = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def is_active(self):
        return self.end_date >= date.today() and not self.is_frozen
    
    def __str__(self):
        return f"{self.user.username} - {self.get_plan_display()}"
 
 
    # pachet de sedinte legat de un instructor (1to1) sau de o clasa specifica (grup)
class SessionPackage(models.Model):
    PACKAGE_TYPES = [
        ('1TO1', 'Personal Training'),
        ('GRP', 'Clasa de grup'),
    ]
    DURATION_TYPES = [
        ('1M', 'Lunar'),
        ('3M', 'Trimestrial'),
    ]
    # cate sedinte include fiecare combinatie + pret
    PACKAGE_CONFIG = {
            ('1TO1', '1M'): {'sessions': 10, 'days': 30,  'price': 800.00},
            ('1TO1', '3M'): {'sessions': 30, 'days': 90,  'price': 2160.00},  # ~10% reducere
            ('GRP', '1M'):  {'sessions': 8,  'days': 30,  'price': 280.00},
            ('GRP', '3M'):  {'sessions': 24, 'days': 90,  'price': 756.00},   # ~10% reducere
        }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='packages')
    package_type = models.CharField(max_length=4, choices=PACKAGE_TYPES)
    duration = models.CharField(max_length=3, choices=DURATION_TYPES)

    # doar pentru 1TO1: instructorul ales
    instructor = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='pt_packages', limit_choices_to={'role': 'INS'}
        )
    # doar pentru GRP: clasa specifica (legat de nume, ca sa prinda toate sesiunile recurente)
    fitness_class_name = models.CharField(max_length=100, null=True, blank=True)

    total_sessions = models.PositiveIntegerField()
    sessions_used = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()

    @property
    def sessions_left(self):
        return self.total_sessions - self.sessions_used

    @property
    def is_active(self):
        return self.end_date >= date.today() and self.sessions_left > 0

    def clean(self):
        super().clean()
        if self.package_type == '1TO1' and not self.instructor:
            raise ValidationError("Un pachet 1-la-1 trebuie sa aiba un instructor ales.")
        if self.package_type == 'GRP' and not self.fitness_class_name:
            raise ValidationError("Un pachet de grup trebuie legat de o clasa specifica.")

    def __str__(self):
        target = self.instructor.last_name if self.instructor else self.fitness_class_name
        return f"{self.user.username} - {self.get_package_type_display()} ({target})"
        
# istoric plati - simplu, fara gateway real
class Payment(models.Model):
    PAYMENT_KINDS = [
        ('SUB', 'Abonament'),
        ('PKG', 'Pachet sedinte'),
        ('SINGLE', 'Sesiune singulara'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    kind = models.CharField(max_length=6, choices=PAYMENT_KINDS)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
 
    # legaturi optionale catre ce s-a platit
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    session_package = models.ForeignKey(SessionPackage, on_delete=models.SET_NULL, null=True, blank=True)
 
    def __str__(self):
        return f"{self.user.username} - {self.amount} RON ({self.get_kind_display()})"
 
 
# tabelul pentru clase
class FitnessClass(models.Model):
    CLASS_TYPES = [
        ('1TO1', 'Personal Training'),
        ('GRP', 'Grup'),
        ('IND', 'Individual (fără antrenor)'),
    ]
    type = models.CharField(max_length=4, choices=CLASS_TYPES, default='GRP')
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, limit_choices_to={'role': 'INS'})
    name = models.CharField(max_length=100)
 
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
 
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
 
# tabelul pentru rezervari
class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fitness_class = models.ForeignKey(FitnessClass, on_delete=models.CASCADE)
    booking_time = models.DateTimeField(auto_now_add=True)
    is_early_bird = models.BooleanField(default=False)
    attended = models.BooleanField(default=False) 
    check_in_time = models.DateTimeField(null=True, blank=True)
    child_name = models.CharField(max_length=100, blank=True, null=True)
    # daca rezervarea a fost acoperita de un pachet, il legam ca sa stim ce sa decrementam
    paid_by_package = models.ForeignKey(SessionPackage, on_delete=models.SET_NULL, null=True, blank=True)

    
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
    is_free_session = models.BooleanField(default=False)  # marcheaza sesiunea gratuita de bun venit
    paid_by_package = models.ForeignKey(SessionPackage, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        duration = 90 
        self.end_time = self.start_time + timedelta(minutes=duration)
        super().save(*args, **kwargs)
