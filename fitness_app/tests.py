from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, FitnessClass, Room, Booking, Subscription

class FitnessAppBookingTests(TestCase):
    
    def setUp(self):
        # se executa inainte de fiecare test pentru a pregati datele de baza
        self.client = Client()
        
        # cream sali de test conform modelului
        self.sala_mare = Room.objects.create(name="Sala Mare", room_type="GYM", capacity=50)
        self.sala_grup = Room.objects.create(name="Sala 1", room_type="GROUP", capacity=15)
        
        # cream utilizatori cu roluri explicite
        self.barbat = User.objects.create_user(
            username="andrei_test", password="password123", email="andrei@test.com",
            gender="M", is_child=False, role="CLI"
        )
        self.femeie = User.objects.create_user(
            username="elena_test", password="password123", email="elena@test.com",
            gender="F", is_child=False, role="CLI"
        )
        self.copil = User.objects.create_user(
            username="copil_test", password="password123", email="copil@test.com",
            gender="M", is_child=True, role="CLI"
        )

        data_azi = timezone.now().date()
        data_expirare = data_azi + timedelta(days=30)
        pret_standard = 150.00

        # activam abonamentele completand pretul, datele si planul obligatoriu
        Subscription.objects.create(user=self.barbat, start_date=data_azi, end_date=data_expirare, price=pret_standard, plan="1M", is_frozen=False)
        Subscription.objects.create(user=self.femeie, start_date=data_azi, end_date=data_expirare, price=pret_standard, plan="1M", is_frozen=False)
        Subscription.objects.create(user=self.copil, start_date=data_azi, end_date=data_expirare, price=pret_standard, plan="1M", is_frozen=False)
        
        # configuratie de timp pentru clase
        self.ora_start = timezone.now() + timedelta(days=1)

    def test_women_only_restriction_blocks_men(self):
        # testam daca un utilizator de gen masculin este blocat la o clasa exclusiva de femei
        clasa_femei = FitnessClass.objects.create(
            name="Aerobic Femei", type="GRP", room=self.sala_grup,
            max_capacity=10, is_for_women_only=True, start_time=self.ora_start
        )
        
        # logam barbatul in sistem
        self.client.login(username="andrei_test", password="password123")
        
        # incercam sa facem rezervarea
        url = reverse('book_class', args=[clasa_femei.id])
        self.client.get(url)
        
        # verificam ca rezervarea nu s-a creat in baza de date
        rezervare_exista = Booking.objects.filter(user=self.barbat, fitness_class=clasa_femei).exists()
        self.assertFalse(rezervare_exista)

    def test_overlapping_classes_are_blocked(self):
        # testam ca un utilizator nu se poate inscrie la doua clase care se suprapun orar
        clasa_1 = FitnessClass.objects.create(
            name="Yoga", type="GRP", room=self.sala_grup,
            max_capacity=10, start_time=self.ora_start
        )
        clasa_2 = FitnessClass.objects.create(
            name="Zumba", type="GRP", room=self.sala_grup,
            max_capacity=10, start_time=self.ora_start + timedelta(minutes=15)
        )
        
        # logam femeia in sistem
        self.client.login(username="elena_test", password="password123")
        
        # inscriere la prima clasa
        self.client.get(reverse('book_class', args=[clasa_1.id]))
        
        # inscriere la a doua clasa care ar trebui blocata
        self.client.get(reverse('book_class', args=[clasa_2.id]))
        
        # verificam ca utilizatorul are o singura clasa salvata
        numar_rezervari = Booking.objects.filter(user=self.femeie).count()
        self.assertEqual(numar_rezervari, 1)

    def test_parent_child_parallel_booking_allowed(self):
        # testam exceptia ca parintele se poate inscrie in paralel cu copilul la aceeasi ora
        clasa_adult = FitnessClass.objects.create(
            name="Crossfit Adulti", type="GRP", room=self.sala_mare,
            max_capacity=20, is_for_children=False, start_time=self.ora_start
        )
        clasa_copil = FitnessClass.objects.create(
            name="Gimnastica Copii", type="GRP", room=self.sala_grup,
            max_capacity=10, is_for_children=True, start_time=self.ora_start
        )
        
        # logam parintele
        self.client.login(username="elena_test", password="password123")
        
        # parintele rezerva pentru el clasa de adulti
        self.client.get(reverse('book_class', args=[clasa_adult.id]))
        
        # parintele rezerva de pe acelasi cont clasa pentru copil
        self.client.get(reverse('book_class', args=[clasa_copil.id]))
        
        # verificam ca ambele rezervari au fost permise pe contul Elenei
        total_rezervari = Booking.objects.filter(user=self.femeie).count()
        self.assertEqual(total_rezervari, 2)