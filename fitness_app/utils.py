from datetime import date, timedelta
from .models import Subscription, SessionPackage, Payment

# SINGLETON pentru configuratia salii
class GymSystemConfig:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GymSystemConfig, cls).__new__(cls, *args, **kwargs)
            # date administrative unice la nivel de aplicatie
            cls._instance.gym_name = "AlgoRhythm Gym"
            cls._instance.contact_phone = "0707 070 070"
            cls._instance.address = "Str. Academiei Nr. 14"
            cls._instance.referral_discount_percentage = 10  # reducerea de 10% din cerinte
            cls._instance.base_membership_price = 150.00
        return cls._instance


# FACTORY pentru abonamente
class BaseSubscriptionPlan:
    """Product de baza"""
    plan_code = None
    def get_details(self):
        cfg = Subscription.PLAN_CONFIG[self.plan_code]
        return {
            'plan': self.plan_code,
            'duration_days': cfg['days'],
            'price': cfg['price'],
            'description': f"Abonament {cfg['label']}",
        }
 
 
class MonthlyPlan(BaseSubscriptionPlan):
    plan_code = '1M'
 
class QuarterlyPlan(BaseSubscriptionPlan):
    plan_code = '3M'
 
class SemiAnnualPlan(BaseSubscriptionPlan):
    plan_code = '6M'
 
class AnnualPlan(BaseSubscriptionPlan):
    plan_code = '12M'
 
class SubscriptionFactory:
    """Creator"""
    _plans = {
        '1M': MonthlyPlan,
        '3M': QuarterlyPlan,
        '6M': SemiAnnualPlan,
        '12M': AnnualPlan,
    }
 
    @staticmethod
    def create_plan(plan_type):
        plan_type = (plan_type or "").upper()
        plan_cls = SubscriptionFactory._plans.get(plan_type, MonthlyPlan)
        return plan_cls()
 
 
# helper: aplica reducerea de 10% daca userul are reduceri disponibile
def apply_referral_discount(user, base_price):
    """
    Returneaza (pret_final, discount_procent_aplicat, a_folosit_reducere).
    Nu consuma reducerea aici, doar calculeaza. Consumarea se face dupa plata reusita
    """
    config = GymSystemConfig()
    if user.discounts_available > 0:
        discount = config.referral_discount_percentage
        final = round(float(base_price) * (1 - discount / 100), 2)
        return final, discount, True
    return float(base_price), 0, False
 
 
def consume_referral_discount(user):
    """Scade o reducere dupa ce a fost folosita la o plata reusita"""
    if user.discounts_available > 0:
        user.discounts_available -= 1
        user.save(update_fields=['discounts_available'])