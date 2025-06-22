from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.views.generic import TemplateView
from plugins import get_plugin_manager

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chart/', include('chart.urls')),
    path('auth/', include('chart.auth_urls')),
    path('', include('django_prometheus.urls')),
    # Uncomment if you have payments:
    # path('payments/', include('payments.urls')),
]

# Add plugin URLs
plugin_manager = get_plugin_manager()
plugin_urls = plugin_manager.get_plugin_urls()
if plugin_urls:
    urlpatterns.extend(plugin_urls)
