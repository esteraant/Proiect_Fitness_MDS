from datetime import date, timedelta

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
    """Clasa de bază pentru planurile de abonament (Product)"""
    def get_details(self):
        raise NotImplementedError("Trebuie să implementezi această metodă!")

class MonthlyPlan(BaseSubscriptionPlan):
    def get_details(self):
        return {
            'plan': '1M',
            'duration_days': 30,
            'price': 150.00,
            'description': "Abonament Lunar Standard"
        }

class SemiAnnualPlan(BaseSubscriptionPlan):
    def get_details(self):
        return {
            'plan': '6M',
            'duration_days': 180,
            'price': 750.00,  # Reducere aplicată direct
            'description': "Abonament 6 Luni (Economisești o lună)"
        }

class AnnualPlan(BaseSubscriptionPlan):
    def get_details(self):
        return {
            'plan': '1Y',
            'duration_days': 365,
            'price': 1400.00,
            'description': "Abonament Anual VIP"
        }


class SubscriptionFactory:
    """Clasa Fabrică (Creator)"""
    @staticmethod
    def create_plan(plan_type):
        plan_type = (plan_type or "").upper()
        
        if plan_type == '6M':
            return SemiAnnualPlan()
        elif plan_type == '1Y':
            return AnnualPlan()
        else:
            return MonthlyPlan()  # planul default