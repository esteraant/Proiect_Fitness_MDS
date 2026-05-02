from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import Subscription, Booking, User, FitnessClass
from .forms import CustomUserCreationForm

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


def instructors_view(request):
    # Filtram utilizatorii care au rolul de instructor
    instructors = User.objects.filter(role='INS')
    return render(request, 'instructors.html', {'instructors': instructors})


def instructor_detail_view(request, instructor_id):
    # Cautam instructorul sau dam eroare 404 daca nu exista
    instructor = get_object_or_404(User, id=instructor_id, role='INS')
    
    # Cautam si clasele pe care le preda acest instructor
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
            user = form.save()
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


