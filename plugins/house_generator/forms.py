"""
Forms for the house generator plugin
"""

from django import forms


class HouseGeneratorForm(forms.Form):
    """
    Form for generating house systems
    """
    house_system = forms.ChoiceField(
        choices=[
            ('placidus', 'Placidus'),
            ('koch', 'Koch'),
            ('equal', 'Equal House'),
            ('whole_sign', 'Whole Sign'),
        ],
        label='House System',
        help_text='Select the house system to use'
    )

    latitude = forms.FloatField(
        label='Latitude',
        help_text='Geographic latitude for house calculation'
    )

    longitude = forms.FloatField(
        label='Longitude',
        help_text='Geographic longitude for house calculation'
    )
