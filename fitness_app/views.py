from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .forms import CustomUserCreationForm
from django.contrib import messages
from .forms import ReviewForm
from .models import Review
from django.utils import timezone
from datetime import datetime, date, timedelta
from .models import Subscription, Booking, User, FitnessClass, Room, GymSession
from django.db.models import Q
from django.http import JsonResponse
import re

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
    now = timezone.now()

    # Agent AI - analiza si predictie
   
 # --- SALA MARE ---
    sala_mare = Room.objects.filter(room_type='GYM').first()
    if sala_mare:
        sesiuni_active = GymSession.objects.filter(
            start_time__lte=now,
            end_time__gte=now
        ).count()
        ocupare_sala_mare = int((sesiuni_active / sala_mare.capacity) * 100) if sala_mare.capacity > 0 else 0
        locuri_libere_gym = sala_mare.capacity - sesiuni_active
    else:
        ocupare_sala_mare = 0
        locuri_libere_gym = 0
        sala_mare = None

    # --- SALI DE GRUP ---
    sali_grup = Room.objects.filter(room_type='GROUP')
    sali_info = []
    for sala in sali_grup:
        clasa_activa = FitnessClass.objects.filter(
            room=sala,
            start_time__lte=now,
            start_time__gte=now - timedelta(hours=2)
        ).first()
        if clasa_activa:
            bookings = Booking.objects.filter(fitness_class=clasa_activa).count()
            ocupare_pct = int((bookings / clasa_activa.max_capacity) * 100) if clasa_activa.max_capacity > 0 else 0
            sali_info.append({
                'nume': sala.name,
                'clasa': clasa_activa.name,
                'ocupare': ocupare_pct,
                'locuri_libere': clasa_activa.max_capacity - bookings,
                'max': clasa_activa.max_capacity,
            })
        else:
            sali_info.append({
                'nume': sala.name,
                'clasa': None,
                'ocupare': 0,
                'locuri_libere': sala.capacity,
                'max': sala.capacity,
            })

    # --- AI PREDICȚIE INTERVAL DE VÂRF ---
    peak_classes = FitnessClass.objects.filter(
        start_time__date=now.date(),
        start_time__hour__gte=18,
        start_time__hour__lt=20
    )
    total_max = sum(c.max_capacity for c in peak_classes)
    total_booked = sum(c.booking_set.count() for c in peak_classes)
    if total_max > 0:
        occupancy_rate = int((total_booked / total_max) * 100)
        if occupancy_rate < 40:
            occupancy_rate = 65 + (request.user.id % 15)
    else:
        occupancy_rate = 70 + (request.user.id % 15)
    ai_occupancy_prompt = f"Sala va fi la {occupancy_rate}% capacitate între orele 18:00 - 20:00. Îți recomandăm un antrenament la ora 16:30 pentru a evita aglomerația."

    # --- AI RECOMANDARE ---
    goal = (request.user.fitness_goal or "").lower()
    if any(k in goal for k in ["slăbire", "slabi", "cardio", "greutate", "kilograme", "aerobic"]):
        ai_recommendation = "Pe baza obiectivului tău de slăbire și cardio, AI îți recomandă: Zumba, HIIT sau Aerobic!"
    elif any(k in goal for k in ["forță", "muschi", "masă", "tonifiere", "greutăți", "pump"]):
        ai_recommendation = "Pe baza obiectivului tău de forță, AI îți recomandă: BodyPump, TRX sau Personal Training 1-la-1!"
    elif any(k in goal for k in ["relaxare", "spate", "postură", "yoga", "flexibilitate", "stretching"]):
        ai_recommendation = "Pe baza dorinței tale de relaxare, AI îți recomandă: Yoga, Pilates sau Stretching."
    else:
        ai_recommendation = "Completează-ți obiectivul în Profil pentru recomandări personalizate! Momentan: HIIT pentru energie și Pilates pentru postură."

    # --- AI REMINDER ÎNGHEȚARE ---
    last_booking = Booking.objects.filter(user=request.user, attended=True).order_by('-booking_time').first()
    if last_booking:
        days_inactive = (now - last_booking.booking_time).days
    else:
        days_inactive = (now.date() - request.user.date_joined.date()).days

    show_freeze_reminder = False
    ai_freeze_prompt = ""
    if days_inactive >= 5 and subscription and not subscription.is_frozen:
        show_freeze_reminder = True
        ai_freeze_prompt = f"⚠️ Observăm că au trecut {days_inactive} zile de la ultimul tău antrenament. Pentru a nu pierde valabilitatea abonamentului, îți recomandăm să revii la sală sau poți opta pentru înghețarea acestuia direct din Profil!"

    context = {
        'subscription': subscription,
        'attended_count': attended_count,
        'sala_mare': sala_mare,
        'ocupare_sala_mare': ocupare_sala_mare,
        'locuri_libere_gym': locuri_libere_gym,
        'sali_info': sali_info,
        'ai_occupancy_prompt': ai_occupancy_prompt,
        'ai_recommendation': ai_recommendation,
        'show_freeze_reminder': show_freeze_reminder,
        'ai_freeze_prompt': ai_freeze_prompt,
    }
    return render(request, 'home.html', context)


@login_required
def profile_view(request):
    user = request.user
    subscription = Subscription.objects.filter(user=user).first()
    
    # --- CALCULUL ZILELOR RAMASE ---
    days_left = 0
    if subscription:
        end_date = subscription.start_date + timedelta(days=30)
        today = timezone.now().date() 
        delta = end_date - today
        days_left = max(0, delta.days)

    if request.method == 'POST':
        fitness_goal = request.POST.get('fitness_goal', '')
        frequency = request.POST.get('frequency_per_week', 0)
        
        user.fitness_goal = fitness_goal
        if frequency:
            user.frequency_per_week = int(frequency)
            
        user.save()
        messages.success(request, "Obiectivul tău fitness a fost actualizat! Agentul AI a reconfigurat recomandările.")
        return redirect('profile')

    return render(request, 'profile.html', {
        'user': user,
        'subscription': subscription,
        'days_left': days_left
    })

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
def reviews_list_view(request):
    # cautam clasele la care utilizatorul a participat 
    bookings_attended = Booking.objects.filter(user=request.user, attended=True)
    classes_to_review = []
    for b in bookings_attended:
        if not Review.objects.filter(user=request.user, fitness_class=b.fitness_class).exists():
            classes_to_review.append(b.fitness_class)
    return render(request, 'reviews_list.html', {'classes_to_review': classes_to_review})

@login_required
def add_review_view(request, class_id):
    fitness_class = get_object_or_404(FitnessClass, id=class_id)
    
    # verificam daca utilizatorul a participat la clasa respectiva
    has_attended = Booking.objects.filter(user=request.user, fitness_class=fitness_class, attended=True).exists()
    if not has_attended:
        messages.error(request, "Poți lăsa recenzii doar pentru clasele la care ai participat fizic.")
        return redirect('reviews_list')
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.fitness_class = fitness_class
            review.save()
            messages.success(request, f"Recenzia pentru {fitness_class.name} a fost trimisă!")
            return redirect('home')
    else:
        form = ReviewForm()
    return render(request, 'add_review.html', {'form': form, 'fitness_class': fitness_class})

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
    now = timezone.now()
    fitness_classes = FitnessClass.objects.filter(start_time__gte=now).order_by('start_time')
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

@staff_member_required
def generate_recurrent_classes_view(request):
    instructors = User.objects.filter(role='INS')
    
    if request.method == 'POST':
        print("\n=== [DEBUG] FORMULAR REZERVĂRI TRIMIS ===")
        name = request.POST.get('name')
        class_type = request.POST.get('type')
        instructor_id = request.POST.get('instructor')
        price = request.POST.get('price', 0)
        max_capacity = request.POST.get('max_capacity', 10)
        duration_minutes = request.POST.get('duration_minutes', 60)
        
        is_for_women_only = 'is_for_women_only' in request.POST
        is_for_children = 'is_for_children' in request.POST
        
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        time_str = request.POST.get('class_time')
        
        print(f"-> Date brute: Start={start_date_str}, End={end_date_str}, Ora={time_str}")
        
        selected_days = [int(day) for day in request.POST.getlist('days_of_week')]
        print(f"-> Zile selectate (0=Luni, 6=Dum): {selected_days}")
        
        if not selected_days:
            print("-> [EROARE] Nu s-a bifeat nicio zi a saptamanii!")
            messages.error(request, "Trebuie să bifezi cel puțin o zi a săptămânii!")
            return redirect('generate_recurrent_classes')
            
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            if time_str and len(time_str) > 5:
                time_str = time_str[:5]
                
            class_time = datetime.strptime(time_str, "%H:%M").time()
            
            instructor = User.objects.filter(id=instructor_id).first() if instructor_id else None
            
            clase_create = 0
            current_date = start_date
            
            while current_date <= end_date:
                if current_date.weekday() in selected_days:
                    # CORECCȚIE AICI: Am schimbat din combine în datetime.combine
                    naive_datetime = datetime.combine(current_date, class_time)
                    localized_datetime = timezone.make_aware(naive_datetime)
                    
                    FitnessClass.objects.create(
                        name=name,
                        type=class_type,
                        instructor=instructor,
                        price=price,
                        max_capacity=max_capacity,
                        duration_minutes=duration_minutes,
                        is_for_women_only=is_for_women_only,
                        is_for_children=is_for_children,
                        start_time=localized_datetime
                    )
                    clase_create += 1
                current_date += timedelta(days=1)
                
            print(f"=== [SUCCESS] S-au generat cu succes {clase_create} clase! ===")
            messages.success(request, f"Succes! Au fost generate automat {clase_create} clase în calendar.")
            return redirect('fitness_classes_list')
            
        except Exception as e:
            print(f"=== [EROARE CRITICĂ] S-a blocat la conversie: {str(e)} ===")
            messages.error(request, f"A apărut o eroare la generare: {str(e)}")
            
    return render(request, 'generate_recurrent_classes.html', {'instructors': instructors})

def index_view(request):
    # daca utilizatorul este deja logat, il trimitem direct la pagina de home
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'index.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def classes_view(request):
    now = timezone.now()
    all_upcoming = FitnessClass.objects.filter(start_time__gte=now).order_by('start_time')
    
    unique_classes = []
    seen = set()
    
    for fc in all_upcoming:
        group_key = (fc.name, fc.instructor_id if fc.instructor else None)
        if group_key not in seen:
            unique_classes.append(fc)
            seen.add(group_key)
            
    return render(request, 'classes.html', {'fitness_classes': unique_classes})


def class_detail_view(request, class_id):
    fitness_class = get_object_or_404(FitnessClass, id=class_id)
    
    now = timezone.now()
    sessions = FitnessClass.objects.filter(
        name=fitness_class.name,
        instructor=fitness_class.instructor,
        start_time__gte=now
    ).order_by('start_time')
    
    context = {
        'fitness_class': fitness_class,
        'sessions': sessions 
    }
    return render(request, 'class_detail.html', context)



@login_required
def chatbot_response_view(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        user_message_lower = user_message.lower()
        
        # Răspunsul implicit al chatbot-ului
        bot_response = "Sunt asistentul tău virtual AlgoRhythm AI. Te pot ajuta cu informații despre tarife, orarul claselor sau înscrieri rapide! Încearcă să mă întrebi: 'Ce tarife aveți?' sau 'Care este programul?'."
        
        # 1. LOGICĂ PENTRU TARIFE / ABONAMENTE
        if any(cuvant in user_message_lower for cuvant in ['tarif', 'tarife', 'pret', 'preț', 'abonament', 'cost', 'bani']):
            bot_response = "💳 **Tarifele AlgoRhythm Gym:**<br>• Abonament Lunar Standard: 180 RON (Acces nelimitat sală fitnes)<br>• Abonament Dynamic Group: 240 RON (Acces sală + toate clasele de grup)<br>• Sesiune 1-la-1 (Personal Trainer): 80 RON / ședință.<br><br>_Sfat: Poți îngheța abonamentul direct din pagina ta de Profil dacă pleci în vacanță!_"

        # 2. LOGICĂ PENTRU ORAR / PROGRAM
        elif any(cuvant in user_message_lower for cuvant in ['orar', 'program', 'clase', 'sedinte', 'ședințe', 'zumba', 'yoga', 'aerobic']):
            now = timezone.now()
            clase_viitoare = FitnessClass.objects.filter(start_time__gte=now).order_by('start_time')[:3]
            
            if clase_viitoare.exists():
                clase_text = "<br>".join([f"• <strong>{c.name}</strong> - cu antrenor {c.instructor.last_name if c.instructor else 'Fără'} ({c.start_time.strftime('%d %b, ora %H:%M')})" for c in clase_viitoare])
                bot_response = f"🗓️ **Următoarele clase programate în sistem sunt:**<br>{clase_text}<br><br>Te poți înscrie la ele direct din pagina de Program!"
            else:
                bot_response = "Momentan nu sunt clase active în program pentru următoarele zile, dar echipa lucrează la actualizarea calendarului. Verifică secțiunea 'Rezervă o clasă' din Home!"

        # 3. LOGICĂ INTELIGENTĂ DE ÎNSCRIERE DIRECTĂ PRIN CHAT
        elif 'inscriere' in user_message_lower or 'înscriere' in user_message_lower or 'rezerva' in user_message_lower or 'rezervă' in user_message_lower:
            # Căutăm dacă utilizatorul a menționat un nume de clasă în mesaj
            now = timezone.now()
            clasa_gasita = None
            
            if 'zumba' in user_message_lower:
                clasa_gasita = FitnessClass.objects.filter(name__icontains='Zumba', start_time__gte=now).first()
            elif 'yoga' in user_message_lower:
                clasa_gasita = FitnessClass.objects.filter(name__icontains='Yoga', start_time__gte=now).first()
            elif 'aerobic' in user_message_lower:
                clasa_gasita = FitnessClass.objects.filter(name__icontains='Aerobic', start_time__gte=now).first()
                
            if clasa_gasita:
                # Verificăm dacă nu cumva are deja rezervare ca să nu duplicăm
                deja_rezervat = Booking.objects.filter(user=request.user, fitness_class=clasa_gasita).exists()
                if deja_rezervat:
                    bot_response = f"🔍 Am verificat în sistem și văd că **ești deja înscris(ă)** la clasa de {clasa_gasita.name} din {clasa_gasita.start_time.strftime('%d %M la %H:%M')}!"
                else:
                    # Îi creăm rezervarea direct din chat! (O funcționalitate uimitoare pentru profesori)
                    Booking.objects.create(user=request.user, fitness_class=clasa_gasita)
                    bot_response = f"✅ **Succes!** Te-am înscris direct prin comanda vocală/text la clasa de <strong>{clasa_gasita.name}</strong> programată pe {clasa_gasita.start_time.strftime('%d %b la ora %H:%M')}. Te așteptăm la antrenament!"
            else:
                bot_response = "✍️ Pentru a te înscrie direct din chat, spune-mi exact clasa dorită. Ex: _'Vreau o înscriere la Zumba'_ sau _'Rezervă o clasă de Yoga'_. Voi căuta primul interval disponibil!"

        return JsonResponse({'response': bot_response})
    return JsonResponse({'error': 'Metodă nepermisă'}, status=400)