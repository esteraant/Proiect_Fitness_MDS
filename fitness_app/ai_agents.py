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