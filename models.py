from django.db import models
from django.contrib.auth.models import AbstractUser

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
    fitness_goal = models.TextField(blank=True) 
    frequency_per_week = models.IntegerField(default=0)

# pentru instructori doar
    experience_years = models.PositiveIntegerField(default=0, null=True, blank=True) 
    bio_short = models.CharField(max_length=150, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='instructors/', null=True, blank=True)

# Tabelul pentru abonamente, cu sistem de inghetare
class Subscription(models.Model):
    # un user poate avea un singur abonament activ
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    is_frozen = models.BooleanField(default=False)
    freeze_start_date = models.DateField(null=True, blank=True)
    is_first_session_free_used = models.BooleanField(default=False)

# Tabelul pentru clase, cu limita de persoane si categorii
class FitnessClass(models.Model):
    CLASS_TYPES = [
        ('1TO1', 'Personal Training'),
        ('GRP', 'Grup'),
        ('IND', 'Individual (fără antrenor)'),
    ]
    type = models.CharField(max_length=4, choices=CLASS_TYPES, default='GRP')
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, limit_choices_to={'role': 'INS'})
    name = models.CharField(max_length=100)
    # ne asiguram ca putem alege doar instructorii cand cream o clasa
    max_capacity = models.PositiveIntegerField()
    is_for_women_only = models.BooleanField(default=False)
    is_for_children = models.BooleanField(default=False)
    start_time = models.DateTimeField()
    
    def __str__(self):
        instructor_name = self.instructor.last_name if self.instructor else "Fără antrenor"
        return f"{self.name} - {instructor_name}"

# Tabelul pentru rezervari, Early Bird si Check-in
class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fitness_class = models.ForeignKey(FitnessClass, on_delete=models.CASCADE)
    booking_time = models.DateTimeField(auto_now_add=True)
    is_early_bird = models.BooleanField(default=False)
    attended = models.BooleanField(default=False) 

# Tabelul pentru recenzii
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fitness_class = models.ForeignKey(FitnessClass, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()