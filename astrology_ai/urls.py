from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.shortcuts import redirect
from plugins import get_plugin_manager
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

def homepage(request):
    """Simple homepage that redirects to chart form"""
    return redirect('chart_form')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('chart/', include('chart.urls')),
    path('auth/', include('chart.auth_urls')),
    path('payments/', include('payments.urls')),
    path('', include('django_prometheus.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Homepage
    path('', homepage, name='homepage'),
]

# Add plugin URLs
plugin_manager = get_plugin_manager()
plugin_urls = plugin_manager.get_plugin_urls()
if plugin_urls:
    urlpatterns.extend(plugin_urls)
