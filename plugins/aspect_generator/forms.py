from django import forms


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