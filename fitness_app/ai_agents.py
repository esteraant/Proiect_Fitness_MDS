import requests
from django.conf import settings
from .utils import GymSystemConfig

class BaseAIAgent:
    """Clasă de bază care stochează configurația sălii și cheia API."""
    def __init__(self):
        self.config = GymSystemConfig()
        # Citim cheia API din settings.py
        self.api_key = getattr(settings, 'GROQ_API_KEY', '')

class ChatbotSupportAgent(BaseAIAgent):
    """Agent AI responsabil de chat, capabil să identifice precis când să facă o rezervare."""
    
    def get_support_response(self, user_message, upcoming_classes_text=""):
        if not user_message:
            return "Cu ce te pot ajuta astăzi?"

        system_prompt = (
            f"Ești asistentul virtual de suport oficial al sălii '{self.config.gym_name}'.\n"
            f"Informații administrative oficiale din sistem:\n"
            f"- Adresă sediu: {self.config.address}\n"
            f"- Telefon contact: {self.config.contact_phone}\n"
            f"- Preț abonament de bază lunar standard: {self.config.base_membership_price} RON\n"
            f"- Reducere invitație prieten (Referral): {self.config.referral_discount_percentage}% discount\n"
            f"- Tipuri de activități: Sesiuni libere individuale în Sala Mare, Clase de grup organizate, Antrenamente 1-la-1 cu antrenor personal.\n\n"
            f"PROGRAMUL GENERAL DE FUNCȚIONARE AL SĂLII:\n"
            f"- De luni până vineri: Deschis între orele 07:00 și 23:00\n"
            f"- În weekend (Sâmbătă și Duminică): Deschis între orele 07:00 și 18:00\n\n"
        )
        
        if upcoming_classes_text:
            system_prompt += f"Programul curent al claselor specifice programate în timp real:\n{upcoming_classes_text}\n\n"
        
        system_prompt += (
            "Reguli stricte de comportament și FUNCȚIONARE:\n"
            "1. Răspunde politicos, prietenos și natural în limba română, adaptat direct la persoana a II-a singular.\n"
            "2. Când oferi detalii, folosește tag-uri HTML simple (precum <strong> pentru îngroșare și <br> pentru rând nou) pentru lărgirea lizibilității.\n"
            "3. DETECTARE REZERVARE (FOARTE CRITIC): ...\n"
            "4. Dacă utilizatorul vrea o rezervare la o activitate care NU se află deloc în listă... \n" 
            "5. NU folosi sub nicio formă emoji-uri și nu combina în același răspuns textul liber cu formatul JSON.\n"
            "6. GESTIONARE PRINCIPIALĂ OFF-TOPIC: Dacă utilizatorul pune întrebări complet colaterale, glume sau subiecte care nu au nicio legătură cu sala de fitness, nutriția, programul sau serviciile voastre (ex: despre unicorni, politică, filme), răspunde-i scurt, glumeț și amabil, dar REDIRECȚIONEAZĂ-L imediat în aceeași replică înapoi către sală. "
            "Exemplu de abordare: 'Deși mi-ar plăcea să avem un unicorn la recepție, eu mă pricep cel mai bine la fitness! Cu ce te pot ajuta astăzi la AlgoRhythm Gym? Vrei să afli programul sau să te înscrii la o clasă?'\n"
            "7. INTERZICERE MARKDOWN (CRITIC): Este STRICT INTERZIS să folosești caractere speciale din Markdown, cum ar fi asteriscuri duble (**text**) sau caractere underscore (_text_) pentru a evidenția cuvinte. Pentru orice evidențiere sau îngroșare de text, folosește EXCLUSIV tag-ul HTML <strong>text</strong>."
)

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                print(f"--- Eroare API Groq (Cod {response.status_code}): ---", response.text)
                return "Momentan întâmpin o mică eroare la nivel de server API."
        except Exception as e:
            print("--- Eroare critică de rețea: ---", str(e))
            return "Sistemul întâmpină probleme de conectare la rețeaua cloud."
        
class GymAnalyticsAgent(BaseAIAgent):
    """Agent AI de analiza predictiva a traficului si recomandari de antrenamente personalizate"""
    
    def generate_dashboard_insights(self, current_time_str, traffic_context, user_goal, available_classes_text):
        system_prompt = (
            "Ești un sistem avansat de analiză predictivă și optimizare fitness (GymAnalyticsAgent).\n"
            "Sarcina ta este să examinezi starea curentă a sălii și profilul utilizatorului și să întorci un răspuns EXCLUSIV sub forma unui obiect JSON valid, fără alte texte înainte sau după.\n\n"
            
            "STRUCTURA JSON CERUTĂ:\n"
            "{\n"
            '  "predictie_trafic": "Aici pui textul pentru prima secțiune. Analizează ora curentă și aglomerația primită. Oferă recomandări de ORE CONCRETE (intervale specifice din zi sau de mâine) la care utilizatorul poate veni pentru a prinde sala liberă și a se antrena eficient.",\n'
            '  "recomandare_antrenament": "Aici pui textul pentru a doua secțiune. Analizează obiectivul din profil, recomandă clase specifice din listă și menționează exact ce tip de antrenament individual să facă în sala mare (ex: Full Body, Brațe, Picioare, Spate sau Cardio) adaptat scopului."\n'
            "}\n\n"
            
            "REGULI STRICTE DE LOGICĂ TEMPORALĂ (FOARTE CRITIC):\n"
            "- Uită-te cu atenție la 'Ora actuală a utilizatorului' primită în mesaj.\n"
            "- Este STRICT INTERZIS să recomanzi clase sau intervale orare din ziua curentă care au o oră MAI MICĂ decât ora actuală a utilizatorului! (Exemplu: dacă ora actuală este 18:55, nu ai voie sub nicio formă să recomanzi o clasă de la ora 16:00 din aceeași zi deoarece A TRECUT DEJA. Recomandă doar clase viitoare sau antrenamente de mâine).\n\n"
            
            "REGULI STRICTE DE FORMATARE ȘI CONȚINUT (CONSTRÂNGERI ABSOLUTE):\n"
            "- ADRESARE DIRECTĂ (OBLIGATORIU): Răspunde exclusiv la persoana a II-a singular (tu/ție). Te adresezi direct utilizatorului logat.\n"
            
            "- LISTĂ NEAGRĂ DE CUVINTE INTERZISE (STRICT INTERZIS):\n"
            "  * Este COMPLET INTERZIS să folosești cuvântul 'recomandăm', 'recomand', 'sugerăm' sau orice derivat al verbului 'a recomanda/a sugera' la persoana I plural sau singular.\n"
            "  * Motiv: Tu nu ești o echipă de oameni, ești un panou de bord automatizat (dashboard istoric).\n"
            
            "- GHID DE ÎNLOCUIRE A FORMULĂRILOR (AȘA NU vs. AȘA DA):\n"
            "  * AȘA NU: 'Îți recomandăm să începi cu o sesiune de Aerobic' sau 'Te recomandăm să faci un antrenament'.\n"
            "  * AȘA DA (Formulări permise): 'Opțiunea ideală pentru programul tău este o sesiune de Aerobic', 'Ai ocazia să profiți de spațiul liber', 'Este indicat să execuți un antrenament de Full Body', sau 'Planul tău de astăzi include...'.\n"
            
            "- FORMATRE HTML: Nu folosi caractere speciale Markdown (** sau _). Folosește doar tag-ul HTML <strong>text</strong> pentru îngroșare și <br> pentru rând nou."
        )

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        user_content = (
            f"Ora actuală a utilizatorului: {current_time_str}.\n"
            f"Contextul de trafic din sală în timp real: {traffic_context}.\n"
            f"Obiectivul curent din profilul utilizatorului: '{user_goal}'.\n"
            f"Lista de clase viitoare programate în sistem:\n{available_classes_text}"
        )

        payload = {
            "model": "llama-3.1-8b-instant",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2
        }

        try:
            import requests
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            return '{"predictie_trafic": "Datele despre trafic se reîncarcă...", "recomandare_antrenament": "Recomandările se reîncarcă..."}'
        except Exception:
            return '{"predictie_trafic": "Eroare conexiune modul predictiv.", "recomandare_antrenament": "Eroare conexiune modul recomandări."}'