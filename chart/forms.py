from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm as BasePasswordChangeForm
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User
import re


class UserRegistrationForm(UserCreationForm):
    """
    Form for user registration with additional astrological fields
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'Enter your email address'
        })
    )

    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'type': 'date',
            'placeholder': 'Birth date (optional)'
        }),
        help_text="Optional: Your birth date for personalized features"
    )

    birth_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'type': 'time',
            'placeholder': 'Birth time (optional)'
        }),
        help_text="Optional: Your birth time for accurate chart calculations"
    )

    birth_location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'City, Country (optional)'
        }),
        help_text="Optional: Your birth location for chart calculations"
    )

    timezone = forms.ChoiceField(
        choices=[
            ('UTC', 'UTC'),
            ('America/New_York', 'Eastern Time (ET)'),
            ('America/Chicago', 'Central Time (CT)'),
            ('America/Denver', 'Mountain Time (MT)'),
            ('America/Los_Angeles', 'Pacific Time (PT)'),
            ('America/Halifax', 'Atlantic Time (AT)'),
            ('Europe/London', 'Greenwich Mean Time (GMT)'),
            ('Europe/Paris', 'Central European Time (CET)'),
            ('Asia/Tokyo', 'Japan Standard Time (JST)'),
            ('Australia/Sydney', 'Australian Eastern Time (AET)'),
        ],
        initial='UTC',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        }),
        help_text="Your timezone for accurate time calculations"
    )

    # Override password fields with custom styling
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'Create a strong password'
        }),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'Confirm your password'
        }),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    # Override username field
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'Choose a username'
        }),
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
    )

    # Terms and conditions
    agree_to_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-plum2 bg-dark2 text-accent focus:ring-accent focus:ring-offset-dark2'
        }),
        error_messages={
            'required': 'You must agree to the terms and conditions to register.'
        }
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'birth_date', 'birth_time', 'birth_location', 'timezone', 'password1', 'password2', 'agree_to_terms')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Check if username is already taken
            if User.objects.filter(username=username).exists():
                raise ValidationError('This username is already taken.')

            # Validate username format
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                raise ValidationError('Username can only contain letters, numbers, and underscores.')

            if len(username) < 3:
                raise ValidationError('Username must be at least 3 characters long.')

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('This email address is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        birth_date = cleaned_data.get('birth_date')
        birth_time = cleaned_data.get('birth_time')
        birth_location = cleaned_data.get('birth_location')

        # If any birth data is provided, require all
        if any([birth_date, birth_time, birth_location]):
            if not all([birth_date, birth_time, birth_location]):
                raise ValidationError(
                    'If you provide birth information, please provide all fields (date, time, and location).'
                )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        # Set astrological preferences
        user.preferred_zodiac_type = 'tropical'
        user.preferred_house_system = 'placidus'
        user.preferred_ai_model = 'gpt-4'

        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """
    Form for editing user profile information
    """
    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'type': 'date'
        })
    )

    birth_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'type': 'time'
        })
    )

    birth_location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'City, Country'
        })
    )

    latitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'step': '0.000001',
            'placeholder': 'Latitude (e.g., 40.7128)'
        })
    )

    longitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'step': '0.000001',
            'placeholder': 'Longitude (e.g., -74.0060)'
        })
    )

    timezone = forms.ChoiceField(
        choices=[
            ('UTC', 'UTC'),
            ('America/New_York', 'Eastern Time (ET)'),
            ('America/Chicago', 'Central Time (CT)'),
            ('America/Denver', 'Mountain Time (MT)'),
            ('America/Los_Angeles', 'Pacific Time (PT)'),
            ('America/Halifax', 'Atlantic Time (AT)'),
            ('Europe/London', 'Greenwich Mean Time (GMT)'),
            ('Europe/Paris', 'Central European Time (CET)'),
            ('Asia/Tokyo', 'Japan Standard Time (JST)'),
            ('Australia/Sydney', 'Australian Eastern Time (AET)'),
        ],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        })
    )

    preferred_zodiac_type = forms.ChoiceField(
        choices=[('tropical', 'Tropical'), ('sidereal', 'Sidereal')],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        })
    )

    preferred_house_system = forms.ChoiceField(
        choices=[('placidus', 'Placidus'), ('whole_sign', 'Whole Sign')],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        })
    )

    preferred_ai_model = forms.ChoiceField(
        choices=[
            ('gpt-4', 'GPT-4'),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
            ('claude-3-opus', 'Claude 3 Opus'),
            ('claude-3-sonnet', 'Claude 3 Sonnet'),
            ('mistral-medium', 'Mistral Medium'),
        ],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        })
    )

    profile_public = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-plum2 bg-dark2 text-accent focus:ring-accent focus:ring-offset-dark2'
        })
    )

    chart_history_public = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-plum2 bg-dark2 text-accent focus:ring-accent focus:ring-offset-dark2'
        })
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'birth_date', 'birth_time',
            'birth_location', 'latitude', 'longitude', 'timezone',
            'preferred_zodiac_type', 'preferred_house_system', 'preferred_ai_model',
            'profile_public', 'chart_history_public'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
                'placeholder': 'Email address'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email is already taken by another user
            existing_user = User.objects.filter(email=email).exclude(pk=self.instance.pk).first()
            if existing_user:
                raise ValidationError('This email address is already registered by another user.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        birth_date = cleaned_data.get('birth_date')
        birth_time = cleaned_data.get('birth_time')
        birth_location = cleaned_data.get('birth_location')
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        # Validate birth data consistency
        if any([birth_date, birth_time, birth_location]):
            if not all([birth_date, birth_time, birth_location]):
                raise ValidationError(
                    'If you provide birth information, please provide all fields (date, time, and location).'
                )

        # Validate coordinates
        if latitude is not None and (latitude < -90 or latitude > 90):
            raise ValidationError('Latitude must be between -90 and 90 degrees.')

        if longitude is not None and (longitude < -180 or longitude > 180):
            raise ValidationError('Longitude must be between -180 and 180 degrees.')

        return cleaned_data


class PasswordChangeForm(BasePasswordChangeForm):
    """
    Custom password change form with styling
    """
    old_password = forms.CharField(
        label=_("Current password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'Current password'
        }),
    )

    new_password1 = forms.CharField(
        label=_("New password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'New password'
        }),
        help_text=password_validation.password_validators_help_text_html(),
    )

    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'Confirm new password'
        }),
    )


class ChartForm(forms.Form):
    """
    Form for generating new charts
    """
    name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'Chart name (optional)'
        }),
        help_text="Optional name for this chart"
    )

    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'type': 'date',
            'required': 'required'
        })
    )

    birth_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'type': 'time',
            'required': 'required'
        })
    )

    latitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'step': '0.000001',
            'required': 'required'
        })
    )

    longitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'step': '0.000001',
            'required': 'required'
        })
    )

    location_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'placeholder': 'City, Country'
        })
    )

    timezone = forms.ChoiceField(
        choices=[
            ('UTC', 'UTC'),
            ('America/New_York', 'Eastern Time (ET)'),
            ('America/Chicago', 'Central Time (CT)'),
            ('America/Denver', 'Mountain Time (MT)'),
            ('America/Los_Angeles', 'Pacific Time (PT)'),
            ('America/Halifax', 'Atlantic Time (AT)'),
            ('Europe/London', 'Greenwich Mean Time (GMT)'),
            ('Europe/Paris', 'Central European Time (CET)'),
            ('Asia/Tokyo', 'Japan Standard Time (JST)'),
            ('Australia/Sydney', 'Australian Eastern Time (AET)'),
        ],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        })
    )

    zodiac_type = forms.ChoiceField(
        choices=[('tropical', 'Tropical'), ('sidereal', 'Sidereal')],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        })
    )

    house_system = forms.ChoiceField(
        choices=[('placidus', 'Placidus'), ('whole_sign', 'Whole Sign')],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        })
    )

    ai_model = forms.ChoiceField(
        choices=[
            ('gpt-4', 'GPT-4'),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
            ('claude-3-opus', 'Claude 3 Opus'),
            ('claude-3-sonnet', 'Claude 3 Sonnet'),
            ('mistral-medium', 'Mistral Medium'),
        ],
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent shadow-sm'
        })
    )

    temperature = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.7,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'step': '0.1',
            'min': '0.0',
            'max': '1.0'
        })
    )

    max_tokens = forms.IntegerField(
        min_value=100,
        max_value=4000,
        initial=1000,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border border-plum2 bg-dark2 text-accent placeholder-plum2 shadow-sm',
            'min': '100',
            'max': '4000'
        })
    )

    is_public = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-plum2 bg-dark2 text-accent focus:ring-accent focus:ring-offset-dark2'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        if latitude is not None and (latitude < -90 or latitude > 90):
            raise ValidationError('Latitude must be between -90 and 90 degrees.')

        if longitude is not None and (longitude < -180 or longitude > 180):
            raise ValidationError('Longitude must be between -180 and 180 degrees.')

        return cleaned_data
