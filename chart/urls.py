from django.urls import path
from . import views

urlpatterns = [
    path('form/', views.chart_form, name='chart_form'),
    path('generate/', views.generate_chart, name='generate_chart'),
]
