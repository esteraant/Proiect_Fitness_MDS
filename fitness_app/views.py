from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import Subscription, Booking, User, FitnessClass
from .forms import CustomUserCreationForm
from datetime import date
from datetime import timedelta
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home') 
        
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required 
def home_view(request):
    subscription = Subscription.objects.filter(user=request.user).first()
    attended_count = Booking.objects.filter(user=request.user, attended=True).count()
    
    context = {
        'subscription': subscription,
        'attended_count': attended_count,
    }
    return render(request, 'home.html', context)

@login_required
def profile_view(request):
    subscription = Subscription.objects.filter(user=request.user).first()
    days_left = 0
    if subscription and subscription.end_date:
        delta = subscription.end_date - date.today()
        days_left = max(0, delta.days)
    context = {
        'subscription': subscription,
        'days_left': days_left,
    }
    return render(request, 'profile.html', context)

@login_required
def freeze_subscription(request):
    subscription = Subscription.objects.filter(user=request.user).first()
    if subscription:
        subscription.is_frozen = not subscription.is_frozen
        subscription.save()
    return redirect('profile')

@login_required
def activate_subscription(request):
    sub, created = Subscription.objects.get_or_create(user=request.user)
    sub.start_date = date.today()
    sub.end_date = date.today() + timedelta(days=30) # Îi dăm 30 de zile
    sub.is_frozen = False
    sub.save()
    return redirect('profile')

# def classes_view(request):
#     fitness_classes = FitnessClass.objects.all()
    
#     for fc in fitness_classes:
#         fc.disponibile = fc.max_capacity - fc.booked_slots
        
#     return render(request, 'classes.html', {'fitness_classes': fitness_classes})

@login_required
def book_class(request, class_id):
    fitness_class = get_object_or_404(FitnessClass, id=class_id)
    
    if fitness_class.available_spots <= 0:
        messages.error(request, "Din păcate, nu mai sunt locuri disponibile la această clasă.")
        return redirect('fitness_classes_list')
    
    # verificam sa nu fie deja inscris
    already_booked = Booking.objects.filter(user=request.user, fitness_class=fitness_class).exists()
    if already_booked:
        messages.warning(request, "Ești deja înscris la această clasă!")
        return redirect('fitness_classes_list')
    
    subscription = Subscription.objects.filter(user=request.user).first()

    if not subscription:
        subscription = Subscription.objects.create(
            user=request.user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            is_frozen=False,
            price=150.00,
            plan='1M'
        )
        messages.info(request, "Un abonament nou a fost activat pentru tine.")
    else:
        if subscription.is_frozen:
            messages.warning(request, "Abonamentul tău este înghețat. Dezgheață-l din profil!")
            return redirect('profile')

    
    Booking.objects.create(
        user=request.user,
        fitness_class=fitness_class
    )
    locuri_ramase = fitness_class.available_spots
    
    messages.success(request, f"Loc rezervat cu succes! (Rămase: {locuri_ramase})")
    return redirect('fitness_classes_list')


def instructors_view(request):
    instructors = User.objects.filter(role='INS')
    return render(request, 'instructors.html', {'instructors': instructors})


def instructor_detail_view(request, instructor_id):
    instructor = get_object_or_404(User, id=instructor_id, role='INS')
    classes = FitnessClass.objects.filter(instructor=instructor)
    
    context = {
        'instructor': instructor,
        'classes': classes
    }
    return render(request, 'instructor_detail.html', context)


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            birth_date = form.cleaned_data.get('birth_date')
            
            if birth_date:
                # Calculăm vârsta exactă
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                # setam automat campul is_child in functie de varsta calculata
                user.is_child = (age < 18)
            user.save()
            login(request, user) # il logam automat dupa inregistrare
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'form': form})


def classes_view(request):
    fitness_classes = FitnessClass.objects.all()
    return render(request, 'classes.html', {'fitness_classes': fitness_classes})

def class_detail_view(request, class_id):
    fitness_class = get_object_or_404(FitnessClass, id=class_id)
    return render(request, 'class_detail.html', {'fitness_class': fitness_class})
    
@staff_member_required
def admin_dashboard_view(request):

    total_users = User.objects.count()
    total_classes = FitnessClass.objects.count()
    recent_bookings = Booking.objects.all().order_by('-id')[:5] 
    # ultimele 5 rezervari

    context = {
        'total_users': total_users,
        'total_classes': total_classes,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'admin_dashboard.html', context)

def index_view(request):
    # daca utilizatorul este deja logat, il trimitem direct la pagina de home
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'index.html')

def logout_view(request):
    logout(request)
    return redirect('login')