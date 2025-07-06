from django import forms


class HouseGeneratorSettingsForm(forms.Form):
    """Settings form for the House Generator plugin"""
    
    houses_enabled = forms.BooleanField(
        label="Enable House Interpretations",
        initial=True,
        required=False,
        help_text="Enable AI-powered house interpretations"
    )
    
    include_planets = forms.BooleanField(
        label="Include Planets in Houses",
        initial=True,
        required=False,
        help_text="Include planet information in house interpretations"
    ) 