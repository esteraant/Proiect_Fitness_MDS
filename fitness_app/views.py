from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from django.contrib import messages
from .forms import ReviewForm
from django.utils import timezone
from datetime import datetime, date, timedelta
from .models import Subscription, Booking, User, FitnessClass, Room, GymSession, Review, InstructorReview
from django.db.models import Q
from django.http import JsonResponse
from .utils import GymSystemConfig, SubscriptionFactory
from .ai_agents import ChatbotSupportAgent
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
    
    now = timezone.now()
    today = now.date()

    is_subscription_active = False
    if subscription:
        if subscription.end_date and subscription.end_date < today:
            # abonamentul expirat sa se stearga automat din DB
            subscription.delete()
            subscription = None
            is_subscription_active = False
        else:
            is_subscription_active = True

    clase_frecventate = Booking.objects.filter(user=request.user, attended=True).count()
    sesiuni_individuale = GymSession.objects.filter(user=request.user, start_time__lte=now).count()
  
    attended_count = clase_frecventate + sesiuni_individuale
    
    # calculam progresul pentru saptamana curenta ca sa il comparam cu obiectivul saptamanal
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    clase_saptamana = Booking.objects.filter(user=request.user, attended=True, fitness_class__start_time__gte=start_of_week).count()
    sesiuni_saptamana = GymSession.objects.filter(user=request.user, start_time__gte=start_of_week).count()
    antrenamente_saptamana_curenta = clase_saptamana + sesiuni_saptamana

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
                'pret': clasa_activa.price,
            })
        else:
            sali_info.append({
                'nume': sala.name,
                'clasa': None,
                'ocupare': 0,
                'locuri_libere': sala.capacity,
                'max': sala.capacity,
            })

    # AI predictie interval de varf
    peak_classes = FitnessClass.objects.filter(
        start_time__date=now.date(),
        start_time__hour__gte=18,
        start_time__hour__lt=20
    )
    total_max = sum(c.max_capacity for c in peak_classes)
    total_booked = sum(c.booking_set.count() for c in peak_classes)
    
    if total_max > 0:
        occupancy_rate = int((total_booked / total_max) * 100)
    else:
        occupancy_rate = 0
        
    ai_occupancy_prompt = f"Sala va fi la {occupancy_rate}% capacitate între orele 18:00 - 20:00. Îți recomandăm un antrenament la ora 16:30 pentru a evita aglomerația."

    try:
        import json
        from .ai_agents import GymAnalyticsAgent
        
        ora_locala = timezone.localtime(now)
        current_time_str = ora_locala.strftime("%H:%M")
        
        traffic_context = f"Capacitate curentă în Sala Mare: {ocupare_sala_mare}%. Procent estimat pe intervalul de vârf diseară (18:00-20:00): {occupancy_rate}% aglomerat. Locuri libere în acest moment: {locuri_libere_gym}."
        user_goal = request.user.fitness_goal or "Nesetată (Menținere generală)"
        
        db_classes = FitnessClass.objects.filter(start_time__gt=ora_locala).order_by('start_time')[:4]
        
        available_classes_list = []
        for c in db_classes:
            clasa_local_time = timezone.localtime(c.start_time)
            available_classes_list.append(f"- Clasa {c.name} programată în viitor la data de {clasa_local_time.strftime('%d %b, ora %H:%M')}")
            
        available_classes_text = "\n".join(available_classes_list)
        if not available_classes_text:
            available_classes_text = "Nu sunt clase de grup viitoare active programate în sistem pentru orele următoare."

        analytics_agent = GymAnalyticsAgent()
        json_bot_response = analytics_agent.generate_dashboard_insights(
            current_time_str=current_time_str,
            traffic_context=traffic_context,
            user_goal=user_goal,
            available_classes_text=available_classes_text
        )
        
        ai_data = json.loads(json_bot_response)
        ai_occupancy_prompt = ai_data.get("predictie_trafic", "").strip()
        ai_recommendation = ai_data.get("recomandare_antrenament", "").strip()
        
        for string_variabila in ['ai_occupancy_prompt', 'ai_recommendation']:
            text_existent = locals()[string_variabila]
            
            text_existent = text_existent.replace("&lt;", "<").replace("&gt;", ">")
            text_existent = text_existent.replace("Îți recomandăm să te prezinți", "Opțiunea optimă pentru tine este să te prezinți")
            text_existent = text_existent.replace("îți recomandăm să", "este indicat să")
            text_existent = text_existent.replace("Te recomandăm să", "Ai posibilitatea să")
            text_existent = text_existent.replace("te recomandăm să", "poți să")

            text_existent = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text_existent)
            text_existent = re.sub(r'_(.*?)_', r'<strong>\1</strong>', text_existent)
            
            locals()[string_variabila] = text_existent

        ai_occupancy_prompt = locals()['ai_occupancy_prompt']
        ai_recommendation = locals()['ai_recommendation']
        
    except Exception as e:
        print("--- Eroare critică parsare GymAnalyticsAgent JSON: ---", str(e))
        ai_occupancy_prompt = f"Sistemul estimează o capacitate de {occupancy_rate}% la orele de vârf."
        ai_recommendation = "Vizualizează programul claselor din meniu pentru a alege un antrenament adaptat scopului tău."

    # AI recomandare inghetare
    last_booking = Booking.objects.filter(user=request.user, attended=True).order_by('-booking_time').first()
    if last_booking:
        days_inactive = (now - last_booking.booking_time).days
    else:
        days_inactive = (now.date() - request.user.date_joined.date()).days

    show_freeze_reminder = False
    ai_freeze_prompt = ""
    if days_inactive >= 5 and subscription and not subscription.is_frozen:
        show_freeze_reminder = True
        ai_freeze_prompt = f"Observăm că au trecut {days_inactive} zile de la ultimul tău antrenament. Pentru a nu pierde valabilitatea abonamentului, îți recomandăm să revii la sală sau poți opta pentru înghețarea acestuia direct din Profil!"
    
    sesiuni_1la1 = GymSession.objects.filter(
        user=request.user,
        session_type='1TO1'
    ).order_by('start_time')

    # toate rezervarile la clase de grup
    rezervari_clase = Booking.objects.filter(user=request.user).order_by('fitness_class__start_time')
    user_role = str(getattr(request.user, 'role', '')).upper()
    is_instructor = (user_role == 'INSTRUCTOR' or user_role == 'INS')
    context = {
        'subscription': subscription,
        'is_subscription_active': is_subscription_active,
        'attended_count': attended_count,
        'antrenamente_saptamana_curenta': antrenamente_saptamana_curenta,
        'sala_mare': sala_mare,
        'ocupare_sala_mare': ocupare_sala_mare,
        'locuri_libere_gym': locuri_libere_gym,
        'sali_info': sali_info,
        'ai_occupancy_prompt': ai_occupancy_prompt,
        'ai_recommendation': ai_recommendation,
        'show_freeze_reminder': show_freeze_reminder,
        'ai_freeze_prompt': ai_freeze_prompt,
        'sesiuni_1la1': sesiuni_1la1,
        'rezervari_clase': rezervari_clase,
        'is_instructor': is_instructor,
    }
    return render(request, 'home.html', context)

def instructor_context_processor(request):
    """ Face variabila is_instructor disponibilă global în toate template-urile """
    if request.user.is_authenticated:
        user_role = str(getattr(request.user, 'role', '')).upper()
        return {
            'is_instructor': (user_role == 'INSTRUCTOR' or user_role == 'INS')
        }
    return {'is_instructor': False}

@login_required
def profile_view(request):
    user = request.user
    subscription = Subscription.objects.filter(user=user).first()
    
    # calculul zilelor ramase
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
        messages.success(request, "Obiectivul tău fitness a fost actualizat! Agentul AI a reconfigurar recomandările.")
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
        if subscription.is_frozen:
            now = timezone.now()
            Booking.objects.filter(user=request.user, fitness_class__start_time__gte=now).delete()
            GymSession.objects.filter(user=request.user, start_time__gte=now).delete()
            
            messages.success(request, "Abonamentul a fost înghețat cu succes! Toate rezervările tale viitoare au fost anulate, iar locurile au fost eliberate.")
        else:
            messages.success(request, "Abonamentul a fost reactivat cu succes! Te poți înscrie din nou la antrenamente.")
            
    return redirect('profile')

@login_required
def activate_subscription(request):
    sub, created = Subscription.objects.get_or_create(user=request.user)
    sub.start_date = date.today()
    sub.end_date = date.today() + timedelta(days=30)
    sub.is_frozen = False
    sub.save()
    return redirect('profile')

@login_required
def reviews_list_view(request):
    bookings_attended = Booking.objects.filter(user=request.user, attended=True)
    classes_to_review = []
    for b in bookings_attended:
        if not Review.objects.filter(user=request.user, fitness_class=b.fitness_class).exists():
            classes_to_review.append(b.fitness_class)
    sessions_attended = GymSession.objects.filter(user=request.user, session_type='1TO1', attended=True)
    sessions_to_review = []
    for s in sessions_attended:
        if not InstructorReview.objects.filter(user=request.user, instructor=s.instructor).exists():
            s.session_id = s.id 
            sessions_to_review.append(s)

    return render(request, 'reviews_list.html', {
        'classes_to_review': classes_to_review,
        'sessions_to_review': sessions_to_review
    })

@login_required
def add_instructor_review_view(request, session_id):
    session = get_object_or_404(GymSession, id=session_id, session_type='1TO1')

    if not session.attended or session.user != request.user:
        messages.error(request, "Poți lăsa recenzii doar pentru ședințele private la care ai participat.")
        return redirect('reviews_list')
        
    instructor = session.instructor

    if request.method == 'POST':
        rating_val = request.POST.get('rating')
        comment_val = request.POST.get('comment')
        
        if rating_val and comment_val:
            try:
                InstructorReview.objects.create(
                    user=request.user,
                    instructor=instructor,
                    rating=int(rating_val),
                    comment=comment_val
                )
                messages.success(request, f"Recenzia pentru instructorul {instructor.get_full_name()} a fost trimisă!")
                return redirect('home')
            except Exception as e:
                messages.error(request, "Ai lăsat deja o recenzie acestui instructor.")
                return redirect('reviews_list')
            
    return render(request, 'add_review.html', {
        'is_instructor_review': True,
        'instructor': instructor
    })

@login_required
def instructor_dashboard_view(request):
    user_role = str(getattr(request.user, 'role', '')).upper()
    
    if not request.user.is_superuser and user_role != 'INSTRUCTOR' and user_role != 'INS':
        return redirect('home')

    now = timezone.now()
    
    assigned_classes = FitnessClass.objects.filter(
        instructor=request.user, 
        start_time__gte=now
    ).order_by('start_time')

    upcoming_1to1_sessions = GymSession.objects.filter(
        instructor=request.user,
        session_type='1TO1',
        start_time__gte=now
    ).order_by('start_time')
    
    past_classes = FitnessClass.objects.filter(
        instructor=request.user,
        start_time__lt=now
    ).order_by('-start_time')[:10]

    past_1to1_sessions = GymSession.objects.filter(
        instructor=request.user,
        session_type='1TO1',
        start_time__lt=now
    ).order_by('-start_time')[:10]

    context = {
        'assigned_classes': assigned_classes,
        'upcoming_1to1_sessions': upcoming_1to1_sessions,
        'past_classes': past_classes,
        'past_1to1_sessions': past_1to1_sessions,
    }
    
    return render(request, 'instructor_dashboard.html', context)

@login_required
def add_review_view(request, class_id):
    fitness_class = get_object_or_404(FitnessClass, id=class_id)
    
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
    user = request.user

    subscription = Subscription.objects.filter(user=request.user).first()
    if subscription and subscription.is_frozen:
        messages.error(request, "Abonamentul tău este înghețat! Nu te poți înscrie la clase de grup până nu îl reactivezi din Profil.")
        return redirect('profile')
    
    if fitness_class.available_spots <= 0:
        messages.error(request, "Din păcate, nu mai sunt locuri disponibile la această clasă.")
        return redirect('fitness_classes_list')
    
    duration = getattr(fitness_class, 'duration_minutes', 60) 
    clasa_end_time = fitness_class.start_time + timedelta(minutes=int(duration))
    
    is_booking_for_child = False
    if fitness_class.is_for_children and hasattr(user, 'is_child') and not user.is_child:
        is_booking_for_child = True

    nume_copil = ""
    if request.method == 'POST':
        nume_copil = request.POST.get('child_name', '').strip()

    if fitness_class.is_for_children and nume_copil:
        already_booked = Booking.objects.filter(user=user, fitness_class=fitness_class, child_name__iexact=nume_copil).exists()
    else:
        already_booked = Booking.objects.filter(user=user, fitness_class=fitness_class, child_name__isnull=True).exists()
        
    if already_booked:
        messages.warning(request, "Exista deja o inscriere activa pentru acest copil la clasa selectata!")
        return redirect('fitness_classes_list')
    

    if fitness_class.is_for_women_only and hasattr(user, 'gender') and user.gender == 'M':
        messages.error(request, "Acces respins! Această clasă este exclusiv dedicată femeilor.")
        return redirect('fitness_classes_list')
    
    user_bookings = Booking.objects.filter(user=user)
    for b in user_bookings:
        b_duration = getattr(b.fitness_class, 'duration_minutes', 60)
        b_end_time = b.fitness_class.start_time + timedelta(minutes=int(b_duration))
        
        if fitness_class.start_time < b_end_time and clasa_end_time > b.fitness_class.start_time:
            if is_booking_for_child and b.child_name != nume_copil:
                continue
            if not fitness_class.is_for_children and b.child_name is not None:
                continue
                
            messages.error(request, f"Suprapunere de orar! Te-ai înscris deja la clasa '{b.fitness_class.name}' în acest interval.")
            return redirect('fitness_classes_list')
        
    if fitness_class.is_for_children:
        if hasattr(user, 'is_child') and not user.is_child:
            messages.info(request, "Notă: Ai rezervat un loc pentru copilul tău la această clasă specială.")
    else:
        if hasattr(user, 'is_child') and user.is_child:
            messages.error(request, "Conturile de copii nu pot efectua rezervări la clasele de adulți. Înscrierea trebuie făcută de un părinte!")
            return redirect('fitness_classes_list')
    
    subscription = Subscription.objects.filter(user=request.user).first()

    if not subscription:
        plan_handler = SubscriptionFactory.create_plan('1M')
        plan_details = plan_handler.get_details()

        subscription = Subscription.objects.create(
            user=request.user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=plan_details['duration_days']),
            is_frozen=False,
            price=plan_details['price'],
            plan=plan_details['plan']
        )
        messages.info(request, "Un abonament nou a fost activat pentru tine.")
    else:
        if subscription.is_frozen:
            messages.warning(request, "Abonamentul tău este înghețat. Dezgheață-l din profil!")
            return redirect('profile')

    Booking.objects.create(
        user=request.user,
        fitness_class=fitness_class,
        child_name=nume_copil if is_booking_for_child else None
    )
    messages.success(request, "Loc rezervat cu succes!")
    return redirect('fitness_classes_list')

@login_required
def book_1to1_view(request, instructor_id):
    subscription = Subscription.objects.filter(user=request.user).first()
    if subscription and subscription.is_frozen:
        messages.error(request, "Abonamentul tău este înghețat! Nu te poți înscrie până nu îl reactivezi.")
        return redirect('profile') 

    instructor = get_object_or_404(User, id=instructor_id, role='INS')
    now = timezone.now()
    
    slots = []
    for day_offset in range(7):
        day = now.date() + timedelta(days=day_offset)
        for hour in range(8, 21):
            slot_start = timezone.make_aware(
                datetime.combine(day, datetime.min.time().replace(hour=hour))
            )
            slot_end = slot_start + timedelta(minutes=90)
            
            instructor_ocupat = GymSession.objects.filter(
                instructor=instructor,
                start_time__lt=slot_end,
                end_time__gt=slot_start
            ).exists()
            
            clasa_ocupata = FitnessClass.objects.filter(
                instructor=instructor,
                start_time__lt=slot_end,
                start_time__gte=slot_start - timedelta(hours=2)
            ).exists()
            
            sala_mare = Room.objects.filter(room_type='GYM').first()
            sesiuni_la_ora = GymSession.objects.filter(
                start_time__lt=slot_end,
                end_time__gt=slot_start
            ).count()
            sala_plina = sala_mare and sesiuni_la_ora >= sala_mare.capacity
            
            if not instructor_ocupat and not clasa_ocupata and not sala_plina:
                slots.append(slot_start)
    
    if request.method == 'POST':
        slot_str = request.POST.get('slot')
        try:
            slot_start = timezone.make_aware(datetime.strptime(slot_str, '%Y-%m-%d %H:%M'))
            slot_end = slot_start + timedelta(minutes=90)
            if slot_start <= now + timedelta(minutes=30):
                messages.error(request, "Eroare la rezervare: Intervalul selectat a trecut deja!")
                context = {
                    'instructor': instructor,
                    'slots': slots,
                }
                return render(request, 'book_1to1.html', context)
            
            instructor_ocupat = GymSession.objects.filter(
                instructor=instructor,
                start_time__lt=slot_end,
                end_time__gt=slot_start
            ).exists()
            
            deja_rezervat = GymSession.objects.filter(
                user=request.user,
                start_time__lt=slot_end,
                end_time__gt=slot_start
            ).exists()
            
            if instructor_ocupat:
                messages.error(request, "Instructorul nu mai este disponibil la această oră.")
            elif deja_rezervat:
                messages.error(request, "Ai deja o sesiune rezervată în acest interval.")
            else:
                GymSession.objects.create(
                    user=request.user,
                    instructor=instructor,
                    session_type='1TO1',
                    start_time=slot_start
                )
                messages.success(request, f"Sesiune 1-la-1 rezervată cu {instructor.first_name} {instructor.last_name}!")
                return redirect('instructor_detail', instructor_id=instructor_id)
        except Exception as e:
            messages.error(request, f"Eroare la rezervare: {str(e)}")
    
    context = {
        'instructor': instructor,
        'slots': slots,
    }
    return render(request, 'book_1to1.html', context)

@login_required
def gym_free_session_view(request):
    sala_mare = Room.objects.filter(room_type='GYM').first()
    now = timezone.now()
    today = now.date()

    url_date_str = request.GET.get('date')
    if url_date_str:
        try:
            zi_ancora = datetime.strptime(url_date_str, '%Y-%m-%d').date()
        except ValueError:
            zi_ancora = today
    else:
        zi_ancora = today

    subscription = Subscription.objects.filter(user=request.user).first()
    if subscription and subscription.is_frozen:
        messages.error(request, "Abonamentul tău este înghețat. Dezgheață-l din profil pentru a putea rezerva un loc în Sala Mare!")
        return redirect('profile')

    toate_zilele = []
    for day_offset in range(6):
        zi = today + timedelta(days=day_offset)
        zi_saptamana = zi.weekday()
        
        if zi_saptamana <= 4:
            ora_start = 7
            ora_end_minute = 21 * 60 + 30
        else:
            ora_start = 7
            ora_end_minute = 16 * 60 + 30

        sloturi_zi = []
        minute_curent = ora_start * 60

        while minute_curent <= ora_end_minute:
            h = minute_curent // 60
            m = minute_curent % 60

            slot_start = timezone.make_aware(
                datetime.combine(zi, datetime.min.time().replace(hour=h, minute=m))
            )
            slot_end = slot_start + timedelta(minutes=90)

            disponibil_temporal = slot_start >= now + timedelta(minutes=30)

            sesiuni_active_sala = GymSession.objects.filter(session_type='FREE', start_time__date=zi)
            sesiuni = 0
            for s in sesiuni_active_sala:
                s_start = s.start_time
                s_end = s.start_time + timedelta(minutes=90)
                if not (slot_end <= s_start or slot_start >= s_end):
                    sesiuni += 1

            capacitate = sala_mare.capacity if sala_mare else 40
            sala_plina = sesiuni >= capacitate

            sesiuni_user_zi_db = GymSession.objects.filter(user=request.user, start_time__date=zi)
            user_suprapunere = False
            for s in sesiuni_user_zi_db:
                s_start = s.start_time
                s_end = s.start_time + timedelta(minutes=90)
                if not (slot_end <= s_start or slot_start >= s_end):
                    user_suprapunere = True
                    break

            sloturi_zi.append({
                'ora': f'{h:02d}:{m:02d}',
                'data': zi.strftime('%Y-%m-%d'),
                'sesiuni': sesiuni,
                'capacitate': capacitate,
                'pct': int((sesiuni / capacitate) * 100) if capacitate > 0 else 0,
                'liber': disponibil_temporal and not sala_plina and not user_suprapunere,
                'trecut': not disponibil_temporal,
                'user_rezervat': user_suprapunere,
            })

            minute_curent += 15

        zile_ro = {0: 'Luni', 1: 'Marti', 2: 'Miercuri', 3: 'Joi', 4: 'Vineri', 5: 'Sambata', 6: 'Duminica'}
        luni_ro = {1: 'Ian', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mai', 6: 'Iun', 7: 'Iul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        
        toate_zilele.append({
            'data': zi.strftime('%Y-%m-%d'),
            'label': f"{'Azi' if day_offset == 0 else 'Maine' if day_offset == 1 else zile_ro[zi_saptamana]}, {zi.day} {luni_ro[zi.month]}",
            'sloturi': sloturi_zi,
        })

    if request.method == 'POST':
        ora_str = request.POST.get('ora')
        data_str = request.POST.get('data')
        if not data_str or not ora_str:
            messages.error(request, "Selecteaza o zi si un slot orar.")
        else:
            try:
                zi_selectata = datetime.strptime(data_str, '%Y-%m-%d').date()
                ora_parts = datetime.strptime(ora_str, '%H:%M').time()
                slot_start = timezone.make_aware(datetime.combine(zi_selectata, ora_parts))
                slot_end = slot_start + timedelta(minutes=90)

                if slot_start < now + timedelta(minutes=30):
                    messages.error(request, "Slotul nu mai este disponibil — rezerva cu cel putin 30 de minute inainte.")
                else:
                    sesiuni_user_zi = GymSession.objects.filter(
                        user=request.user,
                        start_time__date=zi_selectata
                    )
                    permite_salvare = True
                    for s in sesiuni_user_zi:
                        s_end = s.start_time + timedelta(minutes=90)
                        if not (slot_end <= s.start_time or slot_start >= s_end):
                            permite_salvare = False
                            break
                            
                    if not permite_salvare:
                        messages.error(request, "Trebuie să lași o pauză de minimum 90 de minute între antrenamentele tale de pe parcursul unei zile!")
                        return redirect(f"/sala-mare/?date={data_str}")
                    
                    sesiuni_la_ora = GymSession.objects.filter(
                        start_time__lt=slot_end,
                        end_time__gt=slot_start
                    ).count()

                    if sala_mare and sesiuni_la_ora >= sala_mare.capacity:
                        messages.error(request, "Sala este plina la aceasta ora!")
                    else:
                        deja_rezervat = GymSession.objects.filter(
                            user=request.user,
                            start_time__lt=slot_end,
                            end_time__gt=slot_start
                        ).exists()
                        if deja_rezervat:
                            messages.error(request, "Ai deja o sesiune rezervata in acest interval!")
                        else:
                            GymSession.objects.create(
                                user=request.user,
                                instructor=None,
                                session_type='FREE',
                                start_time=slot_start,
                                end_time=slot_end
                            )
                            messages.success(request, f"Loc rezervat in sala mare pe {data_str} la ora {ora_str}!")
                            return redirect(f"/sala-mare/?date={data_str}")
            except Exception as e:
                messages.error(request, f"Eroare: {str(e)}")

    context = {
        'sala_mare': sala_mare,
        'toate_zilele': toate_zilele,
        'now': now,
        'selected_date': zi_ancora.strftime('%Y-%m-%d'),
    }
    return render(request, 'gym_session.html', context)

def instructors_view(request):
    instructors = User.objects.filter(role='INS')
    return render(request, 'instructors.html', {'instructors': instructors})

def instructor_detail_view(request, instructor_id):
    instructor = get_object_or_404(User, id=instructor_id, role='INS')
    now = timezone.now()
    all_upcoming = FitnessClass.objects.filter(instructor=instructor, start_time__gte=now).order_by('start_time')

    unique_classes = []
    seen_names = set()
    for fc in all_upcoming:
        if fc.name not in seen_names:
            unique_classes.append(fc)
            seen_names.add(fc.name)

    context = {
        'instructor': instructor,
        'classes': unique_classes
    }
    return render(request, 'instructor_detail.html', context)

@login_required
def my_bookings_view(request):
    acum = timezone.now()
    sesiuni_individuale = GymSession.objects.filter(user=request.user, start_time__gte=acum).order_by('start_time')
    clase_grup = Booking.objects.filter(user=request.user, fitness_class__start_time__gte=acum).order_by('fitness_class__start_time')
    
    return render(request, 'my_bookings.html', {
        'sesiuni_individuale': sesiuni_individuale,
        'clase_grup': clase_grup
    })

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            birth_date = form.cleaned_data.get('birth_date')
            if birth_date:
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                user.is_child = (age < 18)
            user.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

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
    all_sessions = FitnessClass.objects.filter(
        name=fitness_class.name,
        instructor=fitness_class.instructor,
        start_time__gte=now
    ).order_by('start_time')
    
    luni_ro = {
        1: "Ianuarie", 2: "Februarie", 3: "Martie", 4: "Aprilie", 
        5: "Mai", 6: "Iunie", 7: "Iulie", 8: "August", 
        9: "Septembrie", 10: "Octombrie", 11: "Noiembrie", 12: "Decembrie"
    }

    available_months = {}
    for session in all_sessions:
        month_key = f"{session.start_time.year}-{session.start_time.month:02d}"
        month_display = f"{luni_ro[session.start_time.month]} {session.start_time.year}"
        if month_key not in available_months:
            available_months[month_key] = month_display

    selected_month = request.GET.get('month')
    if not selected_month and available_months:
        selected_month = list(available_months.keys())[0]

    if selected_month:
        try:
            year_str, month_str = selected_month.split('-')
            sessions = all_sessions.filter(start_time__year=int(year_str), start_time__month=int(month_str))
        except (ValueError, IndexError):
            sessions = all_sessions
    else:
        sessions = all_sessions

    selected_day = request.GET.get('day_of_week')
    if selected_day and selected_day != 'all':
        sessions = [s for s in sessions if s.start_time.weekday() == int(selected_day)]
        
    bookings = None
    total_enrolled = 0
    show_attendance_list = False

    if request.user.is_authenticated:
        user_role = str(getattr(request.user, 'role', '')).upper()
        if request.user.is_superuser or fitness_class.instructor == request.user or user_role == 'ADM':
            show_attendance_list = True
            bookings = Booking.objects.filter(fitness_class=fitness_class).select_related('user')
            total_enrolled = bookings.count()

    context = {
        'fitness_class': fitness_class,
        'sessions': sessions,
        'available_months': available_months,
        'selected_month': selected_month,
        'selected_day': selected_day or 'all',
        'bookings': bookings,
        'total_enrolled': total_enrolled,
        'show_attendance_list': show_attendance_list,
    }
    return render(request, 'class_detail.html', context)
    
@login_required
def admin_dashboard_view(request):
    if not request.user.is_superuser:
        return redirect('home')

    total_users = User.objects.count()
    total_classes = FitnessClass.objects.count()
    recent_bookings = Booking.objects.all().order_by('-id')[:5] 
    gym_config = GymSystemConfig()

    context = {
        'total_users': total_users,
        'total_classes': total_classes,
        'recent_bookings': recent_bookings,
        'gym_name': gym_config.gym_name,
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def generate_recurrent_classes_view(request):
    if not request.user.is_superuser:
        return redirect('home')

    instructors = User.objects.filter(role='INS')
    sali_grup = Room.objects.filter(room_type='GROUP')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        class_type = request.POST.get('type')
        instructor_id = request.POST.get('instructor')
        max_capacity = request.POST.get('max_capacity', 10)
        duration_minutes = request.POST.get('duration_minutes', 60)
        
        is_for_women_only = 'is_for_women_only' in request.POST
        is_for_children = 'is_for_children' in request.POST
        
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        time_str = request.POST.get('class_time')
        selected_days = [int(day) for day in request.POST.getlist('days_of_week')]
        
        room = None
        if class_type == '1TO1':
            room = Room.objects.filter(room_type='GYM').first()
            max_capacity = min(int(max_capacity), 2)
        elif class_type == 'INDIVIDUAL':
            room = Room.objects.filter(room_type='GYM').first()
        else:
            room_id = request.POST.get('room')
            if room_id:
                room = Room.objects.filter(id=room_id).first()
            if not room:
                room = Room.objects.filter(room_type='GROUP', name__icontains='Sala 1').first()

        if not selected_days:
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
            
            print("Current date is in year 2026.")
            while current_date <= end_date:
                if current_date.weekday() in selected_days:
                    naive_datetime = datetime.combine(current_date, class_time)
                    localized_datetime = timezone.make_aware(naive_datetime)
                    end_datetime = localized_datetime + timedelta(minutes=int(duration_minutes))
                    price = request.POST.get('price', 0)

                    instructor_ocupat = FitnessClass.objects.filter(
                        instructor=instructor,
                        start_time__lt=end_datetime,
                        start_time__gte=localized_datetime - timedelta(hours=2) 
                    ).exists() if instructor else False
                    
                    sala_ocupata = FitnessClass.objects.filter(
                        room=room,
                        start_time__lt=end_datetime,
                        start_time__gte=localized_datetime - timedelta(hours=2)
                    ).exists() if room else False
                    
                    if instructor_ocupat:
                        messages.warning(request, f"Instructorul este deja ocupat pe data de {current_date} la ora {time_str}!")
                        current_date += timedelta(days=1)
                        continue
                        
                    if sala_ocupata:
                        messages.warning(request, f"Sala selectată este deja ocupată pe data de {current_date} la ora {time_str}!")
                        current_date += timedelta(days=1)
                        continue
                    
                    FitnessClass.objects.create(
                        name=name, type=class_type, instructor=instructor,
                        max_capacity=max_capacity, room=room,
                        is_for_women_only=is_for_women_only, is_for_children=is_for_children,
                        start_time=localized_datetime,
                        price=price
                    )
                    clase_create += 1
                current_date += timedelta(days=1)
            messages.success(request, f"Succes! Au fost generate automat {clase_create} clase în {room.name if room else 'sală'}..")
            return redirect('fitness_classes_list')
        except Exception as e:
            messages.error(request, f"A apărut o eroare la generare: {str(e)}")
    return render(request, 'generate_recurrent_classes.html', {'instructors': instructors, 'rooms': sali_grup})

def index_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'index.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def chatbot_response_view(request):
    if request.method == 'POST':
        user_message = ""
        
        if request.body:
            try:
                import json
                data = json.loads(request.body)
                user_message = data.get('message', '').strip()
            except json.JSONDecodeError:
                pass
        
        if not user_message:
            user_message = request.POST.get('message', '').strip()
            
        if not user_message:
            return JsonResponse({'response': "Te rog să scrii o întrebare validă!"})
            
        try:
            now = timezone.now()

            upcoming_classes = FitnessClass.objects.filter(start_time__gte=now).order_by('start_time')[:5]
            classes_list = [
                f"<strong>- Clasa {c.name}</strong>:<br>• Antrenor: {c.instructor.first_name if c.instructor else ''} {c.instructor.last_name if c.instructor else 'Staff'}<br>• Data: {c.start_time.strftime('%d %b, %H:%M')}<br>" 
                for c in upcoming_classes
            ]
            upcoming_classes_text = "\n".join(classes_list)
            
            user_bookings = Booking.objects.filter(user=request.user, fitness_class__start_time__gte=now).order_by('fitness_class__start_time')
            user_sessions = GymSession.objects.filter(user=request.user, start_time__gte=now).order_by('start_time')
            
            my_reservations_list = []
            for b in user_bookings:
                my_reservations_list.append(f"- Clasa {b.fitness_class.name} din data de {b.fitness_class.start_time.strftime('%d %b la %H:%M')}")
            for s in user_sessions:
                tip_sesiune = "Antrenament Privat 1-to-1" if s.session_type == '1TO1' else "Acces Liber Sala Mare"
                nume_antrenor = f" cu {s.instructor.get_full_name()}" if s.instructor else ""
                my_reservations_list.append(f"- {tip_sesiune}{nume_antrenor} programat pe {s.start_time.strftime('%d %b la %H:%M')}")
                
            my_reservations_text = "\n".join(my_reservations_list) if my_reservations_list else "Utilizatorul nu are nicio rezervare activă programată în acest moment."
            
            if 'chat_history' not in request.session:
                request.session['chat_history'] = []
            
            istoric_curent = request.session['chat_history'][-6:]
            
            mesaj_combinat_cu_istoric = ""
            for replica in istoric_curent:
                mesaj_combinat_cu_istoric += f"{replica['rol']}: {replica['text']}\n"
            mesaj_combinat_cu_istoric += f"user: {user_message}"
            
            bot_agent = ChatbotSupportAgent()
            bot_response = bot_agent.get_support_response(
                user_message=mesaj_combinat_cu_istoric, 
                upcoming_classes_text=upcoming_classes_text,
                user_reservations_text=my_reservations_text
            )
            
            if bot_response.startswith("{") and "book_class" in bot_response:
                try:
                    import json
                    action_data = json.loads(bot_response)
                    target_class_name = action_data.get('class_name', '')
                    
                    possible_classes = FitnessClass.objects.filter(
                        name__icontains=target_class_name,
                        start_time__gte=now
                    ).order_by('start_time')
                    
                    fitness_class = None
                    if possible_classes.exists():
                        match = re.search(r'\b(\d{1,2})\b', user_message)
                        if match:
                            day_int = int(match.group(1))
                            matched_class = possible_classes.filter(start_time__day=day_int).first()
                            if matched_class:
                                fitness_class = matched_class
                        
                        if not fitness_class:
                            fitness_class = possible_classes.first()

                    if fitness_class:
                        already_booked = Booking.objects.filter(user=request.user, fitness_class=fitness_class).exists()
                        if already_booked:
                            return JsonResponse({'response': f"Văd în sistem că <strong>ești deja înscris(ă)</strong> la clasa de {fitness_class.name} din {fitness_class.start_time.strftime('%d %b la %H:%M')}!"})
                        
                        if fitness_class.available_spots > 0:
                            Booking.objects.create(user=request.user, fitness_class=fitness_class)
                            return JsonResponse({
                                'response': f" <strong>Rezervare confirmată!</strong><br>Te-am înscris cu succes la clasa de <strong>{fitness_class.name}</strong>.<br>Ne vedem pe data de {fitness_class.start_time.strftime('%d %b la ora %H:%M')}!"
                            })
                        else:
                            return JsonResponse({'response': f"Din păcate, clasa de {fitness_class.name} este plină."})
                    else:
                        return JsonResponse({'response': f"Nu am găsit nicio clasă viitoare de '{target_class_name}' programată în sistem."})
                        
                except Exception as e:
                    print("--- Eroare rezervare JSON: ---", str(e))
                    return JsonResponse({'response': "A apărut o eroare la efectuarea înscrierii."})
            
            elif bot_response.startswith("{") and "cancel_class" in bot_response:
                try:
                    import json
                    action_data = json.loads(bot_response)
                    target_class_name = action_data.get('class_name', '')

                    rezervare_existenta = Booking.objects.filter(
                        user=request.user,
                        fitness_class__name__icontains=target_class_name,
                        fitness_class__start_time__gte=now
                    ).order_by('fitness_class__start_time').first()

                    if rezervare_existenta:
                        nume_clasa_salvat = rezervare_existenta.fitness_class.name
                        data_clasa_salvat = rezervare_existenta.fitness_class.start_time.strftime('%d %b la %H:%M')
                        rezervare_existenta.delete()
                        
                        return JsonResponse({
                            'response': f" <strong>Rezervare anulată cu succes!</strong><br>Te-am retras de la clasa de <strong>{nume_clasa_salvat}</strong> din data de {data_clasa_salvat}. Locul tău a fost eliberat."
                        })
                    else:
                        return JsonResponse({
                            'response': f"Am verificat în contul tău, însă <strong>nu ai nicio rezervare activă</strong> la o clasă viitoare de '{target_class_name}'."
                        })

                except Exception as e:
                    print("--- Eroare revocare rezervare JSON: ---", str(e))
                    return JsonResponse({'response': "S-a produs o eroare tehnică la anularea rezervării."})

            istoric_curent.append({'rol': 'user', 'text': user_message})
            istoric_curent.append({'rol': 'assistant', 'text': bot_response})
            request.session['chat_history'] = istoric_curent
            request.session.modified = True
            bot_response = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', bot_response)
            bot_response = re.sub(r'_(.*?)_', r'<strong>\1</strong>', bot_response)
            
            return JsonResponse({'response': bot_response})
            
        except Exception as e:
            print("--- Eroare critică chatbot view: ---", str(e))
            return JsonResponse({'response': "Momentan întâmpin o mică problemă tehnică de conexiune."})
            
    return JsonResponse({'error': 'Metoda nepermisa'}, status=400)