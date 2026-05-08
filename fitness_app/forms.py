from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    frequency_per_week = forms.IntegerField(
        min_value=1,
        max_value=7,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 3'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            'first_name', 
            'last_name', 
            'email', 
            'gender', 
            'birth_date', 
            'fitness_goal',
            'frequency_per_week'
        )