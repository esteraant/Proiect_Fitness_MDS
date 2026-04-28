from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import Subscription, Booking, User, FitnessClass

from django.contrib.auth.forms import UserCreationForm
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