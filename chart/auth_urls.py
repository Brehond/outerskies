from django.urls import path
from . import auth_views

app_name = 'auth'

urlpatterns = [
    # Authentication views
    path('register/', auth_views.register_view, name='register'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    
    # Profile management
    path('profile/', auth_views.profile_view, name='profile'),
    path('change-password/', auth_views.change_password_view, name='change_password'),
    
    # Password reset
    path('password-reset/', auth_views.password_reset_request_view, name='password_reset_request'),
    path('reset-password/<uuid:token>/', auth_views.password_reset_confirm_view, name='password_reset_confirm'),
    
    # Chart management
    path('chart-history/', auth_views.chart_history_view, name='chart_history'),
    path('chart/<uuid:chart_id>/delete/', auth_views.delete_chart_view, name='delete_chart'),
    path('chart/<uuid:chart_id>/toggle-favorite/', auth_views.toggle_favorite_chart_view, name='toggle_favorite_chart'),
    
    # API endpoints for AJAX requests
    path('api/check-username/', auth_views.check_username_availability, name='check_username'),
    path('api/check-email/', auth_views.check_email_availability, name='check_email'),
] 