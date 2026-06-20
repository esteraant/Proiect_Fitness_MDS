# PROCESUL DE DEZVOLTARE: AlgoRhythm Gym
## (Aplicatie de management al unei sali de fitness)

---

# CUPRINS
1. Cererea de specificații, backlog-uri
2. Descrierea arhitecturii, diagrame
3. Source control cu GIT
4. Teste automate
5. Raportare bug și rezolvare cu pull request
6. Design patterns
7. Raport despre folosirea instrumentelor AI
   
---

## Cererea de specificații, backlog-uri

Pentru planificarea, organizarea și monitorizarea progresului aplicației ***AlgoRhythm Gym***, echipa noastră a adoptat ca instrument principal pentru managementul activităților platforma *Trello*.
<img width="2880" height="1354" alt="image" src="https://github.com/user-attachments/assets/64474f98-e716-4171-9e7a-c09f6f9fb54c" />

Am definit specificațiile proiectului sub formă de tichere și le-am organizat în următoarele liste:
- Etapa 0: o etapă de inițiere a proiectului;
- Forecast: am stocat ideile viitoare, cerințele tehnice sau administrative (comenzi utile de terminal pentru testare, idei de branch-uri);
- To-Do: a conținut sarcinile selectate și prioritizate pentru a fi implementate în etapa curentă de dezvoltare;
- In Progress: task-urike la care lucram în momentul respectiv;
- Done: lista care validează munca depusă, conținând toate funcționalitățile complet implementate, testate și integrate în ramura principală.
  
---

## Descrierea arhitecturii, diagrame

Aplicația ***AlgoRhythm Gym*** a fost proiectată utilizând un model arhitectural de tip **MVT (Model-View-Template)**, specific framework-ului web **Django**. Arhitectura este împărțită în următoarele straturi principale:
 1. **Frontend**: construit exclusiv cu *HTML/CSS*, fără framework-uri externe precum Bootstrap, și *JavaScript*, pentru mici interacțiuni, meniu de navigare pe mobil și comunicarea asincronă a asistentului AI
 2. **Backend**: dezvoltat în limbajul *Python* utilizând Django. Acesta gestionează autentificarea utilizatorilor, generarea orarelor recurente și interogarea agenților AI
 3. **Baza de date**: utilizează sistemul **ORM (Object-Relational Mapping)** din Django pentru a interacționa în mod sigur și eficient cu baza de date relațională SQL
 4. **Servicii Externe (Integrare AI)**: platforma comunică prin **apeluri API** cu modele de *Inteligență Artificială* (agenții AlgoRhythm AI) pentru a oferi predicții ale gradului de ocupare, recomandări personalizate pentru antrenamente și posibilitatea de a interacționa într-un chatbot.

Modelul de date a fost structurat relațional. Entitățile principale ale sistemului sunt:
- **User**: diferențiază utilizatorii prin roluri (*Client, Instructor, Admin*) și stochează date precum obiectivul de fitness și frecvența săptămânală de antrenamente
- **Subscription**: gestionează statusul financiar al clientului (*activ, înghețat, expirat*), planul ales și data activării
- **SessionPackage**: folosit de sistemul *Factory* pentru a genera intrări limitate fie la o clasă de grup (GRP), fie la sesiuni de Personal Training (1TO1)
- **Room**: Definește capacitatea maximă a unei încăperi
- **FitnessClass**: un eveniment în timp (ex. Zumba, Yoga). Are atribute precum *capacitate_maxima*, *ora_start* și o relație *Foreign Key* către *User* (pentru Instructorul asignat) și către *Room* (Sala în care se desfășoară)
- **Booking**: tabele de legătură care înregistrează participarea unui client (*User*) la un anumit antrenament
- **GymSession**: dedicat sesiunilor individuale în Sala Mare sau sesiunilor private de antrenament (1TO1). Durata fiecărei sesiuni este calculată automat la salvare adăugând 90 de minute la ora de începere.

### Diagrama ER (Entitate-Relație), generată folosind 'django-extentions':
<img width="2740" height="1494" alt="diagrama_er" src="https://github.com/user-attachments/assets/33ddf68f-6064-4a86-adbd-125225c2afbb" />

---

## Source control cu git. Raportare bug și rezolvare cu pull request

Pentru a asigura o colaborare eficientă și un istoric clar al modificărilor, proiectul a fost dezvoltat utilizând *Git*, iar repository-ul a fost găzduit remote pe platforma **GitHub**. Am adoptat un flux de lucru colaborativ, care a asigurat stabilitatea codului pe ramura principală și a permis dezvoltarea funcționalităților în paralel.  
Dezvoltarea nu s-a realizat doar direct pe ramura main, am creat **branches**. Un exemplu concret din dezvoltare a fost crearea ramurii *refactorizare-frontend* pentru organizarea fișierelor HTML și CSS.  Munca a fost salvată iterativ prin comenzi **git commit**. Odată ce o funcționalitate a fost finalizată pe ramura ei izolată, am deschis un **Pull Request** către ramura principală (ex: PR #14 pentru curățenia codului HTML). Aceasta ne-a oferit posibilitatea de a revizui codul înainte de integrare și de a lega rezolvarea de anumite *issues* raportate anterior pe platformă.  
<img width="1680" height="1248" alt="image" src="https://github.com/user-attachments/assets/4f9a44b8-e0bb-4c70-928d-fcb64efa4b01" />
<img width="1984" height="1322" alt="image" src="https://github.com/user-attachments/assets/a8413d73-2dc6-47dc-bcf9-19aa092b70ea" />
<img width="2026" height="428" alt="image" src="https://github.com/user-attachments/assets/5bfea0f8-e5e5-4f58-9900-30738439a0ce" />
<img width="2330" height="1412" alt="image" src="https://github.com/user-attachments/assets/53dbe244-b4af-47b1-bf65-74713ea6f11b" />

---

## Teste automate

Pentru a garanta corectitudinea aplicație, am implementat mai multe teste automate utilizând framework-ul de testare integrat din Django. Prin simularea unui client web (folosind *django.test.Client*), am testat interacțiunea completă dintre modele, interfață și sistemul de validare. 
- **test_women_only_restriction_blocks_men**: ne asigurăm că metoda *book_class* respinge dinamic o înscriere dacă utilizatorul are setat genul masculin (*gender="M"*) și încearcă să se rezerve la o clasă cu atributul *is_for_women_only=True*;
- **test_overlapping_classes_are_blocked**: validăm o constrângere critică a sistemului de rezervări. Am simulat o înscriere la o clasă și o încercare imediată de înscriere la altă clasă care începe la doar 15 minute distanță, în timp ce prima încă se desfășoară. Testul confirmă, prin *assertEqual*, că sistemul a înregistrat o singură rezervare, blocând suprapunerea;
- **test_parent_child_parallel_booking_allowed**: aceasta verifică excepția introdusă intenționat în logica de suprapunere orară. Un cont de adult (părintele) se poate programa la o clasă de adulți și, concomitent, la aceeași oră, poate programa și contul subordonat (copilul) la o clasă *is_for_children=True*. Validarea se face confirmând existența ambelor rezervări pe contul principal.
- <img width="1436" height="414" alt="image" src="https://github.com/user-attachments/assets/56802f5d-1855-4f9c-b2a1-37bd8e5dea03" />

---

## Design Patterns

În dezvoltarea aplicației AlgoRhythm Gym, am utilizat două Design Patterns: *Singleton* și *Factory*. 
1. Scopul modelului *Singleton* este de a garanta că o clasă are o singură instanță globală pe tot parcursul ciclului de viață al aplicației și de a oferi un punct unic de acces la aceasta.
În cadrul proiectului nostru, Singleton a fost aplicat în două puncte cheie:
- **conexiunea la baza de date și configurația serverului**: Django utilizează nativ modelul Singleton pentru managementul conexiunilor SQL și pentru obiectul global de setări (*django.conf.settings*). În loc să se deschidă o conexiune nouă la baza de date pentru fiecare cerere HTTP a unui client, sistemul refolosește aceeași instanță unică, optimizând consumul de memorie;
- **instanțierea agentului AlgoRhythm AI**: serviciul de backend responsabil cu interogarea modelelor inteligente (cum este cel folosit pentru generarea recomandărilor în *ChatMessage*) este implementat ca un Singleton. Clasa clientului API este inițializată o singură dată la pornirea serverului, păstrând în memorie configurația și cheia securizată, evitând costul computațional al re-inițializării la fiecare mesaj trimis în chat.

2. Modelul *Factory* abstractizează procesul de creare a obiectelor, permițând subclasei sau unei logici centrale să decidă ce tip de obiect specific trebuie instanțiat în funcție de parametrii primiți la rulare. În aplicația noastră, acest șablon se regăsește în:
- **SessionPackage**: în funcție de selecția utilizatorului din interfață, sistemul folosește o logică de tip Factory pentru a genera un pachet. Dacă parametrul primit este 1TO1, se instanțiază o structură polimorfică ce obligă alegerea unui instructor personal și aplică regulile de validare aferente. Dacă parametrul este GRP, Factory-ul configurează pachetul pentru o clasă de tip grup, legându-l de o clasă specifică. Această abstractizare ascunde complexitatea creării obiectului în spatele unei configurări unitare (*PACKAGE_CONFIG*);
- **interfața ORM Django (Manager)**: Utilizarea metodei *.objects.create()* pentru entități precum *Booking* sau *User* reprezintă o implementare directă a pattern-ului ***Factory Method***. Noi doar trimitem datele date, iar managerul intern al Django decide cum să construiască obiectul Python complet și cum să ruleze interogarea SQL corespunzătoare.

---

## Raport despre folosirea instrumentelor AI

Proiectul AlgoRhythm Gym integrează o componentă nativă avansată de ***Inteligență Artificială (AI Agents)***, concepută pentru a asigura suport contextual și automatizări predictive. Agenții AI pe care i-am implementat în proiectul nostru sunt:

1. **Agent AI pentru predicția traficului în sală și de recomandare de antrenament**: integrat în panoul principal din *home.html*, acest agent rulează interogări pe baza istoricului de intrare din toate cele 3 săli și generează prompt-uri predictive privind fluxul de membri la momentul accesării site-ului, oferind utilizatorilor insight-uri privind planificarea optimă a antrenamentelor. De asemenea, acest agent poate face recomandări de antrenamente utilizatorilor în funcție de clasele disponibile și de obiectivele setate de utilizator în profilul personal.
2. **Agent AI de ChatBot Support**: un asistent ChatBoy convențional, integrat la nivelul structurii globale *base.html*. Acesta primește mesaje în mod asincron prin request-uri securizate JSON (*Fetch API*) și stochează contextul discuției în sesiune.

### Cazuri de utilizare și automatizare (*Function Calling*):
Agenții AI nu se limitează la răspunsuri informative contextuale, ci sunt conectați direct la logica de business din backend prin metode specifice:

1. Agentul AI de predicție și recomandări: **Ghidare bazată pe Obiective**
    - În pagina de *Profil*, agentul analizează cuvintele cheie introduse de utilizator în caseta de *Obiective Fitness* și generează recomandări personalizate și remindere dinamice privind înghețarea sau prelungirea abonamentului (în cazul în care utilizatorul nu a mai fost la un antrenament de o perioadă mai lungă de timp)
<img width="1165" height="427" alt="image" src="https://github.com/user-attachments/assets/b007ea9d-28c6-4c12-bc98-d5c4bea240a9" />
<img width="1270" height="642" alt="image" src="https://github.com/user-attachments/assets/ba1ef423-8b4d-46a8-9d02-2f5078f085d7" />

2. Agentul AI de asistență în chat (ChatBot): **Înscrieri rapide (Conversational Booking)**
   - La recepționarea unei comenzi de înscriere la o clasă, precum *"Înscrie-mă la clasa de Zumba de marți"*, asistentul AI parsează intenția utilizatorului, interoghează baza de date pentru clasa corespunzătoare și declanșează automat metoda de înscriere, returnând confirmarea direct în fereastra de chat.
<img width="437" height="553" alt="image" src="https://github.com/user-attachments/assets/e8f67862-ec05-4959-95fd-8cd2fc0ed8e3" />
