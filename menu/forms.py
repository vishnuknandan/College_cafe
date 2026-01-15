from django import forms
from django.contrib.auth.models import User

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "Enter Password"
            }
        )
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "Enter Username"
            }),
            "email": forms.EmailInput(attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "Enter Email Address"
            }),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Hash the password
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
            "placeholder": "Username or Email"
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
            "placeholder": "Password"
        })
    )

from .models import Review, Profile

class UserOrderForm(forms.Form):
    # Field removed as per user request
    pass

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
                "min": "1", "max": "5"
            }),
            'comment': forms.Textarea(attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none h-24 focus:ring-2 focus:ring-red-500",
                "placeholder": "Enter your feedback"
            }),
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "First Name"
            }),
            'last_name': forms.TextInput(attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "Last Name"
            }),
            'email': forms.EmailInput(attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "Email"
            }),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_pic', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={
                "class": "w-full p-3 mb-4 bg-gray-800 text-white rounded outline-none h-24 focus:ring-2 focus:ring-red-500",
                "placeholder": "Tell us about yourself"
            }),
            'profile_pic': forms.FileInput(attrs={
                "class": "hidden",
                "id": "profile-upload" 
            }),
        }
