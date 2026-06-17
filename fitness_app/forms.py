from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django.contrib.auth import get_user_model
from .models import Review



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

    friend_code = forms.CharField(
        max_length=15, 
        required=False, 
        label="Cod invitație prieten (Opțional)",
        help_text="Dacă ai un cod de la un prieten, introdu-l aici pentru a-l răsplăti cu 10% reducere!"
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

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Cum a fost antrenamentul?'}),
        }