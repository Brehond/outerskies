from django import forms
from .models import AspectConfiguration


class AspectGeneratorSettingsForm(forms.Form):
    """Settings form for the Aspect Generator plugin"""
    
    default_orb = forms.FloatField(
        label="Default Aspect Orb",
        min_value=0.0,
        max_value=15.0,
        initial=8.0,
        help_text="Default orb in degrees for aspect calculations"
    )
    
    aspects_enabled = forms.BooleanField(
        label="Enable Aspect Generation",
        initial=True,
        required=False,
        help_text="Enable AI-powered aspect interpretations"
    )

class AspectConfigurationForm(forms.ModelForm):
    class Meta:
        model = AspectConfiguration
        fields = ['aspect_type', 'orb', 'is_active']
        widgets = {
            'aspect_type': forms.Select(attrs={'class': 'form-control'}),
            'orb': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        } 