from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chart/', include('chart.urls')),
    path('', include('django_prometheus.urls')),
    # Uncomment if you have payments:
    # path('payments/', include('payments.urls')),
]
