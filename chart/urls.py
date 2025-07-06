from django.urls import path
from . import views
from .views import system_dashboard

urlpatterns = [
    path('', views.chart_form, name='chart_form'),
    path('form/', views.chart_form, name='chart_form'),
    path('generate/', views.generate_chart, name='generate_chart'),
    path('admin/system-dashboard/', system_dashboard, name='system_dashboard'),
]
