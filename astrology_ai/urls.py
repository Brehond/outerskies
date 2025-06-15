from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chart/', include('chart.urls')),
    # Uncomment if you have payments:
    # path('payments/', include('payments.urls')),
]
